import requests
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import Optional, List, Dict, Any
import json
import asyncio
import http.client
from rich.console import Console
from rich.markdown import Markdown
from mcp.server.fastmcp import FastMCP
import os
from mcp import ClientSession
from mcp.client.sse import sse_client
from dotenv import load_dotenv
import logging
from functools import lru_cache
from langchain_core.prompts import ChatPromptTemplate
from sympy import re
import prompts
from langchain_ollama import ChatOllama
from langchain_ollama import OllamaLLM
from langchain_core.output_parsers import JsonOutputParser
import trafilatura
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse
import aiohttp
from cachetools import TTLCache
from concurrent.futures import ThreadPoolExecutor

load_dotenv()

Console = Console()

YOUTUBE_API_KEY = "AIzaSyBhvQEhSfRgJoMTuEMIaz0SIQ7iswMxiEc"
SERPER_API_KEY = "ee555f084be162abc9e6c8fae7170f4de38f92df"
conn = http.client.HTTPSConnection("google.serper.dev")
headers = {
'X-API-KEY': SERPER_API_KEY,
'Content-Type': 'application/json'
}

HOST = os.getenv("HOST")
if not HOST:
    HOST = "localhost"

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not YOUTUBE_API_KEY:
    raise ValueError("YOUTUBE_API_KEY environment variable is required")

YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
GEMMA_MODEL = "gemma3:4b"

json_parser = JsonOutputParser()
llm = OllamaLLM(model="gemma3:4b")
chat = ChatOllama(model="gemma3:4b")

analysis_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are AutoMate, an experienced vehicle mechanic."),
    ("user", prompts.mechanic_analysis_template)
])

format_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are AutoMate, an experienced vehicle mechanic."),
    ("user", prompts.format_prompt)
])

@lru_cache(maxsize=128)
def get_youtube_service():
    # cached youtube service to avoid multiple instantiation
    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=YOUTUBE_API_KEY)

def get_youtube_transcript(youtube_url):
    # Extract video ID
    video_id = youtube_url.split("v=")[-1].split("&")[0]
    transcript_list = YouTubeTranscriptApi().fetch(video_id)
    text = ""
    for transcript in transcript_list:
        text += transcript.text + " "
    return text

def get_webpage_text(url):
    downloaded = trafilatura.fetch_url(url)
    if downloaded:
        return trafilatura.extract(downloaded)
    return None

_aiohttp_session: aiohttp.ClientSession | None = None
_executor = ThreadPoolExecutor(max_workers=6)

async def get_session() -> aiohttp.ClientSession:
    global _aiohttp_session
    if _aiohttp_session is None or _aiohttp_session.closed:
        timeout = aiohttp.ClientTimeout(total=30)
        _aiohttp_session = aiohttp.ClientSession(timeout=timeout)
    return _aiohttp_session

async def shutdown_resources():
    global _aiohttp_session, _executor
    if _aiohttp_session and not _aiohttp_session.closed:
        await _aiohttp_session.close()
    _executor.shutdown(wait=False)

def parse_json_from_text(text: str) -> dict | None:
    """Try json.loads then fallback to extracting first {...} block."""
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{[\s\S]*?\}", text)
        if m:
            try:
                return json.loads(m.group())
            except Exception:
                return None
    return None


chain1 = analysis_prompt | llm
chain2 = format_prompt | llm

def classify_link(url):
    domain = urlparse(url).netloc.lower()

    # Category dictionaries
    VIDEO_SITES = ["youtube.com", "youtu.be", "vimeo.com", "dailymotion.com"]
    SOCIAL_SITES = ["reddit.com", "facebook.com", "twitter.com", "x.com", "quora.com", "instagram.com", "linkedin.com"]
    NEWS_SITES = ["bbc.com", "cnn.com", "nytimes.com", "theguardian.com"]
    FORUM_SITES = ["stackexchange.com", "stackoverflow.com", "github.com", "medium.com"]

    if any(s in domain for s in VIDEO_SITES):
        return "video"
    elif any(s in domain for s in SOCIAL_SITES):
        return "social"
    elif any(s in domain for s in NEWS_SITES):
        return "news"
    elif any(s in domain for s in FORUM_SITES):
        return "forum"
    else:
        return "web"

youtube_videos = []

async def query_gemma_async(query: str) -> str:
    """Async Gemma call using shared aiohttp session."""
    try:
        session = await get_session()
        url = f"http://{HOST.rstrip(':')}:11434/api/generate"
        payload = {"model": GEMMA_MODEL, "prompt": query, "stream": False}
        # simple retry loop
        for attempt in range(3):
            try:
                async with session.post(url, json=payload, timeout=30) as resp:
                    resp.raise_for_status()
                    body = await resp.json()
                    return body.get("response", "")
            except Exception as e:
                if attempt == 2:
                    raise
                await asyncio.sleep(1 + attempt)
    except Exception as e:
        logger.error("Gemma query failed: %s", e)
        return f"Error generating response: {e}"

async def website_search_sse(query: str) -> Dict[str, Any]:
    try:
        payload = json.dumps({
            "q": query
        })
        conn.request("POST", "/search", payload, headers)
        res = conn.getresponse()
        data = res.read()
        res = json.loads(data)
        links = [item['link'] for item in res.get('organic', [])]
        snippets = [item['snippet'] for item in res.get('organic', [])]
        peopleAlsoAsk = [{"question": item['question'], "snippet": item['snippet'], "link": item['link']} for item in res.get('peopleAlsoAsk', [])]
        return {"links": links, "snippets": snippets, "peopleAlsoAsk": peopleAlsoAsk}
    except HttpError as e:
        logger.error(f"Serper API error: {e}")
        return {"error": f"Serper API error: {e}", "links": [], "snippets": [], "peopleAlsoAsk": []}
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {"error": f"Unexpected error: {e}", "links": [], "snippets": [], "peopleAlsoAsk": [] }

async def search_youtube(query: str, max_results: int = 3, order: str = "relevance") -> Dict[str, Any]:
    try:
        if max_results < 1 or max_results > 50:
            max_results = 5
        
        ## create a dummy data for testing purpose
        youtube = get_youtube_service()
        request = youtube.search().list(
            q=query,
            part="snippet",
            type="video",
            maxResults=max_results,
            order=order
        )
        
        response = request.execute()

        videos = []
        for item in response.get("items", []):
            video_data = {
                "video_id": item["id"]["videoId"],
                "title": item["snippet"]["title"],
                "channel": item["snippet"]["channelTitle"],
                "channel_id": item["snippet"]["channelId"],
                "description": item["snippet"]["description"][:200] + "..." if len(item["snippet"]["description"]) > 200 else item["snippet"]["description"],
                "published_at": item["snippet"]["publishedAt"],
                "thumbnail_url": item["snippet"]["thumbnails"]["default"]["url"],
                "url": f"https://www.youtube.com/watch?v={item['id']['videoId']}"
            }
            logging.info(f"Found video: {video_data['title']}")
            videos.append(video_data)

        return {
            "query": query,
            "total_results": len(videos),
            "order": order,
            "videos": videos
        }
    
    except HttpError as e:
        logger.error(f"YouTube API error: {e}")
        return {"error": f"YouTube API error: {e}", "videos": []}
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {"error": f"Unexpected error: {e}", "videos": []}


async def get_webpage_text_async(url: str) -> str | None:
    """Run trafilatura in thread to avoid blocking event loop."""
    loop = asyncio.get_event_loop()
    try:
        def fetch():
            downloaded = trafilatura.fetch_url(url)
            return trafilatura.extract(downloaded) if downloaded else None
        return await loop.run_in_executor(_executor, fetch)
    except Exception as e:
        logger.warning("Failed to fetch %s: %s", url, e)
        return None

async def query_enhancing(user_query):
    global chain1, youtube_videos
    global chain2
    try:
        gemma_analysis = chain1.invoke({"user_query": user_query})
        
        logging.info(f"Gemma Analysis Response: {gemma_analysis}")
        try:
            gemma_analysis = json_parser.parse(gemma_analysis)
        except Exception as e:

            triggers = ["youtube", "how to", "repair", "fix", "install", "tutorial", "video", "watch"]
            needs_youtube = any(trigger in user_query.lower() for trigger in triggers)
            gemma_analysis = {
                    "needs_youtube": needs_youtube,
                    "youtube_query": user_query if needs_youtube else None,
                    "response_type": "tutorial_search" if needs_youtube else "general_response"
                }

        logging.info(f"Gemma Analysis: {gemma_analysis}")
        search_query = gemma_analysis.get("youtube_query", user_query)
        logging.info(f"Search Query: {search_query}")
        website_content = await website_search_sse(search_query)
        links = website_content.get("links", [])
        snippets = website_content.get("snippets", [])
        peopleAlsoAsk = website_content.get("peopleAlsoAsk", [])

        context = ""

        if links is not None:
            for link in links:
                logging.info(f"Fetching content from link: {link}")
                cat = classify_link(link)
                logging.info(f"Classified link category: {cat}")
                if cat == "web":
                    text = await get_webpage_text_async(link)
                    if text:
                        context += f"Content from webpage {link}:\n{text}\n\n"
                elif "youtube" in link:
                    youtube_videos.append(link)
                else:
                    continue
                
        if gemma_analysis.get("needs_youtube", False):
            logging.info("🔍 Performing YouTube search via SSE...")
            youtube_results = await search_youtube(search_query, max_results=3)
            if youtube_results:
                formatted_response = chain2.invoke({
                    "user_query": user_query,
                    "youtube_results": youtube_results,
                    "context": website_content
                })

                logging.info(f"Formatted Response: {formatted_response}")

                if youtube_results.get('videos'):
                    result = youtube_results['videos']
                    logging.info(f"YouTube Search Results: {result}")
                    youtube_videos.extend([video['url'] for video in result])

                return {
                    "response": formatted_response,
                    "youtube_results": youtube_results['videos'],
                    "used_sse": True,
                    "links": website_content.get("links", []),
                    "website_results": website_content,
                }
            
            else:
                # Handle YouTube search error
                formatted_response = chain2.invoke({
                    "user_query": user_query,
                    "youtube_results": None,
                    "context": website_content
                })
                logging.info(f"Formatted Response (No YouTube): {formatted_response}")
                return {
                    "response": formatted_response,
                    "youtube_results": None,
                    "used_sse": False,
                    "error": youtube_results.get('error'),
                    "website_results": website_content,
                    "links": website_content.get("links", []),
                }
            
        else:
            formatted_response = chain2.invoke({
                "user_query": user_query,
                "youtube_results": None,
                "context": website_content
            })
            logging.info(f"Formatted Response (No YouTube): {formatted_response}")
            return {
                "response": formatted_response,
                "youtube_results": None,
                "used_sse": False,
                "links": website_content.get("links", []),
                "website_results": website_content,
            }

            
    except Exception as e:
        print(f"❌ Error in enhanced query: {e}")
        fallback_response = await query_gemma_async(user_query)
        return {
            "response": fallback_response,
            "youtube_results": None,
            "used_sse": False,
            "error": str(e)
        }       


async def attaching_everything(prompt : str):
    print("="*30)
    result = await query_enhancing(prompt)
    print(result["response"])
    print("YouTube Videos Found:")
    
    logging.info("YouTube Videos Found:", {youtube_videos} )
    youtube_links = youtube_videos
    youtube_videos = []
    logging.info(f"YouTube Links: {youtube_links}")
    logging.info(f"Final Result: {youtube_videos}")
    final_response = {
        "youtube_videos": youtube_links,
        "response": result.get("response", ""),
        "links": result.get("links", []),
    }
    return final_response

async def youtube_summarization(youtube_list: list) -> str:
    if not youtube_list:
        return "No YouTube videos to summarize."
    summarization_results = []
    for video_url in youtube_list:
        try:
            transcript = get_youtube_transcript(video_url)
            summary_prompt = f"""
            
            Summarize the following YouTube video transcript in a concise manner, highlighting the key points and steps mentioned:
            Transcript:
            {transcript}
            """
            summary = await query_gemma_async(summary_prompt)
            Console.print(f"\n Summary for {video_url}:")
            Console.print(Markdown(summary))
            summarization_results.append({
                "video_url": video_url,
                "summary": summary
            })  
        except Exception as e:
            Console.print(f" Could not summarize video {video_url}: {e}")
    youtube_videos = []
    return summarization_results

async def main():
    print("="*30)

    while True:
        try:
            user_input = input("\nEnter your query: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print(" Goodbye!")
                break
                
            if not user_input:
                continue
                
            print(" Processing...")
            
            result = await query_enhancing(user_input)

            # print(result)
            # Display the response
            print("Check moment")

            print(json.dumps(result, indent=2))
            print("\ AI Response:")
            print("-" * 30)
            Console.print(Markdown(result["response"]))
            Console.print("\n YouTube Videos Found:")
            Console.print(youtube_videos)
            ask_summarization = input("Would like us to summarize the Youtube Videos? (yes/no): ").strip().lower()
            if ask_summarization in ['yes', 'y']:
                for video_url in youtube_videos:
                    try:
                        transcript = get_youtube_transcript(video_url)
                        summary_prompt = f"""
                        
                        Summarize the following YouTube video transcript in a concise manner, highlighting the key points and steps mentioned:
                        Transcript:
                        {transcript}
                        """

                        summary = await query_gemma_async(summary_prompt)
                        Console.print(f"\n Summary for {video_url}:")
                        Console.print(Markdown(summary))
                    except Exception as e:
                        print(f" Could not summarize video {video_url}: {e}")

            if result.get("website_content", []):
                people_also_ask = result["website_content"].get("peopleAlsoAsk", [])
                if people_also_ask:
                    Console.print("\n People Also Ask:", style="bold yellow")
                    Console.print("-" * 30)
                    for item in people_also_ask:
                        Console.print(f"Q: {item['question']}")
                        Console.print(f"Brief: {item['snippet']}")
                        Console.print(f"Link: {item['link']}\n")

        except (KeyboardInterrupt, EOFError):
            print("\n Exiting...")
            break
        except Exception as e:
            print(f" Unexpected error: {e}")

if __name__ == "__main__":
    asyncio.run(main())

