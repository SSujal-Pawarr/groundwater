import os
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
api_key = os.getenv("MY_GRW_API_KEY")

client = Groq(api_key=api_key)
models = client.models.list()

for m in models.data:
    if "whisper" in m.id or "prompt-guard" in m.id:
        continue
    print(f"Trying {m.id}...")
    try:
        llm = ChatGroq(model=m.id, api_key=api_key)
        res = llm.invoke("Hello, who are you?")
        print(f"Success with {m.id}: {res.content[:50]}")
    except Exception as e:
        print(f"Failed {m.id}: {type(e).__name__} - {str(e)}")
