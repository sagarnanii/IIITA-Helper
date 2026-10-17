# AskIIITA

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://askiiita.streamlit.app/)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Google Gemini](https://img.shields.io/badge/LLM-Gemini%203.8%20Flash-4285F4.svg)](https://ai.google.dev/)
[![MongoDB Atlas](https://img.shields.io/badge/Vector%20DB-MongoDB%20Atlas-47A248.svg)](https://www.mongodb.com/atlas)

> An intelligent, role-aware RAG campus assistant for the Indian Institute of Information Technology, Allahabad (IIIT Allahabad). Ask questions regarding academics, hostel rules, fee structures, ordinances, placements, campus healthcare, and faculty directories with strict role-based document access control.

---

## Overview

AskIIITA bridges the gap between campus documentation and community members. Built with a modern web interface inspired by clean, minimalist dashboard designs, AskIIITA combines Google Gemini, MongoDB Atlas Vector Search, and LangChain to provide grounded, source-backed answers tailored to each user's clearance level.

### Key Features

- **Role-Based Access Control (RBAC):** Hierarchical permissions across four clearance tiers:
  - `public`: General academic calendars, program ordinances, brochures, general library rules.
  - `student`: Detailed fee schedules, student codes of conduct, hostel manuals, exam guidelines.
  - `faculty`: Faculty directories, staff records, and internal institutional documents.
  - `admin`: Full document visibility and administrative access to query audit logs.
- **Dual Retrieval Engine:**
  - **Primary:** MongoDB Atlas Vector Search utilizing vector pre-filtering on `access_level`.
  - **Resilient Fallback:** Automated local in-memory cosine similarity cache (`local_vector.py`) for zero-downtime offline execution.
- **Auditing & Governance:** Every query, authenticated user ID, role, timestamp, and retrieved document chunk is recorded in MongoDB for institutional compliance and performance monitoring.
- **Clean Interface:** Designed with a soft canvas, vector SVG category tiles, circular send actions, a 3D animated campus mascot with head-nodding micro-animations, and zero visual clutter.
- **Interactive FAQs:** Categorized quick-inquiry modules for Academics, Hostel Life, Fees & Grants, Placements, Healthcare, and Regulations.
- **Dual-Interface Architecture:** Use either the Streamlit web application or the headless serverless REST API (`api/` endpoints).

---

## Tech Stack

| Layer | Technology | Description |
|---|---|---|
| **Frontend** | Streamlit | Custom styling, glassmorphism surfaces, responsive CSS animations |
| **Large Language Model** | Google Gemini 3.8 Flash | High-speed, context-grounded reasoning (`gemini-3.8-flash`) |
| **Embeddings** | Google Gemini Embeddings | 3072-dimensional vector representations (`models/gemini-embedding-001`) |
| **Vector Database** | MongoDB Atlas | Cloud vector search with metadata pre-filtering |
| **Orchestration** | LangChain | Document parsing, text chunking, and RAG retrieval pipelines |
| **Security & Auth** | PBKDF2 + PyJWT | Salted password hashing and 24-hour signed JWT access tokens |
| **API Layer** | Flask / Vercel Serverless | REST endpoints for authentication, queries, and audit logging |

---

## Architecture Flow

```
                      +-----------------------------+
                      | User / Client (Web or REST) |
                      +--------------+--------------+
                                     |
                         [JWT Auth & Role Check]
                                     |
                                     v
                  +-----------------------------------+
                  |   Gemini Embedding Generation     |
                  |  (models/gemini-embedding-001)   |
                  +------------------+----------------+
                                     |  3072-dim vector
                                     v
                      +-------------------------------+
                      |   MongoDB Atlas Vector Search |
                      |   Pre-filter: access_level in |
                      |         [allowed_roles]       |
                      +---------------+---------------+
                                      |
                        Top-4 Document Chunks
                                      |
                                      v
                      +-------------------------------+
                      |   Gemini 3.8 Flash LLM        |
                      |   System Prompt + Context     |
                      +---------------+---------------+
                                      |
                                      v
                      +-------------------------------+
                      | Grounded Answer + Source Docs |
                      +---------------+---------------+
                                      |
                           [Audit Log to Atlas]
```

---

## Project Structure

```
ASKIIITA/
├── app.py                      # Streamlit frontend with modern UI & animated mascot
├── auth.py                     # JWT token management, user seeding & password hashing
├── check_setup.py              # Pre-flight environment & connection verification script
├── ingest.py                   # PDF/TXT ingestion pipeline with access level tagging
├── local_vector.py             # Local vector search fallback & in-memory cache
├── migrate_access_levels.py    # Database migration utility for document access tags
├── requirements.txt            # Python package dependencies
├── vercel.json                 # Vercel serverless deployment configuration
├── .env                        # Environment secrets (ignored in version control)
│
├── api/                        # Serverless REST API endpoints
│   ├── login.py                # POST /api/login (User authentication & JWT issue)
│   ├── register.py             # POST /api/register (Account registration)
│   ├── query.py                # POST /api/query (Role-aware RAG query pipeline)
│   └── audit_logs.py           # GET /api/audit_logs (Admin query audit trail)
│
├── data/                       # Source institutional PDFs and text directories
└── images/                     # UI visual assets and 3D animated mascot avatar
```

---

## Quick Start

### 1. Prerequisites

- Python 3.10, 3.11, or 3.12
- A free [MongoDB Atlas](https://cloud.mongodb.com/) cluster
- A [Google AI Studio](https://aistudio.google.com/) API Key

### 2. Clone and Setup Environment

```bash
git clone https://github.com/Adityajakkula7/ASKIIITA.git
cd ASKIIITA

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate       # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the project root:

```env
MONGO_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority
GEMINI_API_KEY=AIzaSy...your_gemini_api_key_here
MONGO_DB_NAME=askiiita
MONGO_COLLECTION_NAME=documents
ATLAS_VECTOR_SEARCH_INDEX=vector_index
JWT_SECRET=your_super_secret_jwt_random_string_here
```

### 4. Configure MongoDB Atlas Vector Search Index

1. Log in to [cloud.mongodb.com](https://cloud.mongodb.com) and navigate to your cluster.
2. Under **Database**, open the **Atlas Search** tab and click **Create Search Index**.
3. Choose **Atlas Vector Search** (JSON Editor).
4. Select database `askiiita` and collection `documents`.
5. Set the index name to `vector_index` (matching `ATLAS_VECTOR_SEARCH_INDEX`).
6. Paste the following configuration:

```json
{
  "fields": [
    {
      "type": "vector",
      "path": "embedding",
      "numDimensions": 3072,
      "similarity": "cosine"
    },
    {
      "type": "filter",
      "path": "access_level"
    }
  ]
}
```

> **Important:** The `numDimensions` must be set to `3072` to match `gemini-embedding-001`. The `access_level` filter field is required for role-based pre-filtering.

### 5. Run the Pre-Flight Verification

Verify your environment variables, package dependencies, MongoDB Atlas connection, and Gemini API access:

```bash
python check_setup.py
```

Ensure all checks report `[OK]`.

### 6. Ingest Campus Documents

Place your campus PDF files and directories in `./data/`, then execute the ingestion script:

```bash
# Ingest all documents in ./data/
python ingest.py

# Or ingest a single file
python ingest.py "data/Fee Structure B.Tech. (New Batch 2026) updated.pdf"
```

The ingestion pipeline will:
- Parse documents and generate chunks with overlap.
- Map files to access levels (`public`, `student`, `faculty`).
- Generate 3072-dimensional vector embeddings with Gemini.
- Store chunks and metadata in MongoDB Atlas.

### 7. Launch the Application

```bash
streamlit run app.py
```

Access the dashboard at `http://localhost:8501`.

---

## Default Test Accounts

When connecting for the first time, default accounts are seeded automatically for testing role clearances:

| Username | Password | Role | Access Scope |
|---|---|---|---|
| `student_test` | `student123` | Student | Public + Student documents (hostel, fees, conduct) |
| `faculty_test` | `faculty123` | Faculty | Public + Student + Faculty documents |
| `admin_test` | `admin123` | Admin | Complete access + Audit Logs dashboard |

You can also register a new account directly from the application login screen.

---

## REST API Reference

The project includes serverless REST endpoints compatible with local Flask execution and Vercel:

### 1. User Login
- **Endpoint:** `POST /api/login`
- **Request Body:**
  ```json
  {
    "username": "student_test",
    "password": "student123"
  }
  ```
- **Response:**
  ```json
  {
    "token": "eyJhbGciOi...",
    "username": "student_test",
    "role": "student"
  }
  ```

### 2. Query Knowledge Base
- **Endpoint:** `POST /api/query`
- **Headers:** `Authorization: Bearer <token>`
- **Request Body:**
  ```json
  {
    "query": "What are the hostel check-in hours and leave procedures?"
  }
  ```
- **Response:**
  ```json
  {
    "answer": "According to the IIIT Allahabad Hostel Manual...",
    "sources": ["Hostel_Manual655.pdf"]
  }
  ```

### 3. Query Audit Logs (Admin Only)
- **Endpoint:** `GET /api/audit_logs`
- **Headers:** `Authorization: Bearer <admin_token>`
- **Response:**
  ```json
  {
    "audit_logs": [
      {
        "id": "671...",
        "user_id": "student_test",
        "role": "student",
        "query_text": "fee deadline",
        "timestamp": "2026-10-18T03:30:00Z",
        "retrieved_chunks": [...]
      }
    ]
  }
  ```

---

## Deployment Options

### Streamlit Community Cloud

1. Push your code to your GitHub repository.
2. Sign in to [share.streamlit.io](https://share.streamlit.io/).
3. Select your repository, branch (`main`), and set Main file path to `app.py`.
4. Open **Advanced settings** -> **Secrets** and enter:
   ```toml
   MONGO_URI = "mongodb+srv://..."
   GEMINI_API_KEY = "AIzaSy..."
   MONGO_DB_NAME = "askiiita"
   MONGO_COLLECTION_NAME = "documents"
   ATLAS_VECTOR_SEARCH_INDEX = "vector_index"
   JWT_SECRET = "your_strong_secret_key"
   ```
5. Click **Deploy**.

### Vercel Serverless

The repository includes a pre-configured `vercel.json` defining Python serverless routes for the `/api/*` endpoints. To deploy:

```bash
npm install -g vercel
vercel
```

Add your environment variables in the Vercel Project Settings.

---

## License

This project is developed for educational and institutional assistance at IIIT Allahabad. Distributed under the MIT License.
