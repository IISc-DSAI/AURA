# from rag.test import query_endpoint_async
import mcp_jiggle

# rag_prompt = "When was BMW E46 lauched? Provide references."
# async def run_rag_async(prompt: str):
#     rag_out = await query_endpoint_async(prompt)
#     response = rag_out["answer"]
#     references = rag_out["reference"]
#     answer_dict = {
#         "response": response,
#         "references": references
#     }
#     return answer_dict

# import asyncio
# response = asyncio.run(run_rag_async(rag_prompt))
# print("=======================================🔴")
# print(response["references"])

import asyncio
from mcp_jiggle import attaching_everything, youtube_summarization

def main():
    result = asyncio.run(attaching_everything("Explain BMW E46 hood workshop position"))
    print(result)
    # response, youtube_videos, links
    youtube_links = result.get("youtube_videos", [])
    summary = asyncio.run(youtube_summarization(youtube_links))
    print(summary)
    
    
if __name__ == "__main__":
    main()


