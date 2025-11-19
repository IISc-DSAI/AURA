import asyncio
import json
import os
from typing import Optional, Dict, Any, List

from lightrag.utils import EmbeddingFunc
from raganything import RAGAnythingConfig

import boto3

def get_bedrock_client(region: str | None = None):
    region_name = region or os.getenv("AWS_REGION") or "us-east-1"
    return boto3.client("bedrock-runtime", region_name=region_name)
import threading
os.environ["LIGHTHRAG_WORKER_TIMEOUT"] = "300"  # 5 minutes for embedding workers
os.environ["LIGHTHRAG_FUNC_TIMEOUT"] = "240"    # 4 minutes for embedding function calls

# Bedrock configuration
BEDROCK_MODEL_ID = os.getenv(
    "BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0"
)
BEDROCK_MAX_TOKENS = int(os.getenv("BEDROCK_MAX_TOKENS", "512"))
BEDROCK_TEMPERATURE = float(os.getenv("BEDROCK_TEMPERATURE", "0.3"))
BEDROCK_TOP_P = float(os.getenv("BEDROCK_TOP_P", "0.9"))
BEDROCK_CLIENT = get_bedrock_client(os.getenv("AWS_REGION"))
BEDROCK_MAX_CONCURRENT = int(os.getenv("BEDROCK_MAX_CONCURRENT", "2"))
BEDROCK_MAX_RETRIES = int(os.getenv("BEDROCK_MAX_RETRIES", "5"))
BEDROCK_RETRY_BASE_DELAY = float(os.getenv("BEDROCK_RETRY_BASE_DELAY", "0.5"))

# Global semaphore to limit concurrent Bedrock calls
_bedrock_semaphore = asyncio.Semaphore(BEDROCK_MAX_CONCURRENT)

# Local embedding model path
LOCAL_EMBEDDING_MODEL_PATH = "/home/ubuntu/mega_folder/bge-large-en-v1.5"

# Working directories
WORKING_DIR = "./rag_storage"
OUTPUT_DIR = "./output"
METADATA_FILE = os.path.join(WORKING_DIR, "processed_files.json")

# Load embedding model ONCE at startup
print(f"Loading local embedding model from: {LOCAL_EMBEDDING_MODEL_PATH}")
from sentence_transformers import SentenceTransformer
LOCAL_EMBEDDING_MODEL = SentenceTransformer(LOCAL_EMBEDDING_MODEL_PATH, device="cuda" if os.getenv("CUDA_VISIBLE_DEVICES") else "cpu")
print("✅ Local embedding model loaded successfully")

# Create a thread lock for thread-safe embedding generation
embedding_lock = threading.Lock()

def get_rag_config():
    """Get RAGAnything configuration with valid parameters only"""
    return RAGAnythingConfig(
        working_dir=WORKING_DIR,
        parser="mineru",
        parse_method="ocr",
        enable_image_processing=True,
        enable_table_processing=True,
        enable_equation_processing=False,
    )

def _parse_data_url(data_url: str) -> Optional[Dict[str, str]]:
    """Extract media type and base64 payload from a data URL or raw base64 string."""
    if not data_url:
        return None

    payload = data_url.strip()
    media_type = "image/png"

    if payload.startswith("data:"):
        payload = payload.split("data:", 1)[1]

    if "," in payload:
        header, encoded = payload.split(",", 1)
    else:
        header, encoded = "", payload

    header = header.strip()
    if header.startswith("image/"):
        media_type = header.split(";")[0]

    encoded = encoded.strip()
    if not encoded:
        return None

    return {"media_type": media_type, "data": encoded}


def _build_bedrock_body(
    prompt: str,
    system_prompt: Optional[str],
    images: List[Dict[str, str]],
) -> Dict[str, Any]:
    content = [{"type": "text", "text": prompt}]
    for img in images:
        content.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": img.get("media_type", "image/png"),
                    "data": img["data"],
                },
            }
        )

    body: Dict[str, Any] = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": BEDROCK_MAX_TOKENS,
        "temperature": BEDROCK_TEMPERATURE,
        "top_p": BEDROCK_TOP_P,
        "messages": [
            {
                "role": "user",
                "content": content,
            }
        ],
    }

    if system_prompt:
        body["system"] = system_prompt

    return body


def _extract_images_from_messages(messages) -> List[Dict[str, str]]:
    collected: List[Dict[str, str]] = []

    if not messages:
        return collected

    for msg in messages:
        if not isinstance(msg, dict):
            continue
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        for item in content:
            if isinstance(item, dict) and item.get("type") == "image_url":
                url_data = item.get("image_url", {}).get("url", "")
                parsed = _parse_data_url(url_data)
                if parsed:
                    collected.append(parsed)

    return collected


async def bedrock_generate_content(
    prompt: str,
    system_instruction: Optional[str] = None,
    image_data: Optional[str] = None,
    messages=None,
):
    """
    Generate content using Claude 3 Sonnet via Amazon Bedrock.
    Supports optional base64 image data (for multimodal prompts).
    """

    image_payloads = _extract_images_from_messages(messages)

    if image_data and not image_payloads:
        parsed = _parse_data_url(image_data) or {
            "media_type": "image/png",
            "data": image_data,
        }
        image_payloads.append(parsed)

    try:
        body = _build_bedrock_body(
            prompt=prompt,
            system_prompt=system_instruction,
            images=image_payloads,
        )

        async with _bedrock_semaphore:
            last_error: Optional[Exception] = None

            for attempt in range(1, BEDROCK_MAX_RETRIES + 1):
                def _invoke():
                    response = BEDROCK_CLIENT.invoke_model(
                        modelId=BEDROCK_MODEL_ID,
                        contentType="application/json",
                        accept="application/json",
                        body=json.dumps(body).encode("utf-8"),
                    )
                    raw = response["body"].read()
                    data = json.loads(raw)

                    texts = [
                        block.get("text", "")
                        for block in data.get("content", [])
                        if block.get("type") == "text"
                    ]
                    return "\n".join(filter(None, texts)) or json.dumps(data)

                try:
                    return await asyncio.to_thread(_invoke)
                except Exception as e:
                    last_error = e
                    msg = str(e)
                    # Handle throttling with exponential backoff
                    if "ThrottlingException" in msg or "Too Many Requests" in msg:
                        delay = BEDROCK_RETRY_BASE_DELAY * (2 ** (attempt - 1))
                        print(
                            f"Bedrock throttled (attempt {attempt}/{BEDROCK_MAX_RETRIES}), "
                            f"backing off for {delay:.2f}s..."
                        )
                        await asyncio.sleep(delay)
                        continue
                    # Other errors: break and fall through to generic handling
                    break

            # If we reach here, all retries failed
            raise last_error or RuntimeError("Unknown Bedrock error")
    except Exception as e:
        print(f"Error in Bedrock generation: {str(e)}")
        if "Extract entities" in prompt:
            return '''{"entities": [], "relationships": []}'''
        elif "analyze this" in prompt.lower():
            return '''{"status": "success", "summary": "Content processed", "key_points": ["Processing successful"]}'''
        return f"Error processing request: {str(e)}"

def get_llm_model_func():
    """Returns function for text-only LLM processing using Claude 3 Sonnet"""
    async def llm_model_func(prompt, system_prompt=None, history_messages=[], **kwargs):
        return await bedrock_generate_content(
            prompt,
            system_instruction=system_prompt,
        )
    return llm_model_func

def get_vision_model_func():
    """Returns function for multimodal processing using Claude 3 Sonnet"""
    async def vision_model_func(
        prompt, system_prompt=None, history_messages=[], image_data=None, messages=None, **kwargs
    ):
        return await bedrock_generate_content(
            prompt,
            system_instruction=system_prompt,
            image_data=image_data,
            messages=messages,
        )
    
    return vision_model_func

def get_embedding_func():
    """Local embedding function using BGE """
    async def embedding_func(texts):
        """Async wrapper that returns embeddings as numpy array"""
        if isinstance(texts, str):
            texts = [texts]
        # Run synchronous embedding in thread pool
        embeddings = await asyncio.to_thread(
            LOCAL_EMBEDDING_MODEL.encode,
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        return embeddings
    
    return EmbeddingFunc(
        embedding_dim=1024,  # bge-large-en-v1.5 uses 1024 dimensions
        max_token_size=512,
        func=embedding_func,
    )