import os
from google import genai
from dotenv import load_dotenv
load_dotenv()
from src.ai.config import config

client = genai.Client(api_key=config.api_key)
chat = client.chats.create(model='gemini-3.5-flash')
response = chat.send_message("What groundwater intelligence capabilities are available in this platform?")
print("Response from gemini-3.5-flash:", response.text)
