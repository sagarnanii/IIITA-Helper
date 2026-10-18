"""
app.py -- AskIIITA
Modern, clean University Campus Helper Chatbot App UI for IIIT Allahabad.
Clean minimal aesthetics, custom circular action buttons, and animated 3D mascot.
Run: streamlit run app.py
"""

import os
import base64
import warnings
from datetime import date
from pathlib import Path

warnings.filterwarnings("ignore", category=DeprecationWarning)

import streamlit as st
from dotenv import load_dotenv

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AskIIITA – Campus Assistant",
    page_icon="images/mascot.jpg" if Path("images/mascot.jpg").exists() else None,
    layout="wide",
    initial_sidebar_state="collapsed",
)

load_dotenv(override=True)
MONGO_URI             = os.getenv("MONGO_URI", "")
GEMINI_API_KEY        = os.getenv("GEMINI_API_KEY", "")
MONGO_DB_NAME         = os.getenv("MONGO_DB_NAME", "askiiita")
MONGO_COLLECTION_NAME = os.getenv("MONGO_COLLECTION_NAME", "documents")
ATLAS_INDEX           = os.getenv("ATLAS_VECTOR_SEARCH_INDEX", "vector_index")

import auth
from pymongo import MongoClient

# Initialize MongoDB client for authentication/seeding/audit logs
try:
    client = MongoClient(
        MONGO_URI, tls=True,
        tlsAllowInvalidCertificates=True,
        tlsAllowInvalidHostnames=True,
        serverSelectionTimeoutMS=2000,
    )
    client.admin.command('ping')
    db = client[MONGO_DB_NAME]
    auth.seed_default_users(db)
    is_mock_db = False
    print("[DB] Connected to MongoDB Atlas successfully.")
except Exception as db_err:
    import mongomock
    client = mongomock.MongoClient()
    db = client[MONGO_DB_NAME]
    auth.seed_default_users(db)
    is_mock_db = True
    print(f"[DB ERROR] MongoDB connection failed: {db_err}. Falling back to mongomock.")


# ── Load images as base64 ────────────────────────────────────────────────────
def img_to_b64(path: str) -> str:
    p = Path(path)
    if p.exists():
        return base64.b64encode(p.read_bytes()).decode()
    return ""

b64_mascot = img_to_b64("images/mascot.jpg")
mascot_src = f"data:image/jpeg;base64,{b64_mascot}" if b64_mascot else ""


# ── Category definitions (With Clean Vector SVG Icons, Zero Placeholders) ─────
CATEGORIES = {
    "Academics": {
        "svg": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg>',
        "tag": "Academics",
        "color": "linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)",
        "bg_soft": "rgba(99, 102, 241, 0.08)",
        "desc": "Programs, curriculum, grading rules and exams",
        "questions": [
            "What B.Tech and M.Tech programs are offered at IIITA?",
            "When does the current semester end?",
            "What is the grading system and CGPA calculation at IIITA?",
            "What is the admission and eligibility criteria for M.Tech?",
        ],
    },
    "Fees and Dues": {
        "svg": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="1" y="4" width="22" height="16" rx="2" ry="2"></rect><line x1="1" y1="10" x2="23" y2="10"></line></svg>',
        "tag": "Fees",
        "color": "linear-gradient(135deg, #10b981 0%, #059669 100%)",
        "bg_soft": "rgba(16, 185, 129, 0.08)",
        "desc": "Semester fees, one-time deposits and batch dues",
        "questions": [
            "What are the one time fees for B.Tech 2026?",
            "What are the semester tuition and exam fees?",
            "What are the annual and gymkhana dues?",
            "What is the total fee structure for B.Tech?",
        ],
    },
    "Calendar": {
        "svg": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>',
        "tag": "Calendar",
        "color": "linear-gradient(135deg, #f59e0b 0%, #d97706 100%)",
        "bg_soft": "rgba(245, 158, 11, 0.08)",
        "desc": "Key dates, semester timelines and exam holidays",
        "questions": [
            "When does the upcoming semester start?",
            "What are the official campus holidays?",
            "When are the mid-semester exams scheduled?",
            "What is the summer semester schedule and registration date?",
        ],
    },
    "Hostels and Mess": {
        "svg": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg>',
        "tag": "Hostels",
        "color": "linear-gradient(135deg, #f43f5e 0%, #e11d48 100%)",
        "bg_soft": "rgba(244, 63, 94, 0.08)",
        "desc": "Room allotments, warden rules and mess facilities",
        "questions": [
            "What are the hostel room allotment rules?",
            "What are the hostel and mess charges per semester?",
            "What are the hostel in-out timings and curfew rules?",
            "What amenities and sports are inside student hostels?",
        ],
    },
    "Library": {
        "svg": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path></svg>',
        "tag": "Academics",
        "color": "linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%)",
        "bg_soft": "rgba(139, 92, 246, 0.08)",
        "desc": "Digital library, book borrowing and timing",
        "questions": [
            "What are the central library working hours and reading room timings?",
            "How many books can a B.Tech or M.Tech student borrow at a time?",
            "What is the late book return fine policy?",
            "How can I access IEEE, Springer, and online journal databases?",
        ],
    },
    "Placements": {
        "svg": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path></svg>',
        "tag": "Career",
        "color": "linear-gradient(135deg, #06b6d4 0%, #0891b2 100%)",
        "bg_soft": "rgba(6, 182, 212, 0.08)",
        "desc": "Recruiters, packages, internships and statistics",
        "questions": [
            "What top companies recruit from IIIT Allahabad?",
            "What is the campus placement and internship selection process?",
            "What is the minimum CGPA eligibility for placement drives?",
            "What are the average and highest CTC packages recorded?",
        ],
    },
    "NEP 2020": {
        "svg": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line></svg>',
        "tag": "Academics",
        "color": "linear-gradient(135deg, #f97316 0%, #ea580c 100%)",
        "bg_soft": "rgba(249, 115, 22, 0.08)",
        "desc": "Multidisciplinary courses and exit credentials",
        "questions": [
            "How is NEP 2020 implemented at IIIT Allahabad?",
            "How does NEP affect the flexible elective choices in B.Tech?",
            "What multidisciplinary minor programs are available under NEP?",
            "What are the multiple exit credentials available under NEP?",
        ],
    },
    "Health Center": {
        "svg": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"></path></svg>',
        "tag": "Campus Life",
        "color": "linear-gradient(135deg, #14b8a6 0%, #0d9488 100%)",
        "bg_soft": "rgba(20, 184, 166, 0.08)",
        "desc": "24/7 medical OPD, pharmacy and emergency services",
        "questions": [
            "Where is the campus health center located?",
            "What are the doctor consultation and OPD timings?",
            "What medical facilities, medicines, and ambulances are available?",
            "How do students get emergency health assistance at night?",
        ],
    },
    "Sports and Gymkhana": {
        "svg": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"></path><path d="M2 12h20"></path></svg>',
        "tag": "Campus Life",
        "color": "linear-gradient(135deg, #ec4899 0%, #db2777 100%)",
        "bg_soft": "rgba(236, 72, 153, 0.08)",
        "desc": "Athletics, clubs, cultural fests and indoor gym",
        "questions": [
            "What indoor and outdoor sports facilities exist on campus?",
            "What are the gymkhana and swimming pool operational hours?",
            "What annual cultural and sports fests are organized?",
            "How can I join student clubs and tech societies at IIITA?",
        ],
    },
    "Administration": {
        "svg": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>',
        "tag": "Administration",
        "color": "linear-gradient(135deg, #a855f7 0%, #9333ea 100%)",
        "bg_soft": "rgba(168, 85, 247, 0.08)",
        "desc": "Director, Deans, HODs and contact information",
        "questions": [
            "Who is the current Director of IIIT Allahabad?",
            "Who is the Dean of Academic Affairs and their office location?",
            "Who is the Dean of Student Affairs (DSA)?",
            "Who are the heads of Information Technology and Electronics departments?",
        ],
    },
}

# ── Dynamic CSS: Clean, No Chunky Curves, Circular Send, Animated Mascot Head ──
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Outfit:wght@400;500;600;700;800;900&display=swap');

/* Typography & Reset */
* {{
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
    box-sizing: border-box;
}}

h1, h2, h3, h4, .brand-title, .hero-title {{
    font-family: 'Outfit', sans-serif !important;
}}

/* Clean Soft Canvas */
html, body, [data-testid="stAppViewContainer"], .stApp {{
    background: #f6f8fd !important;
    background-image: 
        radial-gradient(circle at 10% 8%, rgba(124, 58, 237, 0.06) 0%, transparent 35%),
        radial-gradient(circle at 90% 12%, rgba(236, 72, 153, 0.06) 0%, transparent 35%),
        radial-gradient(circle at 50% 90%, rgba(56, 189, 248, 0.05) 0%, transparent 40%) !important;
    background-attachment: fixed !important;
    color: #1e293b !important;
    min-height: 100vh !important;
}}

#MainMenu, footer, header {{ visibility: hidden; height: 0; }}
.block-container {{
    max-width: 1040px !important;
    margin: 0 auto !important;
    padding: 0.8rem 1.2rem 3rem 1.2rem !important;
}}

section[data-testid="stSidebar"] {{ display: none; }}

/* ── App Top Navigation Bar ── */
.app-navbar {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 0.65rem 1.1rem;
    margin-bottom: 1rem;
    box-shadow: 0 2px 8px rgba(15, 23, 42, 0.03);
}}

.nav-brand {{
    display: flex;
    align-items: center;
    gap: 0.75rem;
    text-decoration: none;
}}

.nav-brand-img {{
    width: 34px;
    height: 34px;
    border-radius: 50%;
    object-fit: cover;
    border: 1.5px solid #e2e8f0;
}}

.nav-brand-text h1 {{
    font-size: 1.2rem;
    font-weight: 800;
    margin: 0;
    line-height: 1.1;
    color: #0f172a;
    letter-spacing: -0.02em;
}}

.nav-brand-text span {{
    font-size: 0.72rem;
    color: #64748b;
    font-weight: 500;
    letter-spacing: 0.02em;
}}

.nav-user-chip {{
    display: flex;
    align-items: center;
    gap: 0.6rem;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 0.3rem 0.75rem;
    font-size: 0.78rem;
    font-weight: 600;
    color: #334155;
}}

.online-dot {{
    width: 7px;
    height: 7px;
    background: #10b981;
    border-radius: 50%;
    display: inline-block;
}}

/* ── Clean Hero Banner Card ── */
.clean-hero-card {{
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 1.4rem 1.6rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1.2rem;
    position: relative;
    box-shadow: 0 4px 16px -2px rgba(15, 23, 42, 0.03);
}}

.hero-content {{
    max-width: 600px;
    z-index: 2;
}}

.hero-sub-label {{
    display: inline-block;
    color: #6d28d9;
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.4rem;
}}

.hero-title {{
    font-size: 1.75rem;
    font-weight: 800;
    line-height: 1.2;
    color: #0f172a;
    margin: 0 0 0.35rem 0;
    letter-spacing: -0.02em;
}}

.hero-title span.grad {{
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #ec4899 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}}

.hero-desc {{
    font-size: 0.88rem;
    color: #475569;
    line-height: 1.45;
    margin: 0 0 0.85rem 0;
}}

.hero-meta-row {{
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
}}

.meta-chip {{
    font-size: 0.72rem;
    font-weight: 600;
    color: #475569;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    padding: 0.2rem 0.6rem;
    border-radius: 6px;
}}

/* ── Animated Mascot Head Movement ── */
.mascot-head-container {{
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    position: relative;
    perspective: 800px;
}}

.hero-mascot-img, .auth-mascot-img {{
    border-radius: 50% !important;
    object-fit: cover !important;
    display: block !important;
    box-shadow: 
        0 14px 28px -4px rgba(236, 72, 153, 0.28),
        0 6px 14px -2px rgba(124, 58, 237, 0.18) !important;
    border: 3px solid #ffffff !important;
    transform-origin: 50% 75% !important;
    animation: mascotHeadAnimation 5.8s cubic-bezier(0.45, 0.05, 0.55, 0.95) infinite !important;
    will-change: transform;
}}

.hero-mascot-img {{
    width: 120px;
    height: 120px;
}}

.auth-mascot-img {{
    width: 125px;
    height: 125px;
    margin: 0 auto 1rem auto;
}}

/* Lifelike Head Movement Keyframes: Tilting left, right, nod, and subtle stretch */
@keyframes mascotHeadAnimation {{
    0% {{
        transform: translateY(0px) rotate(0deg) scale(1);
    }}
    16% {{
        transform: translateY(-4px) rotate(-6deg) scale(1.02);
    }}
    32% {{
        transform: translateY(-6px) rotate(-4.5deg) scale(1.025);
    }}
    48% {{
        transform: translateY(-3px) rotate(5deg) scale(1.02);
    }}
    64% {{
        transform: translateY(-5px) rotate(3.5deg) scale(1.025);
    }}
    78% {{
        transform: translateY(3px) rotate(0deg) scale(0.985);
    }}
    88% {{
        transform: translateY(-2px) rotate(-1deg) scale(1.01);
    }}
    100% {{
        transform: translateY(0px) rotate(0deg) scale(1);
    }}
}}

/* Synchronized gentle breathing shadow underneath mascot */
.mascot-shadow-circle {{
    width: 75px;
    height: 10px;
    background: radial-gradient(ellipse at center, rgba(124, 58, 237, 0.22) 0%, rgba(236, 72, 153, 0.08) 50%, transparent 70%);
    border-radius: 50%;
    margin-top: 6px;
    animation: mascotShadowAnimation 5.8s cubic-bezier(0.45, 0.05, 0.55, 0.95) infinite;
}}

@keyframes mascotShadowAnimation {{
    0%, 100% {{
        transform: scale(1);
        opacity: 0.65;
    }}
    20%, 64% {{
        transform: scale(0.86);
        opacity: 0.4;
    }}
    78% {{
        transform: scale(1.1);
        opacity: 0.8;
    }}
}}

/* ── Standard Button Styling (Clean, 8px radius, NO bulbous pills) ── */
.stButton > button {{
    border-radius: 8px !important;
    border: 1px solid #e2e8f0 !important;
    background: #ffffff !important;
    color: #1e293b !important;
    font-weight: 600 !important;
    font-size: 0.82rem !important;
    padding: 0.55rem 0.9rem !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02) !important;
    transition: all 0.18s ease !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 0.4rem !important;
}}

.stButton > button:hover {{
    background: #f8fafc !important;
    border-color: #cbd5e1 !important;
    color: #0f172a !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.04) !important;
}}

.stButton > button:active {{
    transform: translateY(0px) !important;
}}

/* Active state for program / batch selectors */
.active-sel-btn > div > .stButton > button {{
    background: #4f46e5 !important;
    color: #ffffff !important;
    border-color: #4f46e5 !important;
    box-shadow: 0 2px 8px rgba(79, 70, 229, 0.3) !important;
}}

/* ── TRUE CIRCULAR SEND BUTTON ── */
div[data-testid="stFormSubmitButton"] {{
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    margin: 0 !important;
    padding: 0 !important;
}}

div[data-testid="stFormSubmitButton"] > button {{
    width: 44px !important;
    height: 44px !important;
    min-width: 44px !important;
    max-width: 44px !important;
    border-radius: 50% !important;
    padding: 0 !important;
    margin: 0 auto !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 50%, #ec4899 100%) !important;
    color: #ffffff !important;
    border: none !important;
    font-size: 1.25rem !important;
    font-weight: 800 !important;
    box-shadow: 0 4px 14px rgba(79, 70, 229, 0.32) !important;
    cursor: pointer !important;
    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
}}

div[data-testid="stFormSubmitButton"] > button:hover {{
    transform: scale(1.1) !important;
    box-shadow: 0 6px 20px rgba(236, 72, 153, 0.45) !important;
    color: #ffffff !important;
}}

div[data-testid="stFormSubmitButton"] > button:active {{
    transform: scale(0.95) !important;
}}

/* Hide default chat avatars to completely eliminate any browser or Streamlit default emojis */
[data-testid="stChatMessageAvatar"] {{
    display: none !important;
}}

.stTextInput > div > div > input {{
    height: 44px !important;
    background: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 8px !important;
    color: #0f172a !important;
    font-size: 0.92rem !important;
    padding: 0 1rem !important;
    transition: all 0.2s ease !important;
}}

/* ── Section Titles ── */
.section-header-row {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: 1rem 0 0.7rem 0;
}}

.section-label {{
    font-size: 1.15rem;
    font-weight: 800;
    color: #0f172a;
    margin: 0;
}}

.section-sub {{
    font-size: 0.8rem;
    color: #64748b;
    font-weight: 500;
}}

/* ── Clean Category Cards (With Gradient SVG Icon Tiles) ── */
.clean-cat-card {{
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1rem 1.1rem;
    margin-bottom: 0.55rem;
    transition: all 0.2s ease;
}}

.clean-cat-card:hover {{
    border-color: #cbd5e1;
    box-shadow: 0 4px 12px rgba(15, 23, 42, 0.04);
}}

/* Colored Gradient Tile for SVG Icon */
.cat-svg-tile {{
    width: 40px;
    height: 40px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 3px 8px rgba(0, 0, 0, 0.06);
}}

/* ── Quick Question Chips (Clean, 8px radius) ── */
.clean-q-chip > div > .stButton > button {{
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    color: #334155 !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    padding: 0.55rem 0.9rem !important;
    text-align: left !important;
    justify-content: flex-start !important;
    box-shadow: none !important;
}}

.clean-q-chip > div > .stButton > button:hover {{
    background: #f8fafc !important;
    border-color: #6366f1 !important;
    color: #4f46e5 !important;
}}

/* ── Chat Messages ── */
.stChatMessage {{
    background: transparent !important;
    padding: 0.4rem 0 !important;
}}

div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-user"]) [data-testid="stChatMessageContent"] {{
    background: #1e1b4b !important;
    color: #ffffff !important;
    border-radius: 10px 10px 2px 10px !important;
    border: none !important;
    padding: 0.8rem 1.1rem !important;
    font-size: 0.9rem !important;
    font-weight: 500 !important;
}}

div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-user"]) [data-testid="stChatMessageContent"] p {{
    color: #ffffff !important;
}}

div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-assistant"]) [data-testid="stChatMessageContent"] {{
    background: #ffffff !important;
    color: #1e293b !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 10px 10px 10px 2px !important;
    padding: 0.9rem 1.2rem !important;
    box-shadow: 0 4px 14px rgba(15, 23, 42, 0.03) !important;
    font-size: 0.9rem !important;
    line-height: 1.6 !important;
}}

.source-tag-chip {{
    display: inline-block;
    background: #f1f5f9;
    border: 1px solid #cbd5e1;
    color: #475569;
    font-size: 0.72rem;
    font-weight: 600;
    padding: 0.2rem 0.5rem;
    border-radius: 4px;
    margin: 0.2rem 0.3rem 0.2rem 0;
}}

.stTextInput div[data-testid="InputInstructions"] {{ display: none !important; }}
small[data-testid="InputInstructions"] {{ display: none !important; }}
[data-testid="InputInstructions"] {{ display: none !important; }}

/* ── Auth Card ── */
.clean-auth-card {{
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 2rem 1.8rem;
    box-shadow: 0 8px 30px rgba(15, 23, 42, 0.05);
    max-width: 520px;
    margin: 0 auto;
}}

.stTabs [data-baseweb="tab-list"] {{
    gap: 0.35rem;
    background: #f1f5f9;
    padding: 0.25rem;
    border-radius: 8px;
    border: 1px solid #e2e8f0;
}}

.stTabs [data-baseweb="tab"] {{
    border-radius: 6px !important;
    padding: 0.45rem 0.9rem !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    color: #64748b !important;
    border: none !important;
}}

.stTabs [aria-selected="true"] {{
    background: #ffffff !important;
    color: #0f172a !important;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05) !important;
}}

.streamlit-expanderHeader {{
    background: #f8fafc !important;
    border-radius: 8px !important;
    border: 1px solid #e2e8f0 !important;
    font-weight: 600 !important;
    color: #1e293b !important;
}}

::-webkit-scrollbar {{
    width: 5px;
    height: 5px;
}}
::-webkit-scrollbar-thumb {{
    background: #cbd5e1;
    border-radius: 4px;
}}
</style>
""", unsafe_allow_html=True)


# ── Session State ─────────────────────────────────────────────────────────────
if "messages"         not in st.session_state: st.session_state["messages"]         = []
if "active_category"  not in st.session_state: st.session_state["active_category"]  = None
if "pending_query"    not in st.session_state: st.session_state["pending_query"]     = None
if "selected_program" not in st.session_state: st.session_state["selected_program"]  = "B.Tech"
if "selected_batch"   not in st.session_state: st.session_state["selected_batch"]    = "2026"
if "active_view"      not in st.session_state: st.session_state["active_view"]      = "Assistant"
if "auth_token"       not in st.session_state: st.session_state["auth_token"]       = None
if "username"         not in st.session_state: st.session_state["username"]         = None
if "role"             not in st.session_state: st.session_state["role"]             = None
if "is_mock_db"       not in st.session_state: st.session_state["is_mock_db"]       = is_mock_db

# Verify session token
if st.session_state["auth_token"]:
    payload = auth.verify_token(st.session_state["auth_token"])
    if not payload:
        st.session_state["auth_token"] = None
        st.session_state["username"] = None
        st.session_state["role"] = None
    else:
        st.session_state["username"] = payload.get("sub")
        st.session_state["role"] = payload.get("role")


# ── RAG Function ──────────────────────────────────────────────────────────────
def ask(query: str, username: str, user_role: str):
    from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
    from langchain_mongodb import MongoDBAtlasVectorSearch
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.runnables import RunnablePassthrough
    from datetime import datetime, timezone

    ROLE_HIERARCHY = {
        "public": ["public"],
        "student": ["public", "student"],
        "faculty": ["public", "student", "faculty"],
        "admin": ["public", "student", "faculty", "admin"]
    }
    allowed_levels = ROLE_HIERARCHY.get(user_role, ["public"])

    use_local_search = False
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
        print(f"[DB] Atlas connection failed for query: {conn_err}. Using local search fallback.")
        use_local_search = True

    source_docs = []
    if not use_local_search:
        try:
            emb = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001", google_api_key=GEMINI_API_KEY)
            vs  = MongoDBAtlasVectorSearch(collection=col_local, embedding=emb, index_name=ATLAS_INDEX)
            
            ret = vs.as_retriever(search_kwargs={
                "k": 4,
                "pre_filter": {
                    "access_level": {"$in": allowed_levels}
                }
            })
            source_docs = ret.invoke(query)
        except Exception as search_err:
            print(f"[DB] Atlas search execution failed: {search_err}. Falling back to local search.")
            use_local_search = True

    if use_local_search:
        import local_vector
        try:
            source_docs = local_vector.search_local(query, allowed_levels, GEMINI_API_KEY, k=4)
        except Exception as local_err:
            print(f"[LOCAL ERROR] Local search fallback failed: {local_err}")
            source_docs = []

    llm = ChatGoogleGenerativeAI(model="gemini-3.8-flash", google_api_key=GEMINI_API_KEY, temperature=0.2)

    today = date.today().strftime("%B %d, %Y")
    prompt = ChatPromptTemplate.from_template(f"""\
You are AskIIITA, the friendly, intelligent campus assistant for IIIT Allahabad students and faculty.
Today's date is {today}. Use this for time-aware answers (e.g., if an event has already passed, say so).
Use ONLY the context below to answer. If information is not in the context, be honest and concise.
Structure your answers clearly with bullet points where appropriate.

Context:
{{context}}

Question: {{question}}

Answer:""")

    def fmt(docs): return "\n\n".join(d.page_content for d in docs)

    sources = list({doc.metadata.get("source_file", doc.metadata.get("source", "Unknown")) for doc in source_docs})
    context_str = fmt(source_docs) if source_docs else "No relevant documents found for this query/role level."
    chain   = ({"context": lambda x: context_str, "question": RunnablePassthrough()} | prompt | llm | StrOutputParser())
    answer  = str(chain.invoke(query))
    
    # Audit logging
    try:
        if use_local_search or st.session_state.get("is_mock_db", False):
            db_audit = db
        else:
            db_audit = client_local[MONGO_DB_NAME]
        audit_col = db_audit["audit_logs"]
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
    except Exception as audit_err:
        print(f"[AUDIT ERROR] Failed to write audit log: {audit_err}")
        
    return answer, sources


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 1: ONBOARDING & AUTHENTICATION (Clean, Zero Indented Codebug)
# ══════════════════════════════════════════════════════════════════════════════
if not st.session_state["auth_token"]:
    
    mascot_auth_html = f'<div class="mascot-head-container" style="margin-bottom: 0.8rem;"><img src="{mascot_src}" class="auth-mascot-img"/><div class="mascot-shadow-circle"></div></div>' if mascot_src else ""

    landing_header = (
        f'<div style="text-align: center; padding: 1rem 0;">'
        f'{mascot_auth_html}'
        f'<div class="hero-sub-label">IIIT Allahabad AI Assistant</div>'
        f'<h1 class="hero-title" style="font-size: 2.1rem; margin-bottom: 0.25rem;">'
        f'Your <span class="grad">Smart Assistant</span> for Any Tasks'
        f'</h1>'
        f'<p class="hero-desc" style="max-width: 460px; margin: 0 auto 1.2rem auto;">'
        f'Access verified information regarding academic regulations, hostel allotment, fees, and campus services.'
        f'</p>'
        f'</div>'
    )
    st.markdown(landing_header, unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="clean-auth-card">', unsafe_allow_html=True)
        tab_login, tab_register, tab_quick = st.tabs(["Sign In", "Create Account", "Quick Access"])

        with tab_login:
            st.markdown('<p style="font-size: 0.8rem; color: #64748b; margin-bottom: 0.9rem;">Sign in with your institute account credentials:</p>', unsafe_allow_html=True)
            with st.form("login_form"):
                login_user = st.text_input("Username", placeholder="e.g. student_test")
                login_pass = st.text_input("Password", type="password", placeholder="Password")
                login_submit = st.form_submit_button("Sign In →", use_container_width=True)

                if login_submit:
                    if not login_user or not login_pass:
                        st.error("Please enter both username and password.")
                    elif not db:
                        st.error("Cannot authenticate. Database is currently unreachable.")
                    else:
                        try:
                            user_doc = auth.get_user(db, login_user)
                            if user_doc and auth.verify_password(login_pass, user_doc["password_salt"], user_doc["password_hash"]):
                                token = auth.generate_token(login_user, user_doc["role"])
                                st.session_state["auth_token"] = token
                                st.session_state["username"] = login_user
                                st.session_state["role"] = user_doc["role"]
                                st.success("Access Granted. Redirecting to assistant...")
                                st.rerun()
                            else:
                                st.error("Invalid username or password.")
                        except Exception as e:
                            st.error(f"Authentication Error: {e}")

        with tab_register:
            st.markdown('<p style="font-size: 0.8rem; color: #64748b; margin-bottom: 0.9rem;">Register a new campus profile:</p>', unsafe_allow_html=True)
            with st.form("register_form"):
                reg_user = st.text_input("Username", placeholder="e.g. sagar_student")
                reg_pass = st.text_input("Password", type="password", placeholder="At least 6 characters")
                reg_role = st.selectbox("Campus Role", ["student", "faculty"])
                reg_submit = st.form_submit_button("Create Account →", use_container_width=True)

                if reg_submit:
                    if not reg_user or not reg_pass:
                        st.error("Please fill in all fields.")
                    elif len(reg_pass) < 6:
                        st.error("Password must be at least 6 characters.")
                    elif not db:
                        st.error("Cannot create account. Database is unreachable.")
                    else:
                        try:
                            success = auth.create_user(db, reg_user, reg_pass, reg_role)
                            if success:
                                st.success("Account created successfully. Please sign in.")
                            else:
                                st.error("Username already exists.")
                        except Exception as e:
                            st.error(f"Registration Error: {e}")

        with tab_quick:
            st.markdown('<p style="font-size: 0.8rem; color: #64748b; margin-bottom: 0.9rem;">Instant sign in with pre-seeded accounts:</p>', unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("Student\n(student_test)", use_container_width=True):
                    token = auth.generate_token("student_test", "student")
                    st.session_state["auth_token"] = token
                    st.session_state["username"] = "student_test"
                    st.session_state["role"] = "student"
                    st.rerun()
            with c2:
                if st.button("Faculty\n(faculty_test)", use_container_width=True):
                    token = auth.generate_token("faculty_test", "faculty")
                    st.session_state["auth_token"] = token
                    st.session_state["username"] = "faculty_test"
                    st.session_state["role"] = "faculty"
                    st.rerun()
            with c3:
                if st.button("Admin\n(admin_test)", use_container_width=True):
                    token = auth.generate_token("admin_test", "admin")
                    st.session_state["auth_token"] = token
                    st.session_state["username"] = "admin_test"
                    st.session_state["role"] = "admin"
                    st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 2: AUTHENTICATED MAIN INTERFACE (Clean, Zero Emojis, No Guide Tab)
# ══════════════════════════════════════════════════════════════════════════════

# ── App Top Navigation Bar ──
mascot_nav_html = f'<img src="{mascot_src}" class="nav-brand-img"/>' if mascot_src else ''

st.markdown(f"""
<div class="app-navbar">
    <div class="nav-brand">
        {mascot_nav_html}
        <div class="nav-brand-text">
            <h1>AskIIITA</h1>
            <span>Campus AI Assistant &bull; IIIT Allahabad</span>
        </div>
    </div>
    <div class="nav-user-chip">
        <span class="online-dot"></span>
        <span>{st.session_state["username"]}</span>
        <span style="color: #6366f1; background: #ede9fe; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.72rem; text-transform: uppercase; font-weight: 700;">{st.session_state["role"]}</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Top Navigation Tabs (Assistant, FAQs, Audit Logs [Admin], Sign Out) ──
if st.session_state["role"] == "admin":
    nav_cols = st.columns([1.5, 1.5, 1.5, 1])
    with nav_cols[0]:
        if st.button("Assistant", key="nav_chat", use_container_width=True):
            st.session_state["active_view"] = "Assistant"
            st.session_state["active_category"] = None
            st.rerun()
    with nav_cols[1]:
        if st.button("FAQs", key="nav_faqs", use_container_width=True):
            st.session_state["active_view"] = "FAQs"
            st.rerun()
    with nav_cols[2]:
        if st.button("Audit Logs", key="nav_audit", use_container_width=True):
            st.session_state["active_view"] = "Audit Logs"
            st.rerun()
    with nav_cols[3]:
        if st.button("Sign Out", key="nav_logout", use_container_width=True):
            st.session_state["auth_token"] = None
            st.session_state["username"] = None
            st.session_state["role"] = None
            st.session_state["messages"] = []
            st.session_state["active_category"] = None
            st.rerun()
else:
    nav_cols = st.columns([2, 2, 1.2])
    with nav_cols[0]:
        if st.button("Assistant", key="nav_chat", use_container_width=True):
            st.session_state["active_view"] = "Assistant"
            st.session_state["active_category"] = None
            st.rerun()
    with nav_cols[1]:
        if st.button("FAQs", key="nav_faqs", use_container_width=True):
            st.session_state["active_view"] = "FAQs"
            st.rerun()
    with nav_cols[2]:
        if st.button("Sign Out", key="nav_logout", use_container_width=True):
            st.session_state["auth_token"] = None
            st.session_state["username"] = None
            st.session_state["role"] = None
            st.session_state["messages"] = []
            st.session_state["active_category"] = None
            st.rerun()


# ── View: Admin Audit Logs ──
if st.session_state.get("active_view") == "Audit Logs" and st.session_state["role"] == "admin":
    st.markdown("""
    <div class="section-header-row">
        <h2 class="section-label">System Audit and Access Records</h2>
        <span class="section-sub">Security log of student queries and retrieved context</span>
    </div>
    """, unsafe_allow_html=True)

    with st.container():
        if not db:
            st.error("Database connection unavailable to retrieve logs.")
        else:
            try:
                audit_col = db["audit_logs"]
                logs = list(audit_col.find({}).sort("timestamp", -1).limit(40))
                if not logs:
                    st.info("No queries recorded in audit collection yet.")
                else:
                    for log in logs:
                        ts = log.get('timestamp')
                        ts_display = ts.strftime('%Y-%m-%d %H:%M:%S') if hasattr(ts, 'strftime') else str(ts or "Recent")
                        u = log.get('user_id', 'Unknown')
                        r = log.get('role', 'public')
                        q = log.get('query_text', '')
                        chunks = log.get('retrieved_chunks', [])

                        with st.expander(f"{ts_display} | User: {u} ({r}) | \"{q[:60]}...\""):
                            st.markdown(f"**Query:** `{q}`")
                            st.markdown(f"**Retrieved Chunks ({len(chunks)}):**")
                            if not chunks:
                                st.markdown("*No chunks matched clearance.*")
                            for idx, ch in enumerate(chunks):
                                st.markdown(f"""
                                <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 0.5rem 0.75rem; margin-bottom: 0.35rem;">
                                    <div style="font-size: 0.76rem; font-weight: 700; color: #475569;">
                                        Source: {ch.get('source_file')} | Clearance: {ch.get('access_level')}
                                    </div>
                                    <div style="font-size: 0.8rem; color: #334155; margin-top: 0.25rem;">
                                        {ch.get('content_snippet')}...
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Error fetching audit records: {e}")
    st.stop()


# ── Hero Banner Card with Head-Moving Animated Mascot ──
mascot_hero_html = f"""<div class="mascot-head-container"><img src="{mascot_src}" class="hero-mascot-img"/><div class="mascot-shadow-circle"></div></div>""" if mascot_src else ""

fallback_badge = "<span class='meta-chip' style='color:#b45309; background:#fef3c7;'>Local Fallback</span>" if st.session_state.get("is_mock_db") else "<span class='meta-chip' style='color:#059669; background:#ecfdf5;'>Atlas Connected</span>"

hero_card_html = (
    f'<div class="clean-hero-card">'
    f'<div class="hero-content">'
    f'<div class="hero-sub-label">Campus Knowledge Assistant</div>'
    f'<h2 class="hero-title">Hi, <b>{st.session_state["username"]}</b>. How may I <span class="grad">help you</span> today?</h2>'
    f'<p class="hero-desc">Ask verified questions regarding B.Tech and M.Tech curriculum, semester fee schedules, hostel regulations, or placement statistics.</p>'
    f'<div class="hero-meta-row">'
    f'<span class="meta-chip">Gemini 3.8 Flash</span>'
    f'<span class="meta-chip">3072-dim Vector Search</span>'
    f'<span class="meta-chip">20 Institute Docs</span>'
    f'{fallback_badge}'
    f'</div>'
    f'</div>'
    f'{mascot_hero_html}'
    f'</div>'
)
st.markdown(hero_card_html, unsafe_allow_html=True)


# ── View: FAQs (Formerly Knowledge Hub, with Clean Vector SVG Icons) ───────────
if st.session_state.get("active_view") == "FAQs":
    st.markdown("""
    <div class="section-header-row">
        <div>
            <h2 class="section-label">FAQs</h2>
            <span class="section-sub">Frequently asked campus questions and academic guidance</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    active_cat = st.session_state.get("active_category")

    if active_cat is None:
        cat_items = list(CATEGORIES.items())
        cols = st.columns(2)
        for idx, (cat_name, cat_data) in enumerate(cat_items):
            c_idx = idx % 2
            with cols[c_idx]:
                cat_card_html = (
                    f'<div class="clean-cat-card">'
                    f'<div style="display: flex; align-items: center; justify-content: flex-start; margin-bottom: 0.65rem;">'
                    f'<div class="cat-svg-tile" style="background: {cat_data["color"]};">'
                    f'{cat_data["svg"]}'
                    f'</div>'
                    f'</div>'
                    f'<div style="font-size: 0.98rem; font-weight: 700; color: #0f172a; margin-bottom: 0.2rem;">{cat_name}</div>'
                    f'<div style="font-size: 0.8rem; color: #64748b; line-height: 1.4; margin-bottom: 0.7rem;">{cat_data["desc"]}</div>'
                    f'</div>'
                )
                st.markdown(cat_card_html, unsafe_allow_html=True)
                if st.button(f"View {cat_name} →", key=f"btn_hub_cat_{cat_name}", use_container_width=True):
                    st.session_state["active_category"] = cat_name
                    st.rerun()
    else:
        cat_info = CATEGORIES[active_cat]
        c_back, c_title = st.columns([1, 4])
        with c_back:
            if st.button("← Back to FAQs", key="btn_back_hub"):
                st.session_state["active_category"] = None
                st.rerun()
        with c_title:
            cat_header_html = (
                f'<div style="display:flex; align-items:center; gap:0.6rem; margin-top:0.25rem;">'
                f'<div class="cat-svg-tile" style="background: {cat_info["color"]}; width: 30px; height: 30px;">{cat_info["svg"]}</div>'
                f'<span style="font-size:1.15rem; font-weight:800; color:#0f172a;">{active_cat}</span>'
                f'<span style="font-size:0.8rem; color:#64748b;">({cat_info["desc"]})</span>'
                f'</div>'
            )
            st.markdown(cat_header_html, unsafe_allow_html=True)

        if active_cat == "Fees and Dues":
            st.markdown('<p style="font-size: 0.8rem; font-weight: 700; color: #475569; margin: 0.75rem 0 0.3rem 0;">1. Select Degree Program</p>', unsafe_allow_html=True)
            p_cols = st.columns(3)
            for p in ["B.Tech", "M.Tech", "PhD"]:
                with p_cols[["B.Tech", "M.Tech", "PhD"].index(p)]:
                    is_active = (st.session_state["selected_program"] == p)
                    st.markdown(f'<div class="{"active-sel-btn" if is_active else ""}">', unsafe_allow_html=True)
                    if st.button(p, key=f"prog_pick_{p}", use_container_width=True):
                        st.session_state["selected_program"] = p
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<p style="font-size: 0.8rem; font-weight: 700; color: #475569; margin: 0.75rem 0 0.3rem 0;">2. Select Admission Batch Year</p>', unsafe_allow_html=True)
            b_cols = st.columns(4)
            for b in ["2023", "2024", "2025", "2026"]:
                with b_cols[["2023", "2024", "2025", "2026"].index(b)]:
                    is_active = (st.session_state["selected_batch"] == b)
                    st.markdown(f'<div class="{"active-sel-btn" if is_active else ""}">', unsafe_allow_html=True)
                    if st.button(b, key=f"batch_pick_{b}", use_container_width=True):
                        st.session_state["selected_batch"] = b
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

            curr_p = st.session_state["selected_program"]
            curr_b = st.session_state["selected_batch"]
            dynamic_questions = [
                f"What is the total fee structure for {curr_p} {curr_b} batch?",
                f"What are the semester tuition and hostel charges for {curr_p} {curr_b} batch?",
                f"What are the one-time admission dues for {curr_p} {curr_b} batch?",
                f"What is the refund and late fee penalty policy for {curr_p}?",
            ]
            st.markdown('<p style="font-size: 0.8rem; font-weight: 700; color: #475569; margin: 0.9rem 0 0.4rem 0;">3. Quick Fee Queries (Click to submit):</p>', unsafe_allow_html=True)
            for q_idx, q_text in enumerate(dynamic_questions):
                st.markdown('<div class="clean-q-chip">', unsafe_allow_html=True)
                if st.button(q_text, key=f"qq_fee_dyn_{q_idx}", use_container_width=True):
                    st.session_state["pending_query"] = q_text
                    st.session_state["active_view"] = "Assistant"
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<p style="font-size: 0.8rem; font-weight: 700; color: #475569; margin: 0.8rem 0 0.4rem 0;">Suggested Queries (Click to submit):</p>', unsafe_allow_html=True)
            for q_idx, q_text in enumerate(cat_info["questions"]):
                st.markdown('<div class="clean-q-chip">', unsafe_allow_html=True)
                if st.button(q_text, key=f"qq_cat_{active_cat}_{q_idx}", use_container_width=True):
                    st.session_state["pending_query"] = q_text
                    st.session_state["active_view"] = "Assistant"
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)


# ── View: Conversational Assistant (Chat) ──
if st.session_state.get("active_view", "Assistant") == "Assistant":
    
    st.markdown("""
    <div class="section-header-row">
        <div>
            <h2 class="section-label">Conversational AI Assistant</h2>
            <span class="section-sub">Verified answers sourced from official IIITA regulations</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    chat_box = st.container()

    with chat_box:
        if len(st.session_state["messages"]) == 0:
            st.markdown("""
            <div style="background: #ffffff; border: 1px dashed #cbd5e1; border-radius: 10px; padding: 1.5rem; text-align: center; margin-bottom: 0.9rem;">
                <div style="font-size: 1.05rem; font-weight: 700; color: #0f172a; margin-bottom: 0.25rem;">
                    Welcome to AskIIITA
                </div>
                <div style="font-size: 0.84rem; color: #64748b; max-width: 480px; margin: 0 auto 1rem auto;">
                    Submit a query below or select a recommended question to begin:
                </div>
            </div>
            """, unsafe_allow_html=True)

            starters = [
                "What are the hostel room allotment rules?",
                "When do the mid-semester exams start?",
                "What is the grading policy and passing criteria?",
                "What companies visit IIITA for placements?",
            ]
            s_cols = st.columns(2)
            for s_idx, s_text in enumerate(starters):
                with s_cols[s_idx % 2]:
                    st.markdown('<div class="clean-q-chip">', unsafe_allow_html=True)
                    if st.button(s_text, key=f"starter_btn_{s_idx}", use_container_width=True):
                        st.session_state["pending_query"] = s_text
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

        else:
            c_clear, _ = st.columns([1.5, 4.5])
            with c_clear:
                if st.button("Clear History", key="btn_clear_chat", use_container_width=True):
                    st.session_state["messages"] = []
                    st.rerun()

            for msg in st.session_state["messages"]:
                is_user = (msg["role"] == "user")
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
                    if msg.get("sources"):
                        src_chips = "".join([f'<span class="source-tag-chip">Source: {s}</span>' for s in msg["sources"]])
                        st.markdown(f"""
                        <div style="margin-top: 0.5rem; border-top: 1px solid #f1f5f9; padding-top: 0.35rem;">
                            {src_chips}
                        </div>
                        """, unsafe_allow_html=True)

    # ── Input Area with Circular Send Button ──
    pending = st.session_state.get("pending_query", None)

    st.markdown('<div style="margin-top: 1rem;"></div>', unsafe_allow_html=True)
    with st.form(key="chat_input_form", clear_on_submit=True):
        f_col1, f_col2 = st.columns([11, 1])
        with f_col1:
            user_input = st.text_input(
                "Ask a campus query",
                placeholder="Ask about courses, hostels, grades, fees, or regulations...",
                key="chat_input_field",
                label_visibility="collapsed"
            )
        with f_col2:
            submitted = st.form_submit_button("↑")

    # Handle incoming query
    active_query = pending or (user_input if submitted else None)

    if active_query and active_query.strip():
        st.session_state["messages"].append({"role": "user", "content": active_query.strip()})
        st.session_state["pending_query"] = None

        with st.spinner("Consulting IIITA Knowledge Base..."):
            try:
                answer, sources = ask(active_query.strip(), st.session_state["username"], st.session_state["role"])
            except Exception as e:
                err_msg = str(e)
                if "RESOURCE_EXHAUSTED" in err_msg or "429" in err_msg:
                    answer = (
                        "Gemini API daily quota exceeded. "
                        "Please wait a few moments or configure an active API key in .env."
                    )
                else:
                    answer = f"Service notice: Unable to complete query: {err_msg}"
                sources = []

        st.session_state["messages"].append({
            "role": "assistant",
            "content": answer,
            "sources": sources
        })
        st.rerun()
