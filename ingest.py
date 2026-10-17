"""
ingest.py -- AskIIITA
--------------------
Load one or more PDF files, split them into chunks,
embed them with Gemini, and upsert into MongoDB Atlas
as vector documents ready for similarity search.

Usage:
    python ingest.py                        # processes all PDFs in ./data/
    python ingest.py data/fee_structure.pdf # processes a single file
"""

import os
import sys
import glob
import io
import warnings
from pathlib import Path

# Fix Windows UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings("ignore", category=DeprecationWarning)

from dotenv import load_dotenv
from pymongo import MongoClient
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_mongodb import MongoDBAtlasVectorSearch

# -- 1. Load environment -------------------------------------------------------
load_dotenv(override=True)

MONGO_URI             = os.environ["MONGO_URI"]
GEMINI_API_KEY        = os.environ["GEMINI_API_KEY"]
MONGO_DB_NAME         = os.getenv("MONGO_DB_NAME",        "askiiita")
MONGO_COLLECTION_NAME = os.getenv("MONGO_COLLECTION_NAME", "documents")
ATLAS_VECTOR_SEARCH_INDEX = os.getenv("ATLAS_VECTOR_SEARCH_INDEX", "vector_index")

print(f"[ENV] Loaded GEMINI_API_KEY: {GEMINI_API_KEY[:8]}...{GEMINI_API_KEY[-4:]}")

from langchain_community.document_loaders import PyPDFLoader, TextLoader

# -- 2. Pick files to ingest ---------------------------------------------------
if len(sys.argv) > 1:
    file_paths = sys.argv[1:]
else:
    file_paths = glob.glob("data/*.pdf") + glob.glob("data/*.txt")

if not file_paths:
    print("ERROR: No PDF or TXT files found. Put files in ./data/ or pass paths as arguments.")
    sys.exit(1)

print(f"[FILES] Found {len(file_paths)} file(s) to ingest: {[Path(p).name for p in file_paths]}")

# -- 3. Load & split -----------------------------------------------------------
splitter = RecursiveCharacterTextSplitter(
    chunk_size=3200,
    chunk_overlap=200,
    separators=["\n\n", "\n", " ", ""],
)

# Filename-to-role mapping
MAPPING = {
    # Public
    "Academic Calendar (Except For Fresher Batch) Jan to December 2026.pdf": "public",
    "B Tech.pdf": "public",
    "DD M Tech Phd.pdf": "public",
    "General Library Rules & Regulations.pdf": "public",
    "Gymkhana Constitution Draft final.pdf": "public",
    "IHC Schedule 01072025.pdf": "public",
    "INSTITUTE PHARMACY_14.08.2025 (1).pdf": "public",
    "M Tech & M Tech (WP).pdf": "public",
    "NEP Ordinance adob updated.pdf": "public",
    "Phd & WP (1).pdf": "public",
    "Phd & WP.pdf": "public",
    "Phd Regular & WP.pdf": "public",
    "Placement_Brochure_2026-27.pdf": "public",
    # Student
    "Fee Structure B.Tech. (New Batch 2026) updated.pdf": "student",
    "Gmail - Reminder_ Student Code of Conduct at IIIT Allahabad_260706201503.pdf": "student",
    "Hostel_Manual655.pdf": "student",
    "Library Orientation-2024-UG+PG.pdf": "student",
    "Salient_Points_&_Examination Guidelines for Students 2025_F.pdf": "student",
    "UG B,Tech  Curriculum 2025.pdf": "student",
    # Faculty
    "people_directory.txt": "faculty"
}

all_chunks = []
for path in file_paths:
    print(f"   Loading: {path}")
    if path.endswith(".pdf"):
        loader = PyPDFLoader(path)
        pages  = loader.load()
    elif path.endswith(".txt"):
        loader = TextLoader(path, encoding='utf-8')
        pages  = loader.load()
    else:
        print(f"   Skip unsupported file format: {path}")
        continue
        
    chunks = splitter.split_documents(pages)
    for chunk in chunks:
        filename = Path(path).name
        chunk.metadata["source_file"] = filename
        chunk.metadata["access_level"] = MAPPING.get(filename, "public")
    all_chunks.extend(chunks)
    print(f"   -> {len(pages)} pages/documents -> {len(chunks)} chunks")

print(f"\n[OK]  Total chunks ready for embedding: {len(all_chunks)}")

# -- 4. Embed & store ----------------------------------------------------------
print("[DB]  Connecting to MongoDB Atlas ...")
client = MongoClient(
    MONGO_URI,
    tls=True,
    tlsAllowInvalidCertificates=True,
    tlsAllowInvalidHostnames=True,
    serverSelectionTimeoutMS=30000,
)
collection = client[MONGO_DB_NAME][MONGO_COLLECTION_NAME]
print("[DB]  Clearing existing collection to ensure a clean index...")
collection.delete_many({})

print("[AI]  Initialising Gemini embeddings (models/gemini-embedding-001) ...")
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001",
    google_api_key=GEMINI_API_KEY,
)

import time

print("[UP]  Upserting chunks into Atlas (batching to avoid rate limits) ...")
vector_store = MongoDBAtlasVectorSearch(
    collection=collection,
    embedding=embeddings,
    index_name=ATLAS_VECTOR_SEARCH_INDEX,
)

batch_size = 50
total_batches = (len(all_chunks) - 1) // batch_size + 1

for i in range(0, len(all_chunks), batch_size):
    batch = all_chunks[i:i + batch_size]
    batch_num = i // batch_size + 1
    print(f"      Sending batch {batch_num}/{total_batches} ({len(batch)} chunks)...")
    max_retries = 5
    success = False
    for attempt in range(1, max_retries + 1):
        try:
            vector_store.add_documents(batch)
            success = True
            break
        except Exception as e:
            err_msg = str(e)
            if attempt == max_retries:
                print(f"      ERROR: Batch {batch_num} failed after {max_retries} attempts. Skipping. Last error: {e}")
                break
            if "RESOURCE_EXHAUSTED" in err_msg or "429" in err_msg:
                print(f"      Rate limit hit (attempt {attempt}/{max_retries})! Sleeping for 30 seconds before retrying...")
                time.sleep(30)
            elif "getaddrinfo failed" in err_msg or "ConnectError" in err_msg or "11001" in err_msg:
                print(f"      Connection issue (attempt {attempt}/{max_retries})! Sleeping for 15 seconds before retrying...")
                time.sleep(15)
            else:
                print(f"      Transient error (attempt {attempt}/{max_retries}): {e}. Retrying in 10 seconds...")
                time.sleep(10)
    if success:
        time.sleep(2)  # Short delay between successful batches

print(f"\n[DONE]  Successfully processed and stored {len(all_chunks)} chunks in '{MONGO_DB_NAME}.{MONGO_COLLECTION_NAME}'.")
