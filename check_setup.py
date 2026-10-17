"""
check_setup.py — AskIIITA
---------------------------
Run this first to verify your environment is configured correctly
before running ingest.py or app.py.

Usage:
    python check_setup.py
"""

import sys
import io

# Force UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def check(label, fn):
    try:
        result = fn()
        print(f"  [OK]  {label}: {result}")
        return True
    except Exception as e:
        print(f"  [!!]  {label}: {e}")
        return False

print("\nAskIIITA -- Setup Checker\n" + "-" * 40)

# 1. Python version
import platform
check("Python version", lambda: platform.python_version())

# 2. .env + env vars
from dotenv import load_dotenv
import os
load_dotenv()
env_ok = all([
    check("MONGO_URI set",       lambda: "✓" if os.environ.get("MONGO_URI")       else (_ for _ in ()).throw(ValueError("Missing MONGO_URI in .env"))),
    check("GEMINI_API_KEY set",  lambda: "✓" if os.environ.get("GEMINI_API_KEY")  else (_ for _ in ()).throw(ValueError("Missing GEMINI_API_KEY in .env"))),
])

# 3. Package imports
pkgs = [
    ("langchain",               "langchain"),
    ("langchain-google-genai",  "langchain_google_genai"),
    ("langchain-mongodb",       "langchain_mongodb"),
    ("pymongo",                 "pymongo"),
    ("pypdf",                   "pypdf"),
    ("streamlit",               "streamlit"),
]
all_pkgs_ok = all(check(f"import {name}", lambda m=mod: __import__(m) and "✓") for name, mod in pkgs)

# 4. MongoDB connectivity
if env_ok:
    from pymongo import MongoClient
    check(
        "MongoDB Atlas ping",
        lambda: (
            MongoClient(os.environ["MONGO_URI"], serverSelectionTimeoutMS=5000)
            .admin.command("ping") and "✓"
        ),
    )

# 5. Gemini API
if env_ok:
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    def test_gemini():
        emb = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
            google_api_key=os.environ["GEMINI_API_KEY"],
        )
        emb.embed_query("test")
        return "✓"
    check("Gemini embedding API", test_gemini)

print("\n" + "-" * 40)
print("If all [OK] -- you're ready! Run:  python ingest.py\n")
