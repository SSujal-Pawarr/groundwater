import os
from dotenv import load_dotenv
load_dotenv()
from langchain_google_genai import ChatGoogleGenerativeAI

llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash", api_key=os.getenv("MY_GRW_API_KEY"))
print("Direct generation via langchain:")
try:
    response = llm.invoke("What groundwater intelligence capabilities are available in this platform?")
    print(response.content)
except Exception as e:
    print("FAILED DIRECT GENERATION:", e)
