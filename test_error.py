import os
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("MY_GRW_API_KEY")

try:
    llm = ChatGroq(model="llama3-8b-8192", api_key=api_key)
    res = llm.invoke("Hello")
except Exception as e:
    print(str(e))
