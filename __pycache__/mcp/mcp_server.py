# youtube_server.py
import os
from typing import Optional, List, Dict, Any
import aiohttp
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging
import requests
from mcp.server.fastmcp import FastMCP
import logging
import dotenv
from pyparsing import lru_cache
import langchain
import http.client
import asyncio
import json

dotenv.load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
conn = http.client.HTTPSConnection("google.serper.dev")
headers = {
'X-API-KEY': SERPER_API_KEY,
'Content-Type': 'application/json'
}

HOST = os.getenv("HOST")
if not HOST:
    HOST = "localhost"

# Create an MCP server
mcp = FastMCP("Demo", host=HOST, port=8000)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# YouTube API configuration

if not YOUTUBE_API_KEY:
    raise ValueError("YOUTUBE_API_KEY environment variable is required")

YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
GEMMA_MODEL = "gemma3"

@lru_cache(maxsize=128)
def get_youtube_service():
    # cached youtube service to avoid multiple instantiation
    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=YOUTUBE_API_KEY)

def query_gemma(query):
    url = "http://localhost:11434/api/generate"
    model = "gemma3:4b"
    payload = {
        "model": model,
        "prompt": query,
        "stream": False,
    }

    response = requests.post(url, json=payload)
    response.raise_for_status()
    data = response.json()
    return data["response"]

@mcp.tool("sse_search_and_summarize")
async def sse_search_and_summarize(query: str) -> Dict[str, Any]:
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

@mcp.tool("search_youtube_videos")
def search_youtube_videos(query: str, max_results: int = 5, order: str = "relevance") -> Dict[str, Any]:
    """
    Search YouTube for videos with specified query.
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return (1-50, default: 5)
        order: Sort order - 'relevance', 'date', 'rating', 'viewCount', 'title' (default: 'relevance')
    
    Returns:
        Dictionary containing search results with video information
    
        
    This snippet is to uncommente when you want to use actual YouTube API calls.
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
    """
    
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
        # videos = [{
        #     "video_id": "dQw4w9WgXcQ",
        #     "title": "Rick Astley - Never Gonna Give You Up (Video)",
        #     "channel": "RickAstleyVEVO",
        #     "channel_id": "UCuAXFkgsw1L7xaCfnd5JJOw",
        #     "description": "The official video for “Never Gonna Give You Up” by Rick Astley",
        #     "published_at": "2009-10-25T07:57:33Z",
        #     "thumbnail_url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/default.jpg",
        #     "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        # },
        # {
        #     "video_id": "3JZ_D3ELwOQ",
        #     "title": "a-ha - Take On Me (Official 4K Music Video)",
        #     "channel": "a-ha",
        #     "channel_id": "UCjzHeG1KWoonmf9d5KBvSiw",
        #     "description": "The official music video for a-ha - Take On Me",
        #     "published_at": "2009-06-16T12:00:00Z",
        #     "thumbnail_url": "https://i.ytimg.com/vi/3JZ_D3ELwOQ/default.jpg",
        #     "url": "https://www.youtube.com/watch?v=3JZ_D3ELwOQ"
        # }
        # ]

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


if __name__ == "__main__":
    print("Starting YouTube MCP Server...")
    print("Server will be available at http://localhost:8080/sse")
    print("Tools available:")
    print("- search_youtube_videos")
    print("- sse_search_and_summarize")
    asyncio.run(mcp.run(transport="sse"))
    # mcp.run(transport="sse")


