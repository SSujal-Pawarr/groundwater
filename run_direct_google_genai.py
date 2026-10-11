import os
from google import genai
from dotenv import load_dotenv
load_dotenv()
from src.ai.config import config

client = genai.Client(api_key=config.api_key)
response = client.models.generate_content(
    model=config.model_name,
    contents="What groundwater intelligence capabilities are available in this platform?"
)
print("Response from google-genai:", response.text)
