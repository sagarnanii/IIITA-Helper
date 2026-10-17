import os
import json
import numpy as np
from pathlib import Path
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader

CACHE_DIR = Path("scratch")
CACHE_FILE = CACHE_DIR / "local_vector_cache.json"

# Filename-to-role mapping
MAPPING = {
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
    
    "Fee Structure B.Tech. (New Batch 2026) updated.pdf": "student",
    "Gmail - Reminder_ Student Code of Conduct at IIIT Allahabad_260706201503.pdf": "student",
    "Hostel_Manual655.pdf": "student",
    "Library Orientation-2024-UG+PG.pdf": "student",
    "Salient_Points_&_Examination Guidelines for Students 2025_F.pdf": "student",
    "UG B,Tech  Curriculum 2025.pdf": "student",
    
    "people_directory.txt": "faculty"
}

def cosine_similarity(v1, v2):
    dot = np.dot(v1, v2)
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(dot / (norm1 * norm2))

def build_local_cache(gemini_key: str):
    """Parse local documents, generate embeddings, and write to cache."""
    print("[LOCAL-VS] Rebuilding local vector cache...")
    CACHE_DIR.mkdir(exist_ok=True)
    
    # 1. Discover files
    import glob
    file_paths = glob.glob("data/*.pdf") + glob.glob("data/*.txt")
    if not file_paths:
        print("[LOCAL-VS] Warning: No PDF or TXT files found in data/")
        return []

    # 2. Setup text splitter
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=3200,
        chunk_overlap=200,
        separators=["\n\n", "\n", " ", ""],
    )

    all_chunks = []
    for path in file_paths:
        filename = Path(path).name
        level = MAPPING.get(filename, "public")
        
        try:
            if path.endswith(".pdf"):
                loader = PyPDFLoader(path)
                pages = loader.load()
            else:
                loader = TextLoader(path, encoding='utf-8')
                pages = loader.load()
            
            chunks = splitter.split_documents(pages)
            for chunk in chunks:
                chunk.metadata["source_file"] = filename
                chunk.metadata["access_level"] = level
            all_chunks.extend(chunks)
        except Exception as e:
            print(f"[LOCAL-VS] Error loading {filename}: {e}")

    if not all_chunks:
        return []

    # 3. Generate embeddings
    embeddings_model = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        google_api_key=gemini_key
    )

    print(f"[LOCAL-VS] Embedding {len(all_chunks)} chunks...")
    cache_data = []
    
    # Embed in batches to avoid API rate limits
    import time
    batch_size = 50
    for idx in range(0, len(all_chunks), batch_size):
        batch = all_chunks[idx : idx + batch_size]
        texts = [doc.page_content for doc in batch]
        
        retries = 3
        embedded = False
        while retries > 0:
            try:
                vectors = embeddings_model.embed_documents(texts)
                for doc, vec in zip(batch, vectors):
                    cache_data.append({
                        "text": doc.page_content,
                        "embedding": vec,
                        "metadata": doc.metadata
                    })
                embedded = True
                break
            except Exception as e:
                print(f"[LOCAL-VS] Embedding failed: {e}. Retrying...")
                time.sleep(5)
                retries -= 1
        if not embedded:
            print(f"[LOCAL-VS] WARNING: Batch starting at index {idx} failed after 3 retries. "
                  f"Skipping {len(batch)} chunks — local search results may be incomplete.")
        time.sleep(1)

    # 4. Save to file
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache_data, f)
    print(f"[LOCAL-VS] Successfully cached {len(cache_data)} chunks to {CACHE_FILE}")
    return cache_data

def get_cached_documents(gemini_key: str):
    """Load cached document chunks. Rebuild cache if it doesn't exist."""
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[LOCAL-VS] Error reading cache file: {e}")
    
    return build_local_cache(gemini_key)

def search_local(query: str, allowed_levels: list, gemini_key: str, k: int = 4) -> list[Document]:
    """Perform a local in-memory cosine similarity search over cached embeddings."""
    chunks = get_cached_documents(gemini_key)
    if not chunks:
        return []

    # 1. Embed query
    embeddings_model = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        google_api_key=gemini_key
    )
    query_vector = embeddings_model.embed_query(query)

    # 2. Filter by access levels and calculate similarity
    matches = []
    for chunk in chunks:
        meta = chunk.get("metadata", {})
        chunk_level = meta.get("access_level", "public")
        
        if chunk_level in allowed_levels:
            sim = cosine_similarity(query_vector, chunk.get("embedding", []))
            matches.append((sim, chunk))

    # 3. Sort by similarity descending
    matches.sort(key=lambda x: x[0], reverse=True)
    
    # 4. Convert top-k to LangChain Document objects
    results = []
    for sim, chunk in matches[:k]:
        doc = Document(
            page_content=chunk.get("text", ""),
            metadata=chunk.get("metadata", {})
        )
        results.append(doc)
        
    return results
