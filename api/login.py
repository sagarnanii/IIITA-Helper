import os
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from flask import Flask, request, jsonify
from pymongo import MongoClient
import auth

app = Flask(__name__)
MONGO_URI = os.getenv("MONGO_URI", "")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "askiiita")

@app.route('/api/login', methods=['POST', 'OPTIONS'])
def login_endpoint():
    if request.method == 'OPTIONS':
        res = app.make_response('')
        res.headers.add("Access-Control-Allow-Origin", "*")
        res.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
        res.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        return res

    data = request.get_json() or {}
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Missing username or password."}), 400

    try:
        # Check connection
        try:
            client = MongoClient(
                MONGO_URI, tls=True,
                tlsAllowInvalidCertificates=True,
                tlsAllowInvalidHostnames=True,
                serverSelectionTimeoutMS=2000,
            )
            client.admin.command('ping')
            db = client[MONGO_DB_NAME]
            print("[API LOGIN] Connected to Atlas MongoDB.")
        except Exception as conn_err:
            print(f"[API LOGIN DB ERROR] Falling back to mongomock: {conn_err}")
            import mongomock
            client = mongomock.MongoClient()
            db = client[MONGO_DB_NAME]
        
        # Seed in-memory db in case it's a fallback database
        auth.seed_default_users(db)
        
        user_doc = auth.get_user(db, username)
        if user_doc and auth.verify_password(password, user_doc["password_salt"], user_doc["password_hash"]):
            token = auth.generate_token(username, user_doc["role"])
            response = jsonify({"token": token, "username": username, "role": user_doc["role"]})
            response.headers.add("Access-Control-Allow-Origin", "*")
            return response
        else:
            return jsonify({"error": "Invalid username or password."}), 401
    except Exception as e:
        return jsonify({"error": f"Database Error: {str(e)}"}), 500

handler = app
