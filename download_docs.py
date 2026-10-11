import urllib.request
import hashlib
import os
import shutil
import ssl

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
    print(f"Downloading {doc['url']} to {doc['file']}...")
    req = urllib.request.Request(doc["url"], headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as response, open(doc["file"], 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
        
        # Hash it
        hasher = hashlib.sha256()
        with open(doc["file"], 'rb') as f:
            hasher.update(f.read())
        print(f"SHA256: {hasher.hexdigest()}")
    except Exception as e:
        print(f"Failed: {e}")
