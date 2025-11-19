# test.py
import re
from .retrieve import answer_query, answer_query_async


# =======================================
# Here are the relevant references from the AIC paper:

# ### References

# - [2] AIC.pdf

def extract_reference(answer: str):
    """
    Extract reference link from RAG text output, if available.
    """
    # search line that is just ### References
    ref_section = re.split(r"### References", answer)
    if len(ref_section) < 2:
        return None
    refs = ref_section[1].strip().splitlines()
    if len(refs) == 0:
        return None
    return refs

def query_endpoint(query: str):
    """
    SYNC version — uses answer_query() wrapper.
    Safe for scripts, NOT for FastAPI.
    """
    resp = answer_query(query, mode="hybrid")
    ref = extract_reference(resp)
    return {"answer": resp, "reference": ref}


async def query_endpoint_async(query: str):
    """
    ASYNC version — safe for FastAPI + uvicorn.
    """
    resp = await answer_query_async(query, mode="hybrid")
    ref = extract_reference(resp)
    return {"answer": resp, "reference": ref}


# DO NOT RUN ANYTHING ON IMPORT
if __name__ == "__main__":
    print(query_endpoint("Test RAG query"))