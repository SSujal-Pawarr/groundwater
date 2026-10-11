import os
from google import genai
from dotenv import load_dotenv
load_dotenv()
from src.ai.config import config

client = genai.Client(api_key=config.api_key)
for m in client.models.list():
    if 'embed' in m.name.lower() or 'embedding' in m.name.lower():
        print(m.name, m.supported_actions)
