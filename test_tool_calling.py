import os
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("MY_GRW_API_KEY")

@tool
def get_weather(location: str):
    """Get the weather in a location."""
    return "sunny"

llm = ChatGroq(model="qwen/qwen3.8-27b", api_key=api_key)
llm_with_tools = llm.bind_tools([get_weather])
res = llm_with_tools.invoke("What is the weather in Paris?")
print(f"qwen tool calls: {res.tool_calls}")

llm = ChatGroq(model="openai/gpt-oss-120b", api_key=api_key)
llm_with_tools = llm.bind_tools([get_weather])
res = llm_with_tools.invoke("What is the weather in Paris?")
print(f"gpt-oss tool calls: {res.tool_calls}")
