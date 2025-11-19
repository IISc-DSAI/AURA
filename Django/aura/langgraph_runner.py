# orchestrator/langgraph_runner.py
import requests
import time
import random

LANGGRAPH_URL = "http://13.201.4.144:9000/process"

def run_langgraph(payload: dict) -> dict:
    resp = requests.post(LANGGRAPH_URL, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()

    # """
    # Dummy LangGraph runner.
    # Accepts:
    # {
    #     "query": str,
    #     "chat_history": str,
    #     "images_base_64": List[str],
    #     "mcp": 0/1,
    #     "rag": 0/1,
    #     "yt_summary": 0/1
    # }

    # Returns:
    # {
    #     "final_response": str,
    #     "youtube_links": list,
    #     "google_links": list,
    #     "citation": list,
    #     "youtube_summary": str or None
    # }
    # """

    # # ---------------------------
    # # Extract inputs
    # # ---------------------------
    # query = payload.get("query", "")
    # history = payload.get("chat_history", "")
    # images = payload.get("images_base_64", [])
    # use_mcp = payload.get("mcp", 0)
    # use_rag = payload.get("rag", 0)
    # use_yt = payload.get("yt_summary", 0)

    # # ---------------------------
    # # Dummy processing simulation
    # # ---------------------------
    # time.sleep(0.4)   # simulate LLM delay

    # # Fake generating content
    # fake_answer = f"🧪 Dummy Answer for: **{query}**\n\n"
    # fake_answer += f"History length: {len(history.split())} words\n"
    # fake_answer += f"Images received: {len(images)}\n\n"

    # if use_rag:
    #     fake_answer += "🔍 RAG was used.\n"
    # else:
    #     fake_answer += "❌ RAG disabled.\n"

    # if use_mcp:
    #     fake_answer += "🌐 MCP web search active.\n"
    # else:
    #     fake_answer += "❌ MCP disabled.\n"

    # if use_yt:
    #     fake_answer += "▶️ YouTube summarization enabled.\n"
    # else:
    #     fake_answer += "❌ YouTube summary disabled.\n"

    # # ---------------------------
    # # Dummy links + citations
    # # ---------------------------
    # dummy_google = [
    #     "https://example.com/google_result_1",
    #     "https://example.com/google_result_2"
    # ] if use_mcp else []

    # dummy_youtube = [
    #     "https://youtu.be/dQw4w9WgXcQ"
    # ] if use_mcp else []

    # dummy_yt_summary = (
    #     "This is a dummy YouTube summary generated for testing." if use_yt else None
    # ) 

    # dummy_citations = [
    #     {"source": "Dummy RAG doc", "page": 1},
    #     {"source": "Dummy Web Search", "rank": 2}
    # ] if use_rag else []

    # # ---------------------------
    # # FINAL STRUCTURED OUTPUT
    # # ---------------------------
    # result = {
    #     "final_response": fake_answer,
    #     "youtube_links": dummy_youtube,
    #     "google_links": dummy_google,
    #     "citation": dummy_citations,
    #     "youtube_summary": dummy_yt_summary
    # }

    # return result