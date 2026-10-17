import os
import sys
from pathlib import Path

# Add root folder to sys.path to allow importing auth.py
sys.path.append(str(Path(__file__).parent.parent))

from flask import Flask, request, jsonify
from pymongo import MongoClient
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from datetime import datetime, timezone
import auth

app = Flask(__name__)

MONGO_URI = os.getenv("MONGO_URI", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "askiiita")
MONGO_COLLECTION_NAME = os.getenv("MONGO_COLLECTION_NAME", "documents")
ATLAS_INDEX = os.getenv("ATLAS_VECTOR_SEARCH_INDEX", "vector_index")

@app.route('/api/query', methods=['POST', 'OPTIONS'])
def query_endpoint():
    # CORS preflight handling
    if request.method == 'OPTIONS':
        response = app.make_response('')
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        return response

    data = request.get_json() or {}
    query = data.get("query")
    token = data.get("token") or request.headers.get("Authorization")

    if token and token.startswith("Bearer "):
        token = token[7:]

    if not query:
        return jsonify({"error": "Missing query parameter."}), 400

    if not token:
        return jsonify({"error": "Unauthorized. Missing authentication token."}), 401

    payload = auth.verify_token(token)
    if not payload:
        return jsonify({"error": "Unauthorized. Invalid or expired token."}), 401

    username = payload.get("sub")
    user_role = payload.get("role")

    ROLE_HIERARCHY = {
        "public": ["public"],
        "student": ["public", "student"],
        "faculty": ["public", "student", "faculty"],
        "admin": ["public", "student", "faculty", "admin"]
    }
    allowed_levels = ROLE_HIERARCHY.get(user_role, ["public"])

    use_local_search = False
    client_local = None
    col_local = None
    try:
        client_local = MongoClient(
            MONGO_URI, tls=True,
            tlsAllowInvalidCertificates=True,
            tlsAllowInvalidHostnames=True,
            serverSelectionTimeoutMS=2000,
        )
        client_local.admin.command('ping')
        col_local = client_local[MONGO_DB_NAME][MONGO_COLLECTION_NAME]
    except Exception as conn_err:
        print(f"[API DB] Atlas connection failed for API query: {conn_err}. Using local search.")
        use_local_search = True

    source_docs = []
    if not use_local_search:
        try:
            emb = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001", google_api_key=GEMINI_API_KEY)
            vs  = MongoDBAtlasVectorSearch(collection=col_local, embedding=emb, index_name=ATLAS_INDEX)
            
            # Pre-filtering based on access level
            ret = vs.as_retriever(search_kwargs={
                "k": 4,
                "pre_filter": {
                    "access_level": {"$in": allowed_levels}
                }
            })
            source_docs = ret.invoke(query)
        except Exception as search_err:
            print(f"[API DB] Atlas search execution failed: {search_err}. Falling back to local search.")
            use_local_search = True

    if use_local_search:
        import local_vector
        try:
            source_docs = local_vector.search_local(query, allowed_levels, GEMINI_API_KEY, k=4)
        except Exception as local_err:
            print(f"[API LOCAL ERROR] Local search fallback failed: {local_err}")
            source_docs = []

    try:
        llm = ChatGoogleGenerativeAI(model="gemini-3.8-flash", google_api_key=GEMINI_API_KEY, temperature=0.2)

        today = datetime.now(timezone.utc).strftime("%B %d, %Y")
        prompt = ChatPromptTemplate.from_template(f"""\
You are AskIIITA, a helpful and friendly assistant for IIIT Allahabad students and faculty.
Today's date is {today}. Use this for time-aware answers.
Use ONLY the context below to answer. If info is not in context, say so honestly.
Be concise, accurate, and friendly.

Context:
{{context}}

Question: {{question}}

Answer:""")

        def fmt(docs): return "\n\n".join(d.page_content for d in docs)

        sources = list({doc.metadata.get("source_file", doc.metadata.get("source", "Unknown")) for doc in source_docs})
        context_str = fmt(source_docs) if source_docs else "No relevant documents found for this query/role level."
        chain   = ({"context": lambda x: context_str, "question": RunnablePassthrough()} | prompt | llm | StrOutputParser())
        answer  = chain.invoke(query)

        # Audit logging — only write when Atlas is reachable; skip when using local fallback
        try:
            if not use_local_search and client_local is not None:
                audit_col = client_local[MONGO_DB_NAME]["audit_logs"]
                audit_entry = {
                    "user_id": username,
                    "role": user_role,
                    "query_text": query,
                    "timestamp": datetime.now(timezone.utc),
                    "retrieved_chunks": [
                        {
                            "chunk_id": str(doc.metadata.get("_id") or ""),
                            "source_file": doc.metadata.get("source_file", "Unknown"),
                            "access_level": doc.metadata.get("access_level", "public"),
                            "content_snippet": doc.page_content[:200]
                        } for doc in source_docs
                    ]
                }
                audit_col.insert_one(audit_entry)
            else:
                print(f"[AUDIT] Skipping audit log for '{username}' — Atlas unavailable (local fallback mode).")
        except Exception as audit_err:
            print(f"[AUDIT ERROR] Failed to write audit log: {audit_err}")

        # Add CORS headers
        response = jsonify({"answer": answer, "sources": sources})
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response

    except Exception as e:
        return jsonify({"error": f"Internal Server Error: {str(e)}"}), 500

handler = app
