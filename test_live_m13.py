from src.ai.graph import graph
import asyncio

state = {"query": "What groundwater intelligence capabilities are available in this platform?", "messages": []}
result = graph.invoke(state)
print("---")
print(result.get("response", "No response generated."))
print("---")
