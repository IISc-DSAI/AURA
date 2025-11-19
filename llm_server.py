# from fastapi import FastAPI
# from pydantic import BaseModel
# from transformers import AutoTokenizer, AutoModelForCausalLM
# import torch

# app = FastAPI()

# MODEL_PATH = "./qwen2.5-1.5b"

# # --------------------------
# # Load tokenizer + model ONCE
# # --------------------------
# tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)

# model = AutoModelForCausalLM.from_pretrained(
#     MODEL_PATH,
#     dtype=torch.float16,
#     device_map="auto"      # LOADS MODEL ON GPU AUTOMATICALLY
# )

# model.config.use_cache = True


# # --------------------------
# # Helper: LLM generation
# # --------------------------
# def generate_llm(prompt: str, max_tokens: int = 150) -> str:
#     inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

#     output = model.generate(
#         **inputs,
#         max_new_tokens=max_tokens,
#         temperature=0.2,
#         do_sample=False,
#         use_cache=True,
#     )

#     text = tokenizer.decode(output[0], skip_special_tokens=True)
#     return text


# # --------------------------
# # Request Schema
# # --------------------------
# class Input(BaseModel):
#     text: str


# # --------------------------
# # 1) Query Rewrite
# # --------------------------
# @app.post("/rewrite")
# async def rewrite(data: Input):
#     prompt = (
#         "Rewrite the following text to be clear, concise, and well-structured:\n\n"
#         f"{data.text}\n\nRewritten:"
#     )

#     output = generate_llm(prompt, max_tokens=200)
#     rewritten = output.replace(prompt, "").strip()

#     return {"rewritten": rewritten}


# # --------------------------
# # 2) Conversation Summariser
# # --------------------------
# @app.post("/summarise")
# async def summarise(data: Input):
#     prompt = (
#         "Summarise the following conversation between User and Assistant clearly and concisely.\n\n"
#         f"{data.text}\n\nSummary:"
#     )

#     output = generate_llm(prompt, max_tokens=1500)
#     summary = output.replace(prompt, "").strip()

#     return {"summary": summary}

# # --------------------------
# # 3) Title Generation
# # --------------------------
# @app.post("/title_generation")
# async def title_generation(data: Input):
#     prompt = (
#         "Generate a concise and catchy title for the following content:\n\n"
#         f"{data.text}\n\nTitle:"
#     )

#     output = generate_llm(prompt, max_tokens=20)
#     title = output.replace(prompt, "").strip()

#     return {"title": title}

from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

app = FastAPI()

MODEL_PATH = "./qwen2.5-1.5b"

# --------------------------------------------------------
# Load tokenizer + model ONCE (GPU if available)
# --------------------------------------------------------
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)

model = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH,
    torch_dtype=torch.float16,
    device_map="auto",
)

model.config.use_cache = True


# --------------------------------------------------------
# Helper: LLM text generation
# --------------------------------------------------------
def generate_llm(prompt: str, max_tokens: int = 150) -> str:
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

    output = model.generate(
        **inputs,
        max_new_tokens=max_tokens,
        temperature=0.2,
        do_sample=False,
        use_cache=True,
        eos_token_id=tokenizer.eos_token_id,
    )

    text = tokenizer.decode(output[0], skip_special_tokens=True)

    # Remove the prompt portion if model echoes it
    if text.startswith(prompt):
        text = text[len(prompt):]

    return text.strip()


# --------------------------------------------------------
# Request Schema
# --------------------------------------------------------
class Input(BaseModel):
    text: str


# --------------------------------------------------------
# 1) Query Rewrite
# --------------------------------------------------------
@app.post("/rewrite")
async def rewrite(data: Input):
    prompt = (
        "Rewrite the following text to be clearer, well-structured, and grammatically correct.\n"
        "Do NOT change the meaning or add new information. Keep the original intent intact.\n"
        "Improve clarity, fix mistakes, and make it more readable.\n\n"
        f"Original text:\n{data.text}\n\n"
        "Rewritten:"
    )

    output = generate_llm(prompt, max_tokens=200)
    return {"rewritten": output}


# --------------------------------------------------------
# 2) Conversation Summariser
# --------------------------------------------------------
@app.post("/summarise")
async def summarise(data: Input):
    prompt = (
        "Summarise the following conversation clearly and concisely.\n"
        "Focus only on the key points. Remove filler, unnecessary details, or repetition.\n"
        "Make the summary easy to understand while preserving the main ideas.\n\n"
        f"Conversation:\n{data.text}\n\n"
        "Summary:"
    )

    output = generate_llm(prompt, max_tokens=1500)
    return {"summary": output}


# --------------------------------------------------------
# 3) Title Generation
# --------------------------------------------------------
@app.post("/title_generation")
async def title_generation(data: Input):
    prompt = (
        "Generate a short, clear and concise title summarising the content.\n"
        "Keep it 4–8 words. No punctuation at the end.\n\n"
        f"Content:\n{data.text}\n\n"
        "Title:"
    )

    output = generate_llm(prompt, max_tokens=20)
    return {"title": output}