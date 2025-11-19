# import base64
# import warnings
# from io import BytesIO
# from fastapi import FastAPI
# from pydantic import BaseModel

# from transformers import (
#     AutoProcessor,
#     AutoModelForImageTextToText
# )

# import torch
# from PIL import Image

# warnings.filterwarnings("ignore")

# MODEL_PATH = "./Qwen2.5-VL-3B-Instruct"

# print("Loading Qwen2.5-VL-3B-Instruct (FP16) ...")

# processor = AutoProcessor.from_pretrained(
#     MODEL_PATH,
#     use_fast=True           # faster, fewer warnings
# )

# model = AutoModelForImageTextToText.from_pretrained(
#     MODEL_PATH,
#     dtype=torch.float16,
#     device_map="auto",
# )

# app = FastAPI()


# class InputImages(BaseModel):
#     images: list[str]


# def decode_base64_to_image(b64: str):
#     data = base64.b64decode(b64)
#     return Image.open(BytesIO(data)).convert("RGB")


# @app.post("/describe")
# async def describe_images(data: InputImages):

#     # Decode base64 images into PIL
#     pil_images = [decode_base64_to_image(b) for b in data.images]

#     # Build messages in the REQUIRED Qwen2.5-VL format
#     contents = []

#     for img in pil_images:
#         contents.append({"type": "image", "image": img})

#     contents.append({
#         "type": "text",
#         "text": "Describe these images clearly and in detail."
#     })

#     messages = [{"role": "user", "content": contents}]

#     # Build input tensors EXACTLY as HF recommends
#     inputs = processor.apply_chat_template(
#         messages,
#         add_generation_prompt=True,
#         tokenize=True,
#         return_tensors="pt",
#         return_dict=True,
#     ).to(model.device)

#     # Generate output
#     output_ids = model.generate(
#         **inputs,
#         max_new_tokens=1000,
#         temperature=0.2,
#     )

#     # The model output comes AFTER the input tokens
#     generated_text = processor.decode(
#         output_ids[0][inputs["input_ids"].shape[-1]:],
#         skip_special_tokens=True
#     )

#     return {"description": generated_text}



# # --------------------------

# # -----------------------------------------
# # NEW: Helper for text-only generation
# # -----------------------------------------

# class MCPInput(BaseModel):
#     text: str


# def generate_text_vl(prompt: str, max_new_tokens=300):
#     """
#     Use Qwen2.5-VL-3B-Instruct for pure text generation.
#     """
#     messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]

#     inputs = processor.apply_chat_template(
#         messages,
#         add_generation_prompt=True,
#         tokenize=True,
#         return_tensors="pt",
#         return_dict=True,
#     ).to(model.device)

#     output_ids = model.generate(
#         **inputs,
#         max_new_tokens=max_new_tokens,
#         temperature=0.2,
#         do_sample=False,               # deterministic output
#         eos_token_id=processor.tokenizer.eos_token_id
#     )

#     # Decode ONLY new tokens
#     generated = processor.decode(
#         output_ids[0][inputs["input_ids"].shape[-1]:],
#         skip_special_tokens=True
#     ).strip()

#     return generated


# # -----------------------------------------
# # NEW: MCP PROMPT GENERATION
# # -----------------------------------------

# @app.post("/mcp_prompt")
# async def generate_mcp_prompt(data: MCPInput):
#     """
#     Convert the mixed content (query + history + image description)
#     into a single, clean, actionable MCP prompt.
#     """

#     prompt = f"""
# You are an expert AI prompt engineer.

# Convert the following mixed content into a single, clean, actionable 
# MCP system prompt. The MCP prompt should:

# - clearly state the user's goal
# - summarize essential conversation context
# - summarize image descriptions (if provided)
# - give a concrete task for the MCP system
# - avoid repeating unnecessary details
# - be written as a single coherent instruction
# - begin with a double quote (") and end with a double quote (")
# - follow the example style strictly

# =====================
# MCP FORMAT EXAMPLE 1
# =====================
# Example Input:
# User wants to identify a bird in an uploaded image.
# Context: beginner photographer.
# Image: yellow bird, black wings, pointed beak.

# Example Output:
# "Identify the bird using the provided description 
# (yellow bird with black wings and pointed beak). 
# Provide species, price if sold as a pet, and helpful 
# advice for a beginner photographer."

# =====================
# MCP FORMAT EXAMPLE 2
# =====================
# Example Input:
# User uploaded laptop photo. Context shows user wants a budget device under $800.
# Image: silver 14-inch laptop with Intel sticker.

# Example Output:
# "Identify the laptop model using the description 
# (silver 14-inch notebook with Intel badge). Provide 
# probable model name, price range, and alternatives 
# under $800."

# ---------------------
# NOW CONVERT THIS INPUT
# ---------------------
# {data.text}

# ====================
# FINAL MCP PROMPT ONLY
# ====================
# """

#     final_prompt = generate_text_vl(prompt, max_new_tokens=300)

#     # Ensure it starts and ends with a quote
#     fp = final_prompt
#     if not fp.startswith('"'):
#         fp = '"' + fp
#     if not fp.endswith('"'):
#         fp = fp + '"'

#     return {"mcp_prompt": fp}

# # --------------------------

# @app.post("/rag_prompt")
# async def generate_rag_prompt(data: MCPInput):
#     """
#     Generate a high-quality RAG query prompt from mixed content:
#     - user query
#     - conversation summary
#     - image descriptions
#     - contextual notes  

#     The output will be a *single clean RAG prompt* the RAG retriever can use.
#     """

#     prompt = f"""
# You are an expert RAG prompt engineer.

# Convert the following mixed content into one clean, compact,
# information-dense *RAG retrieval query*. Follow these rules:

# RAG PROMPT RULES:
# - Focus ONLY on factual details needed to search documents.
# - Avoid conversational framing ("the user said...", "assistant said...").
# - Combine details from:
#     • user query
#     • conversation context
#     • image descriptions
# - Remove filler words and irrelevant story context.
# - Make the output a *single short paragraph*, maximum 3–5 sentences.
# - NO bullet points.
# - NO explanation.
# - Begin with a quote (") and end with a quote (").

# Example Input:
# User wants to know how to replace an E46 air filter.
# Chat context says they already removed the air intake cover.
# Image: shows BMW E46 engine bay with open airbox.

# Example Output:
# "BMW E46 air-filter replacement procedure where intake cover already removed and the airbox is open. 
# Retrieve steps, torque specs, safety notes, and reassembly instructions."

# ---------------------
# NOW CONVERT THIS INPUT
# ---------------------
# {data.text}

# ====================
# FINAL RAG PROMPT ONLY
# ====================
# """

#     # Use your Qwen-VL model for text-only generation
#     final_prompt = generate_text_vl(prompt, max_new_tokens=250).strip()

#     # Auto-wrap in quotes
#     if not final_prompt.startswith('"'):
#         final_prompt = '"' + final_prompt
#     if not final_prompt.endswith('"'):
#         final_prompt = final_prompt + '"'

#     return {"rag_prompt": final_prompt}

import base64
import warnings
from io import BytesIO

from fastapi import FastAPI
from pydantic import BaseModel
from PIL import Image

import torch
from transformers import AutoProcessor, AutoModelForImageTextToText

warnings.filterwarnings("ignore")

# -----------------------------------------------------------
# Load Qwen2.5-VL-3B-Instruct
# -----------------------------------------------------------
MODEL_PATH = "./Qwen2.5-VL-3B-Instruct"

print("Loading Qwen2.5-VL-3B-Instruct (FP16)...")

processor = AutoProcessor.from_pretrained(
    MODEL_PATH,
    use_fast=True
)

model = AutoModelForImageTextToText.from_pretrained(
    MODEL_PATH,
    dtype=torch.float16,
    device_map="auto",
)

app = FastAPI(title="Multimodal Preprocessing API")


# -----------------------------------------------------------
# Utility Helpers
# -----------------------------------------------------------
def decode_base64_image(b64: str) -> Image.Image:
    """Decode base64 → PIL image in RGB."""
    return Image.open(BytesIO(base64.b64decode(b64))).convert("RGB")


def build_vl_messages(images: list[Image.Image], text: str):
    """
    Build messages in the exact Qwen2.5-VL instruct format.
    """
    contents = [{"type": "image", "image": img} for img in images]
    contents.append({"type": "text", "text": text})
    return [{"role": "user", "content": contents}]


def build_text_messages(prompt: str):
    """Build text-only message in Qwen2.5-VL chat template format."""
    return [{"role": "user", "content": [{"type": "text", "text": prompt}]}]


def run_vl_generation(messages, max_new_tokens=300):
    """
    Unified function for both text & multimodal generation.
    """
    inputs = processor.apply_chat_template(
        messages,
        add_generation_prompt=True,
        return_tensors="pt",
        return_dict=True,
        tokenize=True
    ).to(model.device)

    output_ids = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        temperature=0.2,
        do_sample=False,
        eos_token_id=processor.tokenizer.eos_token_id
    )

    # Decode only newly generated tokens (skip input portion)
    generated = processor.decode(
        output_ids[0][inputs["input_ids"].shape[-1]:],
        skip_special_tokens=True
    )

    return generated.strip()


def ensure_wrapped_quotes(text: str) -> str:
    """Ensure the final output begins and ends with a double-quote."""
    if not text.startswith('"'):
        text = '"' + text
    if not text.endswith('"'):
        text = text + '"'
    return text


# -----------------------------------------------------------
# Request Schemas
# -----------------------------------------------------------
class InputImages(BaseModel):
    images: list[str]   # base64 strings


class TextInput(BaseModel):
    text: str


# -----------------------------------------------------------
# IMAGE → DESCRIPTION ENDPOINT
# -----------------------------------------------------------
@app.post("/describe")
async def describe_images(data: InputImages):
    """
    Describe multiple images in detail using Qwen2.5-VL.
    """

    pil_images = [decode_base64_image(b) for b in data.images]
    prompt_text = "Describe these images clearly, accurately, and in detail."

    messages = build_vl_messages(pil_images, prompt_text)
    description = run_vl_generation(messages, max_new_tokens=1000)

    return {"description": description}


# -----------------------------------------------------------
# TEXT-ONLY GENERATION WRAPPER (Used by MCP + RAG)
# -----------------------------------------------------------
def generate_text(prompt: str, max_new_tokens=300):
    messages = build_text_messages(prompt)
    return run_vl_generation(messages, max_new_tokens=max_new_tokens)


# -----------------------------------------------------------
# MCP PROMPT GENERATOR
# -----------------------------------------------------------
@app.post("/mcp_prompt")
async def generate_mcp_prompt(data: TextInput):
    """
    Convert messy user content/history/images into one clean,
    structured MCP system prompt.
    """

    prompt = f"""
You are an expert AI prompt engineer.

Convert the following mixed content into *one high-quality MCP system prompt*.
The MCP prompt must:

- clearly express the user’s goal
- merge relevant history/context into a short summary
- summarize image descriptions (if present in text)
- be written as a single coherent instruction
- avoid repeating irrelevant or verbose details
- be actionable and unambiguous
- begin with a double quote (") and end with a double quote (")
- avoid meta-commentary or explanations
- follow the style of the examples

===========================
MCP EXAMPLE 1
===========================
Input:
User wants to identify a bird from an uploaded image.
Context: beginner photographer.
Image: yellow bird, black wings.

Output:
"Identify the bird using the description (yellow bird with black wings). 
Provide its species, average price if sold as a pet, and beginner-friendly photography tips."

===========================
MCP EXAMPLE 2
===========================
Input:
User uploads laptop photo. Context says they want budget options.
Image: silver 14-inch laptop with Intel badge.

Output:
"Identify the laptop model from the description (silver 14-inch notebook with Intel badge). 
Provide likely model name, price range, and similar models under $800."

---------------------------
NOW PROCESS THIS INPUT:
---------------------------
{data.text}

===========================
FINAL MCP PROMPT ONLY
===========================
"""

    result = generate_text(prompt, max_new_tokens=350)
    return {"mcp_prompt": ensure_wrapped_quotes(result)}


# -----------------------------------------------------------
# RAG PROMPT GENERATOR
# -----------------------------------------------------------
@app.post("/rag_prompt")
async def generate_rag_prompt(data: TextInput):
    """
    Convert mixed content (query + history + image desc + notes)
    into a compact, factual, information-dense RAG retrieval query.
    """

    prompt = f"""
You are an expert RAG retrieval prompt engineer.

Convert the following mixed content into a *single, information-dense RAG query*.
Follow these rules strictly:

RAG RULES:
- Include only factual details useful for document search.
- No dialogue framing (no "user said", "assistant said").
- Combine:
    • the user’s core request
    • relevant context
    • image-based facts (if mentioned)
- Remove filler, emotion, or irrelevant narrative.
- Output must be 3–5 concise sentences.
- No bullet points.
- No explanations.
- Start and end with a double quote (").

---------------------------
NOW PROCESS THIS INPUT:
---------------------------
{data.text}

===========================
FINAL RAG PROMPT ONLY
===========================
"""

    result = generate_text(prompt, max_new_tokens=250)
    return {"rag_prompt": ensure_wrapped_quotes(result)}
