import os
import re

def test_no_hardcoded_secrets():
    # Regex to catch API keys
    key_pattern = re.compile(r'(?i)(api[_-]?key|secret|token|password)[\s:=]+["\']?[a-zA-Z0-9_\-]{20,}["\']?')
    gemini_pattern = re.compile(r'AIzaSy[A-Za-z0-9_-]{33}')
    
    found_secrets = []
    
    # directories to scan
    scan_dirs = ["src", "frontend/src", "scripts"]
    
    for d in scan_dirs:
        for root, _, files in os.walk(d):
            for file in files:
                if file.endswith((".py", ".ts", ".tsx", ".js", ".jsx", ".json")):
                    filepath = os.path.join(root, file)
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        
                    if gemini_pattern.search(content):
                        found_secrets.append(f"Hardcoded Gemini key found in {filepath}")
                    
    assert len(found_secrets) == 0, f"Secrets found: {found_secrets}"
