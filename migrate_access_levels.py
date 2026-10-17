import os
import sys
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "askiiita")
MONGO_COLLECTION_NAME = os.getenv("MONGO_COLLECTION_NAME", "documents")

if not MONGO_URI:
    print("ERROR: MONGO_URI environment variable is not set.")
    sys.exit(1)

# Mapping of file names to their access level
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

def main():
    print(f"[MIGRATION] Connecting to MongoDB: {MONGO_DB_NAME}...")
    client = MongoClient(
        MONGO_URI,
        tls=True,
        tlsAllowInvalidCertificates=True,
        tlsAllowInvalidHostnames=True,
    )
    
    db = client[MONGO_DB_NAME]
    col = db[MONGO_COLLECTION_NAME]
    
    total_documents = col.count_documents({})
    print(f"[MIGRATION] Total chunks found: {total_documents}")
    
    # 1. Update based on mapping
    total_updated = 0
    for filename, level in MAPPING.items():
        # MongoDBAtlasVectorSearch stores source_file and access_level as top-level fields
        query = {"source_file": filename}
        update = {"$set": {"access_level": level}}
        result = col.update_many(query, update)
        print(f"  Mapped {filename} -> {level} (Matched: {result.matched_count}, Modified: {result.modified_count})")
        total_updated += result.modified_count
        
    # 2. Set default fallback for anything else
    query_fallback = {"access_level": {"$exists": False}}
    update_fallback = {"$set": {"access_level": "public"}}
    result_fallback = col.update_many(query_fallback, update_fallback)
    print(f"  Fallback default 'public' assigned (Matched: {result_fallback.matched_count}, Modified: {result_fallback.modified_count})")
    total_updated += result_fallback.modified_count
    
    print(f"\n[DONE] Migration complete. Updated {total_updated} chunks.")

if __name__ == "__main__":
    main()
