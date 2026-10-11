import os
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("MY_GRW_API_KEY")

models_to_try = [
    "llama3-8b-8192",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
    "llama-3.2-1b-preview",
    "llama-3.2-3b-preview",
    "llama-3.2-11b-vision-preview",
    "llama-3.2-90b-vision-preview"
]

for m in models_to_try:
    try:
        print(f"Trying {m}...")
        llm = ChatGroq(model=m, api_key=api_key)
        res = llm.invoke("Hello")
        print(f"Success with {m}: {res.content[:20]}")
    except Exception as e:
        print(f"Failed {m}: {type(e).__name__}")
