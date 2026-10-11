import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("MY_GRW_API_KEY")

client = Groq(api_key=api_key)
models = client.models.list()
for m in models.data:
    print(m.id)
