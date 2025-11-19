from langgraph_runner import run_langgraph

data = {
    "query": "How to fix a sensor?",
    "chat_history": "User: 'Hello'\nBot: 'Hi!'",
    "images_base_64": [],
    "mcp": 1,
    "rag": 1,
    "yt_summary": 0
}

print(run_langgraph(data))
