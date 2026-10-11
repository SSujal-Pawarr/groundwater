import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
from src.ai.graph import graph
from src.ai.state import AgentState

print("Starting direct LangGraph query test...")
initial_state = {
    "query": "Hello, what can you help me with?",
    "candidate_site_id": None,
    "intent": None,
    "tool_calls": [],
    "tool_results": [],
    "evidence": [],
    "response": None,
    "errors": [],
    "messages": []
}

res = graph.invoke(initial_state)
print("Response:", res.get("response"))
print("Errors:", res.get("errors"))

print("\nStarting real project query test...")
initial_state_2 = {
    "query": "User Selected Site Context: W28581\nUser Query: What is the condition and early warning alert for this site?",
    "candidate_site_id": "W28581",
    "intent": None,
    "tool_calls": [],
    "tool_results": [],
    "evidence": [],
    "response": None,
    "errors": [],
    "messages": []
}

res_2 = graph.invoke(initial_state_2)
print("Response:", res_2.get("response"))
print("Evidence:", [e.get("tool") for e in res_2.get("evidence", [])])
print("Errors:", res_2.get("errors"))
