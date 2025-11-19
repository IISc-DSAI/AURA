import requests

def rewrite_query(text: str, host: str = "http://localhost:8100"):
    url = f"{host}/rewrite"
    payload = {"text": text}
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()["rewritten"]


def summarise_conversation(convo: str, host: str = "http://localhost:8100"):
    url = f"{host}/summarise"
    payload = {"text": convo}
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()["summary"]


def generate_title(text: str, host: str = "http://localhost:8100"):
    url = f"{host}/title_generation"
    payload = {"text": text}
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()["title"]

# ====================================================================================================================================

def mcp_prompt(text: str, host: str = "http://localhost:8600"):
    url = f"{host}/mcp_prompt"
    payload = {"text": text}

    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data.get("mcp_prompt", "")

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Error calling MCP prompt endpoint: {e}")

def generate_rag_prompt(text: str, host: str = "http://localhost:8600"):
    url = f"{host}/rag_prompt"
    payload = {"text": text}

    response = requests.post(url, json=payload)
    response.raise_for_status()

    return response.json()["rag_prompt"]

def describe_images_locally(image_b64_list, host="http://localhost:8600"):
    url = f"{host}/describe"
    payload = {"images": image_b64_list}
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()["description"]

# ====================================================================================================================================

import asyncio
from mcp_jiggle import attaching_everything, youtube_summarization


async def run_full_pipeline_async(prompt: str, yt_summary: int = 1):
    """
    Runs the full MCP pipeline:
    - YouTube search
    - Google/web search
    - Unified answer generation
    - Optional YouTube summarization
    
    yt_summary = 1 → include YT summaries  
    yt_summary = 0 → skip summarization and return None  
    """
    response = await attaching_everything(prompt)

    yt_videos = response.get("youtube_videos", [])
    answer = response.get("response", "")
    links = response.get("links", [])

    # Conditionally get YouTube summaries
    if yt_summary == 1 and yt_videos:
        yt_vids_summary = await youtube_summarization(yt_videos)
    else:
        yt_vids_summary = None

    return {
        "answer": answer,
        "links": links,
        "youtube_videos": yt_videos,
        "summaries": yt_vids_summary
    }


def run_full_pipeline(prompt: str, yt_summary: int = 1):
    """
    Sync wrapper around the async pipeline.
    This allows FastAPI / LangGraph / Streamlit / scripts to call safely.
    """
    return asyncio.run(run_full_pipeline_async(prompt, yt_summary=yt_summary))