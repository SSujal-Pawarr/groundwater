import time
from src.ai.graph import graph
import asyncio

queries = [
    "What is the dynamic groundwater resource assessment of India?",
    "What does the National Water Policy say about groundwater management?",
    "What groundwater monitoring information is available for Maharashtra?",
    "What is the groundwater condition of candidate site W28581, and what does the official documentation say about groundwater management?"
]

for i, q in enumerate(queries):
    print(f"\n--- Query {i+1} ---")
    print(f"Q: {q}")
    state = {"query": q, "messages": []}
    try:
        result = graph.invoke(state)
        print("Response:")
        print(result.get("response", "No response generated."))
    except Exception as e:
        print(f"Error: {e}")
    print("-------------------")
    if i < len(queries) - 1:
        print("Sleeping 15 seconds to avoid rate limits...")
        time.sleep(15)
