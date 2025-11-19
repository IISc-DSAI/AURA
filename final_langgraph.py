import asyncio
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

from ai_preprocessing import (
    rewrite_query,
    summarise_conversation,
    describe_images_locally,
    mcp_prompt,
    generate_rag_prompt,
    run_full_pipeline
)

from genai_multimodal_helpers import (
    prompt_only,
    merge_with_polished,
    merge_two_polished
)

from rag.test import query_endpoint_async


# ===========================================================
# Input Model
# ===========================================================

class PipelineInput(BaseModel):
    query: str
    chat_history: str
    images_base_64: List[str] = []
    mcp: int = 0
    rag: int = 0
    yt_summary: int = 0


# ===========================================================
# FastAPI App
# ===========================================================

app = FastAPI()


# ===========================================================
# Async Wrappers
# ===========================================================

async def run_mcp_async(prompt: str, yt_summary: int):
    return await asyncio.to_thread(run_full_pipeline, prompt, yt_summary)


async def run_rag_async(prompt: str):
    rag_out = await query_endpoint_async(prompt)
    return {
        "answer": rag_out.get("answer", ""),
        "reference": rag_out.get("reference", None)
    }


# ===========================================================
# MAIN PIPELINE
# ===========================================================

async def master_pipeline(data: PipelineInput):

    # -------------------------------------------------------
    # 1. Preprocessing
    # -------------------------------------------------------
    rewritten_query = rewrite_query(data.query)
    history_summary = summarise_conversation(data.chat_history)

    img_desc = (
        describe_images_locally(data.images_base_64)
        if data.images_base_64 else ""
    )

    ultimate_prompt = (
        history_summary + "\n" +
        rewritten_query + "\n" +
        img_desc
    )

    # -------------------------------------------------------
    # Store intermediate steps
    # -------------------------------------------------------
    intermediate_steps = {
        "retrieved_chat_history": data.chat_history,
        "original_query": data.query,
        "rewritten_query": rewritten_query,
        "chat_history_summary": history_summary,
        "image_description": img_desc,
        "has_images": len(data.images_base_64) > 0,
        "ultimate_prompt": ultimate_prompt,
        "mcp_enabled": data.mcp == 1,
        "rag_enabled": data.rag == 1,
        "yt_summary_enabled": data.yt_summary == 1,
    }

    mcp_output = None
    rag_output = None
    youtube_links = []
    google_links = []
    citation = []
    youtube_summary = None

    # -------------------------------------------------------
    # 2. MCP
    # -------------------------------------------------------
    if data.mcp == 1:
        proper_mcp_prompt = mcp_prompt(ultimate_prompt)
        intermediate_steps["mcp_prompt"] = proper_mcp_prompt

        mcp_output = await run_mcp_async(
            # proper_mcp_prompt,
            rewritten_query,
            yt_summary=data.yt_summary
        )

        intermediate_steps["mcp_output"] = mcp_output

        youtube_links = mcp_output.get("youtube_videos", [])
        google_links = mcp_output.get("links", [])
        youtube_summary = mcp_output.get("summaries", None)

    # -------------------------------------------------------
    # 3. RAG
    # -------------------------------------------------------
    if data.rag == 1:
        proper_rag_prompt = generate_rag_prompt(ultimate_prompt)
        intermediate_steps["rag_prompt"] = proper_rag_prompt

        rag_output = await run_rag_async(proper_rag_prompt)
        intermediate_steps["rag_output"] = rag_output

        if rag_output.get("reference"):
            citation = [rag_output["reference"]]

    # -------------------------------------------------------
    # 4. Final response construction
    # -------------------------------------------------------
    if data.mcp == 0 and data.rag == 0:
        final = prompt_only(ultimate_prompt, images_b64=data.images_base_64)

    elif data.mcp == 1 and data.rag == 0:
        final = merge_with_polished(
            mcp_output.get("answer", ""),
            ultimate_prompt,
            data.images_base_64
        )

    elif data.mcp == 0 and data.rag == 1:
        final = merge_with_polished(
            rag_output.get("answer", ""),
            ultimate_prompt,
            data.images_base_64
        )

    else:  # both MCP + RAG
        final = merge_two_polished(
            mcp_output.get("answer", ""),
            rag_output.get("answer", ""),
            ultimate_prompt,
            data.images_base_64
        )

    # -------------------------------------------------------
    # Final result
    # -------------------------------------------------------
    final_result = {
        "final_response": final,
        "youtube_links": youtube_links,
        "google_links": google_links,
        "citation": citation,
        "youtube_summary": youtube_summary
    }

    return {
        **final_result,
        "intermediate_steps": intermediate_steps
    }


# ===========================================================
# Endpoint
# ===========================================================

@app.post("/process")
async def process_pipeline(data: PipelineInput):
    return await master_pipeline(data)
