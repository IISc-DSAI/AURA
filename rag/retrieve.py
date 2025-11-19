# retrieve.py
import os
import asyncio
from raganything import RAGAnything
from lightrag import LightRAG
from lightrag.kg.shared_storage import initialize_pipeline_status

from .config import (
    get_rag_config,
    get_llm_model_func,
    get_vision_model_func,
    get_embedding_func
)

# Absolute path to rag_storage
BASE_DIR = os.path.dirname(__file__)
DEFAULT_RAG_DIR = os.path.join(BASE_DIR, "rag_storage")


async def _create_rag(working_dir: str = DEFAULT_RAG_DIR) -> RAGAnything:
    """Create RAG instance using correct absolute path."""
    if not os.path.exists(working_dir):
        raise FileNotFoundError(
            f"No RAG storage found at '{working_dir}'. Run `ingest.py` first."
        )

    lightrag_instance = LightRAG(
        working_dir=working_dir,
        llm_model_func=get_llm_model_func(),
        embedding_func=get_embedding_func(),
    )

    await lightrag_instance.initialize_storages()
    await initialize_pipeline_status()

    return RAGAnything(
        lightrag=lightrag_instance,
        config=get_rag_config(),
        vision_model_func=get_vision_model_func(),
    )


async def answer_query_async(
    query: str,
    mode: str = "hybrid",
    vlm_enhanced: bool = False,
    working_dir: str = DEFAULT_RAG_DIR,
) -> str:
    """Fully async version (FastAPI should call this)."""
    rag = await _create_rag(working_dir)
    return await rag.aquery(query, mode=mode, vlm_enhanced=vlm_enhanced)


def answer_query(
    query: str,
    mode: str = "hybrid",
    vlm_enhanced: bool = False,
    working_dir: str = DEFAULT_RAG_DIR,
) -> str:
    """
    Sync wrapper for CLI and scripts.
    Auto-detects if an event loop is running.
    """
    try:
        loop = asyncio.get_running_loop()
        # FastAPI/uvicorn: schedule task in running loop
        return loop.run_until_complete(
            answer_query_async(query, mode, vlm_enhanced, working_dir)
        )
    except RuntimeError:
        # No loop running → normal script
        return asyncio.run(
            answer_query_async(query, mode, vlm_enhanced, working_dir)
        )