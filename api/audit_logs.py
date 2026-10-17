import os
import sys
from pathlib import Path

# Add root folder to sys.path to allow importing auth.py
sys.path.append(str(Path(__file__).parent.parent))

from flask import Flask, request, jsonify
from pymongo import MongoClient
import auth

app = Flask(__name__)

MONGO_URI = os.getenv("MONGO_URI", "")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "askiiita")

@app.route('/api/audit_logs', methods=['GET', 'OPTIONS'])
def audit_logs_endpoint():
    # CORS preflight handling
    if request.method == 'OPTIONS':
        response = app.make_response('')
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
        response.headers.add("Access-Control-Allow-Methods", "GET, OPTIONS")
        return response

    token = request.headers.get("Authorization")
    if token and token.startswith("Bearer "):
        token = token[7:]

    if not token:
        token = request.args.get("token")

    if not token:
        return jsonify({"error": "Unauthorized. Missing authentication token."}), 401

    payload = auth.verify_token(token)
    if not payload:
        return jsonify({"error": "Unauthorized. Invalid or expired token."}), 401

    user_role = payload.get("role")
    if user_role != "admin":
        return jsonify({"error": "Forbidden. Admin privileges required."}), 403

    try:
        try:
            client = MongoClient(
                MONGO_URI, tls=True,
                tlsAllowInvalidCertificates=True,
                tlsAllowInvalidHostnames=True,
                serverSelectionTimeoutMS=2000,
            )
            client.admin.command('ping')
            db = client[MONGO_DB_NAME]
            print("[API AUDIT LOGS] Connected to Atlas MongoDB.")
        except Exception as conn_err:
            print(f"[API AUDIT LOGS DB ERROR] Falling back to mongomock: {conn_err}")
            import mongomock
            client = mongomock.MongoClient()
            db = client[MONGO_DB_NAME]

        audit_col = db["audit_logs"]
        logs = list(audit_col.find({}).sort("timestamp", -1).limit(50))
        
        # Serialize logs to JSON-safe format
        serialized_logs = []
        for log in logs:
            log_entry = {
                "id": str(log.get("_id", "")),
                "user_id": log.get("user_id", ""),
                "role": log.get("role", ""),
                "query_text": log.get("query_text", ""),
                "timestamp": log.get("timestamp").isoformat() if log.get("timestamp") else None,
                "retrieved_chunks": log.get("retrieved_chunks", [])
            }
            serialized_logs.append(log_entry)

        response = jsonify({"audit_logs": serialized_logs})
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response

    except Exception as e:
        return jsonify({"error": f"Internal Server Error: {str(e)}"}), 500

handler = app
