# ================================================================
# test_bedrock.py
# Bedrock version of the 3 multimodal helper functions
# ================================================================

import os
import json
import base64
import random
import time
from typing import List, Optional
import boto3


# -------------------------
# Create Bedrock Client
# -------------------------
def bedrock_client(region=None):
    region_name = region or os.getenv("AWS_REGION") or "us-east-1"
    print(f"[INIT] Using AWS Region: {region_name}")
    return boto3.client("bedrock-runtime", region_name=region_name)


MODEL_ID = "anthropic.claude-3-5-sonnet-20240620-v1:0"

# GLOBAL CLIENT (IMPORTANT)
client = bedrock_client()


# -------------------------
# Convert base64 → Bedrock format
# -------------------------
def b64_to_bedrock_images(images_b64: Optional[List[str]]) -> List[dict]:
    if not images_b64:
        return []

    out = []
    for b64 in images_b64:
        if not b64:
            continue
        try:
            if b64.startswith("data:") and "base64," in b64:
                b64 = b64.split("base64,", 1)[1]

            raw = base64.b64decode(b64)

            # mime detection
            if raw[:3] == b"\xff\xd8\xff":
                mime = "image/jpeg"
            elif raw[:8].startswith(b"\x89PNG\r\n\x1a\n"):
                mime = "image/png"
            else:
                mime = "image/png"

            out.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": mime,
                    "data": base64.b64encode(raw).decode("utf-8")
                }
            })

        except:
            continue

    return out


# -------------------------
# Core Claude Bedrock Invoker
# -------------------------
def _claude(messages, max_tokens=4000, retries=20):
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "messages": messages,
    }

    for attempt in range(retries):
        try:
            response = client.invoke_model(
                modelId=MODEL_ID,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body)
            )
            raw = response["body"].read()
            data = json.loads(raw)
            return data["content"][0]["text"]

        except Exception as e:
            msg = str(e)
            if ("Throttling" in msg or
                "Too Many Requests" in msg or
                "rate" in msg.lower() or
                "503" in msg):

                wait = min(10, (2**attempt) + random.random())
                print(f"[WARN] Throttled. Retrying in {wait:.1f}s...")
                time.sleep(wait)
                continue

            raise e

    raise RuntimeError("Claude failed after max retries.")


# ================================================================
# 1) prompt_only
# ================================================================
def prompt_only(prompt: str, images_b64=None) -> str:
    imgs = b64_to_bedrock_images(images_b64)

    messages = [{
        "role": "user",
        "content": [
            {"type": "text",
             "text": "You are an expert multimodal assistant. If images are provided, use them."},
            *imgs,
            {"type": "text", "text": prompt}
        ]
    }]

    return _claude(messages)


# ================================================================
# 2) merge_with_polished
# ================================================================
def merge_with_polished(polished_answer: str, prompt: str, images_b64=None) -> str:
    imgs = b64_to_bedrock_images(images_b64)

    system_msg = (
        "You are an expert aggregator assistant. You will be provided a user prompt and "
        "a POLISHED ANSWER from a retrieval pipeline. Produce a unified final answer."
        "Do not add any context from your side."
    )

    text_block = (
        f"USER PROMPT:\n{prompt}\n\n"
        f"POLISHED ANSWER:\n{polished_answer}\n\n"
        "Now produce the final unified answer."
    )

    messages = [{
        "role": "user",
        "content": [
            {"type": "text", "text": system_msg},
            *imgs,
            {"type": "text", "text": text_block}
        ]
    }]

    return _claude(messages)


# ================================================================
# 3) merge_two_polished
# ================================================================
def merge_two_polished(a1: str, a2: str, prompt: str, images_b64=None) -> str:
    imgs = b64_to_bedrock_images(images_b64)

    system_msg = (
        "You are an expert reasoning orchestrator. You will be given two polished answers. "
        "Combine them into one best final answer."
        "Do not add any context from your side."
    )

    text_block = (
        f"USER PROMPT:\n{prompt}\n\n"
        f"POLISHED ANSWER 1:\n{a1}\n\n"
        f"POLISHED ANSWER 2:\n{a2}\n\n"
        "Now produce the single best final answer."
    )

    messages = [{
        "role": "user",
        "content": [
            {"type": "text", "text": system_msg},
            *imgs,
            {"type": "text", "text": text_block}
        ]
    }]

    return _claude(messages)