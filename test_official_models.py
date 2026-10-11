import os
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("MY_GRW_API_KEY")

for m in ["llama-3.1-8b-instant", "mixtral-8x7b-32768"]:
    try:
        print(f"Trying {m}...")
        llm = ChatGroq(model=m, api_key=api_key)
        res = llm.invoke("Hello, who are you?")
        print(f"Success with {m}: {res.content[:50]}")
    except Exception as e:
        print(f"Failed {m}: {type(e).__name__} - {str(e)}")
