import os
from dotenv import load_dotenv
load_dotenv()
from langchain_google_genai import ChatGoogleGenerativeAI
from src.ai.config import config

llm = ChatGoogleGenerativeAI(model=config.model_name, api_key=config.api_key)
print("Direct generation:")
try:
    response = llm.invoke("What groundwater intelligence capabilities are available in this platform?")
    print(response.content)
except Exception as e:
    print("FAILED DIRECT GENERATION:", e)
