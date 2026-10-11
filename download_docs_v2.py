import urllib.request
import hashlib
import os
import ssl
import sys

ssl._create_default_https_context = ssl._create_unverified_context

docs = [
    {
        "url": "https://cgwb.gov.in/cgwbpnm/download/1141",
        "file": "data/rag/documents/cgwb_dynamic_groundwater_resources_india_2023.pdf"
    },
    {
        "url": "https://www.jalshakti-dowr.gov.in/static/uploads/2024/02/2023020993.pdf",
        "file": "data/rag/documents/national_water_policy_2012.pdf"
    },
    {
        "url": "https://cgwb.gov.in/cgwbpnm/download/1687",
        "file": "data/rag/documents/cgwb_groundwater_yearbook_maharashtra_2023_24.pdf"
    }
]

os.makedirs("data/rag/documents", exist_ok=True)

for doc in docs:
    print(f"Downloading {doc['url']} to {doc['file']}...", flush=True)
    req = urllib.request.Request(doc["url"], headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'})
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read()
            with open(doc["file"], 'wb') as out_file:
                out_file.write(content)
        
        hasher = hashlib.sha256()
        hasher.update(content)
        print(f"SHA256: {hasher.hexdigest()}", flush=True)
    except Exception as e:
        print(f"Failed: {e}", flush=True)
