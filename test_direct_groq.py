import os
import traceback
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

def run_smoke_test():
    api_key = os.getenv("MY_GRW_API_KEY")
    print(f"GROQ API key present: {bool(api_key)}")
    if api_key:
        print(f"GROQ API key length: {len(api_key)}")
    
    model = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")
    print(f"GROQ model: {model}")
    
    try:
        llm = ChatGroq(model=model, api_key=api_key)
        response = llm.invoke("Reply with exactly: GROQ_CONNECTION_OK")
        print(f"Response: {response.content}")
    except Exception as e:
        print(f"Exception occurred: {type(e).__name__} - {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    run_smoke_test()
