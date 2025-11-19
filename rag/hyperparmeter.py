import os
import asyncio
import json

from raganything import RAGAnything
from lightrag import LightRAG
from lightrag.kg.shared_storage import initialize_pipeline_status
from config import (
    get_rag_config,
    get_llm_model_func,
    get_vision_model_func,
    get_embedding_func
)

async def load_rag(working_dir="./rag_storage"):
    if not os.path.exists(working_dir):
        raise FileNotFoundError("RAG storage folder not found. Run ingest.py first.")

    lr = LightRAG(
        working_dir=working_dir,
        llm_model_func=get_llm_model_func(),
        embedding_func=get_embedding_func(),
    )
    await lr.initialize_storages()
    await initialize_pipeline_status()

    rag = RAGAnything(
        lightrag=lr,
        config=get_rag_config(),
        vision_model_func=get_vision_model_func(),
    )
    return rag


async def print_hyperparams():
    rag = await load_rag()
    lr = rag.lightrag

    print("\n=== HYPERPARAMETERS (LightRAG + RAGAnything) ===\n")

    hyperparams = {}

    for k, v in vars(lr).items():
        # Only keep simple tunable values (int, float, str, bool, dict)
        if isinstance(v, (int, float, str, bool, dict, list, tuple)):
            hyperparams[k] = v

    print(json.dumps(hyperparams, indent=2, ensure_ascii=False))

    print("\n=== TOTAL:", len(hyperparams), "parameters ===\n")


if __name__ == "__main__":
    asyncio.run(print_hyperparams())
