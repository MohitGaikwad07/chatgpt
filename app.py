import base64
import os
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

# =========================================================
# PAGE CONFIGURATION
# =========================================================
st.set_page_config(
    page_title="Swaraj's ChatGPT",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_PATH = Path("chats.db")
MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
FALLBACK_MODEL = "openai/gpt-oss-120b"

SYSTEM_PROMPT = """
You are Swaraj's ChatGPT, an advanced, highly intelligent, thoughtful, and articulate AI companion.

CORE BEHAVIOR:
- Address the user naturally, with precision, warmth, and clarity.
- When answering technical or coding questions, provide clean, idiomatic code with explanations and edge cases.
- Use clean Markdown with headers, bullet points, and code fences to structure longer answers.
- Be direct, avoid unnecessary pleasantries, and deliver top-tier insightful responses.
- Respect Swaraj as your primary user and collaborator.
"""

# =========================================================
# PROCEDURAL COSMIC STARFIELD (PURE CODE SVG - NO IMAGE ASSET)
# =========================================================
def get_starfield_base64():
    stars = []
    # 180 stars distributed deterministically across 1920x1080 canvas
    for i in range(180):
        x = (i * 127 + 43) % 1920
        y = (i * 181 + 71) % 1080
        r = round(0.7 + ((i * 17) % 11) / 7.0, 1)
        op = round(0.35 + ((i * 23) % 11) / 16.0, 2)
        color = '#ffffff' if i % 3 == 0 else ('#e9d5ff' if i % 3 == 1 else '#c084fc')
        stars.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}" opacity="{op}"/>')

    # Cosmic glowing sparkle cross stars
    sparkles = [
        (260, 150, 15), (540, 290, 12), (880, 120, 19), (1190, 220, 16), (1550, 160, 14), 
        (380, 580, 13), (760, 440, 16), (1080, 620, 14), (1440, 520, 18), (620, 830, 15), 
        (1260, 840, 14), (170, 780, 12), (1700, 750, 15), (940, 890, 13)
    ]

    for sx, sy, sz in sparkles:
        stars.append(f'<circle cx="{sx}" cy="{sy}" r="{sz*2}" fill="#a855f7" opacity="0.18"/>')
        stars.append(f'<circle cx="{sx}" cy="{sy}" r="{sz}" fill="#c084fc" opacity="0.4"/>')
        stars.append(f'<circle cx="{sx}" cy="{sy}" r="3" fill="#ffffff" opacity="0.95"/>')
        flare = f'M {sx} {sy-sz} Q {sx} {sy} {sx+sz} {sy} Q {sx} {sy} {sx} {sy+sz} Q {sx} {sy} {sx-sz} {sy} Q {sx} {sy} {sx} {sy-sz} Z'
        stars.append(f'<path d="{flare}" fill="#ffffff" opacity="0.95"/>')

    svg_content = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080" width="100%" height="100%"><rect width="1920" height="1080" fill="none"/>{"".join(stars)}</svg>'
    return base64.b64encode(svg_content.encode("utf-8")).decode("utf-8")

STARFIELD_B64 = get_starfield_base64()

# SVG Avatars for Purple Dark Theme
ASSISTANT_AVATAR = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 36 36' width='36' height='36'%3E"
    "%3Cdefs%3E%3ClinearGradient id='cgGrad' x1='0%25' y1='0%25' x2='100%25' y2='100%25'%3E"
    "%3Cstop offset='0%25' stop-color='%237c3aed'/%3E%3Cstop offset='100%25' stop-color='%23c084fc'/%3E"
    "%3C/linearGradient%3E%3C/defs%3E"
    "%3Crect width='36' height='36' rx='18' fill='url(%23cgGrad)'/%3E"
    "%3Cpath fill='%23ffffff' d='M18 7.5c-5.8 0-10.5 4.7-10.5 10.5 0 2.2.7 4.2 1.9 5.8l-1.2 4.4 4.5-1.2c1.6 1 3.4 1.5 5.3 1.5 5.8 0 10.5-4.7 10.5-10.5S23.8 7.5 18 7.5zm0 17.5c-1.6 0-3.1-.4-4.4-1.2l-.3-.2-3.1.8.8-3-.2-.3c-.9-1.3-1.4-2.8-1.4-4.4 0-4.7 3.8-8.5 8.5-8.5s8.5 3.8 8.5 8.5-3.8 8.3-8.4 8.3z'/%3E"
    "%3Ccircle cx='18' cy='18' r='3.2' fill='%23ffffff'/%3E"
    "%3C/svg%3E"
)

USER_AVATAR = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 36 36' width='36' height='36'%3E"
    "%3Cdefs%3E%3ClinearGradient id='uGrad' x1='0%25' y1='0%25' x2='100%25' y2='100%25'%3E"
    "%3Cstop offset='0%25' stop-color='%23581c87'/%3E%3Cstop offset='100%25' stop-color='%239333ea'/%3E"
    "%3C/linearGradient%3E%3C/defs%3E"
    "%3Crect width='36' height='36' rx='18' fill='url(%23uGrad)'/%3E"
    "%3Ctext x='50%25' y='55%25' dominant-baseline='middle' text-anchor='middle' fill='%23ffffff' font-family='sans-serif' font-weight='700' font-size='16'%3ES%3C/text%3E"
    "%3C/svg%3E"
)


# =========================================================
# DATABASE & STORAGE
# =========================================================
def connect_db():
    return sqlite3.connect(str(DB_PATH), timeout=15)


def init_db():
    with connect_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(chat_id) REFERENCES chats(id)
            )
        """)


def create_chat():
    chat_id = str(uuid.uuid4())
    now = datetime.now().isoformat(timespec="seconds")
    with connect_db() as conn:
        conn.execute(
            "INSERT INTO chats (id, title, created_at) VALUES (?, ?, ?)",
            (chat_id, "New conversation", now),
        )
    return chat_id


def get_chats():
    with connect_db() as conn:
        return conn.execute(
            "SELECT id, title FROM chats ORDER BY created_at DESC"
        ).fetchall()


def get_messages(chat_id):
    with connect_db() as conn:
        rows = conn.execute(
            """SELECT role, content FROM messages
               WHERE chat_id = ? ORDER BY id ASC""",
            (chat_id,),
        ).fetchall()
    return [{"role": role, "content": content} for role, content in rows]


def save_message(chat_id, role, content):
    now = datetime.now().isoformat(timespec="seconds")
    with connect_db() as conn:
        conn.execute(
            """INSERT INTO messages (chat_id, role, content, created_at)
               VALUES (?, ?, ?, ?)""",
            (chat_id, role, content, now),
        )
        if role == "user":
            count = conn.execute(
                """SELECT COUNT(*) FROM messages
                   WHERE chat_id = ? AND role = 'user'""",
                (chat_id,),
            ).fetchone()[0]
            if count == 1:
                # Set a concise title from the first prompt
                clean_title = " ".join(content.strip().split())[:36]
                conn.execute(
                    "UPDATE chats SET title = ? WHERE id = ?",
                    (clean_title or "New conversation", chat_id),
                )


def delete_chat(chat_id):
    with connect_db() as conn:
        conn.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
        conn.execute("DELETE FROM chats WHERE id = ?", (chat_id,))


init_db()


# =========================================================
# GROQ CLIENT
# =========================================================
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    try:
        api_key = st.secrets.get("GROQ_API_KEY")
    except Exception:
        api_key = None

if not api_key:
    st.error(
        "GROQ_API_KEY is missing. Please add GROQ_API_KEY in your .env or Streamlit secrets."
    )
    st.stop()

client = Groq(api_key=api_key, timeout=40.0)


# =========================================================
# SESSION STATE MANAGEMENT
# =========================================================
if "chat_id" not in st.session_state:
    all_chats = get_chats()
    st.session_state.chat_id = all_chats[0][0] if all_chats else create_chat()


# =========================================================
# PURPLE DARK THEME & RESPONSIVE STYLING CSS
# =========================================================
st.markdown(f"""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap">

<style>
/* --- Purple Theme Color Tokens --- */
:root {{
  --bg-app: #090312;
  --bg-sidebar: rgba(13, 6, 24, 0.94);
  --bg-input: rgba(24, 13, 44, 0.92);
  --border-subtle: rgba(168, 85, 247, 0.16);
  --border-medium: rgba(168, 85, 247, 0.28);
  --border-hover: rgba(192, 132, 252, 0.55);
  --text-main: #f5f3ff;
  --text-muted: #c4b5fd;
  --text-dim: #8b7ca8;
  --purple-primary: #9333ea;
  --purple-hover: #a855f7;
  --purple-light: #c084fc;
  --purple-glow: rgba(168, 85, 247, 0.45);
}}

/* Typography: Selective application to avoid breaking font glyphs */
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"],
p, h1, h2, h3, h4, h5, h6, input, textarea, label {{
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
  box-sizing: border-box;
}}

/* =========================================================
   PERMANENT SIDEBAR ARROW FIX:
   1. Suppress all raw text ligature text completely (font-size: 0)
   2. Render crisp vector SVG double-chevron arrow via pseudo-element
   ========================================================= */
[data-testid="stExpandSidebarButton"] *,
[data-testid="stSidebarCollapseButton"] * {{
  font-size: 0 !important;
  line-height: 0 !important;
  color: transparent !important;
  visibility: hidden !important;
}}

[data-testid="stExpandSidebarButton"] {{
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  background: rgba(28, 14, 50, 0.88) !important;
  border: 1px solid rgba(168, 85, 247, 0.4) !important;
  border-radius: 10px !important;
  width: 38px !important;
  height: 38px !important;
  min-width: 38px !important;
  min-height: 38px !important;
  padding: 0 !important;
  margin: 0.5rem 0.85rem !important;
  cursor: pointer !important;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.5), 0 0 12px rgba(168, 85, 247, 0.3) !important;
  backdrop-filter: blur(12px) !important;
  position: relative !important;
  overflow: visible !important;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
}}

[data-testid="stExpandSidebarButton"]:hover {{
  background: rgba(88, 28, 135, 0.95) !important;
  border-color: #c084fc !important;
  box-shadow: 0 0 22px rgba(168, 85, 247, 0.65) !important;
  transform: scale(1.06) !important;
}}

/* Vector SVG Double Chevron Right (») */
[data-testid="stExpandSidebarButton"]::before {{
  content: "" !important;
  display: block !important;
  width: 20px !important;
  height: 20px !important;
  background-color: #c084fc !important;
  -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2.4' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='13 17 18 12 13 7'%3E%3C/polyline%3E%3Cpolyline points='6 17 11 12 6 7'%3E%3C/polyline%3E%3C/svg%3E") no-repeat center / contain !important;
  mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2.4' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='13 17 18 12 13 7'%3E%3C/polyline%3E%3Cpolyline points='6 17 11 12 6 7'%3E%3C/polyline%3E%3C/svg%3E") no-repeat center / contain !important;
  filter: drop-shadow(0 0 8px rgba(192, 132, 252, 0.75)) !important;
  transition: all 0.2s ease !important;
}}

[data-testid="stExpandSidebarButton"]:hover::before {{
  background-color: #ffffff !important;
  filter: drop-shadow(0 0 12px #c084fc) !important;
}}

/* Vector SVG Double Chevron Left («) inside sidebar */
[data-testid="stSidebarCollapseButton"] {{
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  background: rgba(28, 14, 50, 0.8) !important;
  border: 1px solid rgba(168, 85, 247, 0.3) !important;
  border-radius: 9px !important;
  width: 34px !important;
  height: 34px !important;
  min-width: 34px !important;
  min-height: 34px !important;
  padding: 0 !important;
  cursor: pointer !important;
  position: relative !important;
  overflow: visible !important;
  transition: all 0.2s ease !important;
}}

[data-testid="stSidebarCollapseButton"]:hover {{
  background: rgba(88, 28, 135, 0.9) !important;
  border-color: #c084fc !important;
  box-shadow: 0 0 14px rgba(168, 85, 247, 0.5) !important;
}}

[data-testid="stSidebarCollapseButton"]::before {{
  content: "" !important;
  display: block !important;
  width: 18px !important;
  height: 18px !important;
  background-color: #c084fc !important;
  -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2.4' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='11 17 6 12 11 7'%3E%3C/polyline%3E%3Cpolyline points='18 17 13 12 18 7'%3E%3C/polyline%3E%3C/svg%3E") no-repeat center / contain !important;
  mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2.4' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='11 17 6 12 11 7'%3E%3C/polyline%3E%3Cpolyline points='18 17 13 12 18 7'%3E%3C/polyline%3E%3C/svg%3E") no-repeat center / contain !important;
  filter: drop-shadow(0 0 8px rgba(192, 132, 252, 0.75)) !important;
  transition: all 0.2s ease !important;
}}

[data-testid="stSidebarCollapseButton"]:hover::before {{
  background-color: #ffffff !important;
  filter: drop-shadow(0 0 12px #c084fc) !important;
}}

/* Hide default streamlit decorations */
#MainMenu, footer, header[data-testid="stHeader"] .stDeployButton, [data-testid="stDecoration"] {{
  display: none !important;
}}

header[data-testid="stHeader"] {{
  background: transparent !important;
  border-bottom: none !important;
  height: 3.5rem !important;
  z-index: 99999 !important;
  display: flex !important;
  align-items: center !important;
}}

[data-testid="stAppToolbar"] {{
  background: transparent !important;
}}

/* =========================================================
   COSMIC DARK PURPLE SPACE THEME (PURE CSS & SVG STARFIELD)
   ========================================================= */
.stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {{
  background-color: var(--bg-app) !important;
  background-image: 
    radial-gradient(ellipse 70% 50% at 50% 25%, rgba(126, 34, 206, 0.38) 0%, rgba(76, 29, 149, 0.22) 45%, transparent 75%),
    radial-gradient(ellipse 55% 45% at 75% 45%, rgba(147, 51, 234, 0.28) 0%, transparent 65%),
    radial-gradient(ellipse 60% 40% at 20% 65%, rgba(107, 33, 168, 0.25) 0%, transparent 60%),
    radial-gradient(circle at 50% 85%, rgba(88, 28, 135, 0.2) 0%, transparent 60%),
    url("data:image/svg+xml;base64,{STARFIELD_B64}") !important;
  background-size: cover !important;
  background-position: center center !important;
  background-attachment: fixed !important;
  background-repeat: no-repeat !important;
  color: var(--text-main) !important;
}}

.block-container {{
  max-width: 780px !important;
  padding: 1.5rem 1.2rem 8.5rem !important;
}}

/* --- SIDEBAR STYLING --- */
[data-testid="stSidebar"] {{
  background-color: var(--bg-sidebar) !important;
  border-right: 1px solid var(--border-subtle) !important;
  backdrop-filter: blur(18px) !important;
}}

[data-testid="stSidebar"] > div:first-child {{
  background-color: transparent !important;
  padding: 1rem 0.75rem !important;
}}

/* Brand header in sidebar */
.sidebar-brand-wrapper {{
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0.4rem 0.5rem 1rem;
  border-bottom: 1px solid var(--border-subtle);
  margin-bottom: 1rem;
}}

.sidebar-brand-logo {{
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: linear-gradient(135deg, #7c3aed, #c084fc);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 14px var(--purple-glow);
  color: white;
  font-size: 14px;
}}

.sidebar-brand-name {{
  font-weight: 700;
  font-size: 1.05rem;
  letter-spacing: -0.02em;
  color: #ffffff;
}}

.sidebar-section-title {{
  color: var(--text-dim);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin: 1.1rem 0.5rem 0.5rem;
}}

/* New chat button */
[data-testid="stSidebar"] .stButton.new-chat-button > button,
[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:nth-child(2) .stButton > button {{
  background: rgba(35, 18, 62, 0.7) !important;
  border: 1px solid var(--border-medium) !important;
  color: var(--text-main) !important;
  border-radius: 10px !important;
  font-weight: 500 !important;
  font-size: 0.88rem !important;
  padding: 0.65rem 0.85rem !important;
  transition: all 0.2s ease !important;
  text-align: left !important;
  justify-content: flex-start !important;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3) !important;
}}

[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:nth-child(2) .stButton > button:hover {{
  background: rgba(59, 28, 105, 0.9) !important;
  border-color: var(--purple-light) !important;
  color: #ffffff !important;
  transform: translateY(-1px);
  box-shadow: 0 0 14px rgba(168, 85, 247, 0.45) !important;
}}

/* Conversation item buttons */
[data-testid="stSidebar"] .stButton > button {{
  border-radius: 8px !important;
  font-size: 0.85rem !important;
  padding: 0.45rem 0.65rem !important;
  text-align: left !important;
  justify-content: flex-start !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  transition: all 0.15s ease !important;
  color: var(--text-muted) !important;
  background: transparent !important;
  border: 1px solid transparent !important;
}}

/* Active chat button */
[data-testid="stSidebar"] .stButton > button[kind="primary"] {{
  background-color: rgba(76, 29, 149, 0.5) !important;
  border: 1px solid rgba(168, 85, 247, 0.45) !important;
  color: #ffffff !important;
  font-weight: 600 !important;
  box-shadow: 0 0 12px rgba(147, 51, 234, 0.25) !important;
}}

[data-testid="stSidebar"] .stButton > button:hover {{
  background-color: rgba(46, 21, 82, 0.6) !important;
  border-color: var(--border-subtle) !important;
  color: #ffffff !important;
}}

/* Delete button styling */
[data-testid="stSidebar"] .del-btn .stButton > button {{
  text-align: center !important;
  justify-content: center !important;
  padding: 0.45rem 0.3rem !important;
  color: var(--text-dim) !important;
}}

[data-testid="stSidebar"] .del-btn .stButton > button:hover {{
  background: rgba(239, 68, 68, 0.2) !important;
  border-color: rgba(239, 68, 68, 0.4) !important;
  color: #f87171 !important;
}}

/* Sidebar user profile badge */
.sidebar-user-footer {{
  margin-top: 1.5rem;
  padding-top: 0.85rem;
  border-top: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0.75rem 0.6rem;
  border-radius: 10px;
  background: rgba(30, 14, 52, 0.4);
  border: 1px solid rgba(168, 85, 247, 0.15);
}}

.user-avatar-badge {{
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, #7c3aed, #a855f7);
  box-shadow: 0 0 10px rgba(168, 85, 247, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 14px;
  color: white;
}}

.user-name-text {{
  font-weight: 600;
  font-size: 0.88rem;
  color: #ffffff;
  line-height: 1.2;
}}

.user-tier-text {{
  font-size: 0.72rem;
  color: var(--purple-light);
  display: flex;
  align-items: center;
  gap: 4px;
}}

.user-tier-dot {{
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--purple-hover);
  box-shadow: 0 0 6px var(--purple-light);
}}

/* --- TOP NAVBAR --- */
.top-navbar {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.2rem 0 1.2rem;
  margin-bottom: 0.5rem;
}}

.top-model-pill {{
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: rgba(30, 15, 52, 0.5);
  border: 1px solid var(--border-medium);
  border-radius: 20px;
  padding: 6px 14px 6px 10px;
  font-size: 0.86rem;
  font-weight: 600;
  color: var(--text-main);
  backdrop-filter: blur(10px);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.25);
}}

.top-model-dot {{
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--purple-hover);
  box-shadow: 0 0 8px var(--purple-light);
}}

.top-model-sub {{
  color: var(--text-muted);
  font-size: 0.75rem;
  font-weight: 500;
}}

/* --- HERO FRONT PAGE BRANDING --- */
.hero-wrapper {{
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 12vh 1rem 4rem;
  animation: fadeIn 0.4s ease-out;
}}

@keyframes fadeIn {{
  from {{ opacity: 0; transform: translateY(8px); }}
  to {{ opacity: 1; transform: translateY(0); }}
}}

.hero-emblem {{
  width: 68px;
  height: 68px;
  border-radius: 50%;
  background: linear-gradient(135deg, #7c3aed, #a855f7);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 35px var(--purple-glow), 0 0 70px rgba(124, 58, 237, 0.3);
  margin-bottom: 1.5rem;
  border: 1px solid rgba(216, 180, 254, 0.3);
}}

.hero-emblem svg {{
  width: 34px;
  height: 34px;
  color: #ffffff;
}}

.hero-brand-title {{
  font-size: clamp(2.3rem, 5.5vw, 3.4rem);
  font-weight: 700;
  letter-spacing: -0.04em;
  color: #ffffff;
  margin: 0 0 0.65rem;
  line-height: 1.1;
}}

.hero-brand-title span {{
  background: linear-gradient(120deg, #ffffff 25%, #d8b4fe 65%, #c084fc 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}}

.hero-brand-subtitle {{
  font-size: 1.18rem;
  color: var(--text-muted);
  font-weight: 400;
  margin: 0;
  max-width: 500px;
}}

/* --- CHAT MESSAGES STYLING --- */
[data-testid="stChatMessage"] {{
  background: transparent !important;
  border: none !important;
  padding: 1.25rem 0.5rem !important;
  gap: 1rem !important;
  margin-bottom: 0.25rem !important;
}}

/* User Message Bubble */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]),
[data-testid="stChatMessage"]:has([alt="user avatar"]) {{
  background: rgba(59, 23, 98, 0.35) !important;
  border-radius: 16px !important;
  border: 1px solid var(--border-medium) !important;
  backdrop-filter: blur(8px) !important;
}}

[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] li {{
  line-height: 1.75;
  font-size: 1rem;
  color: #f3e8ff;
  overflow-wrap: anywhere;
}}

/* Code block formatting */
pre {{
  background-color: rgba(18, 9, 36, 0.88) !important;
  border: 1px solid var(--border-medium) !important;
  border-radius: 10px !important;
  padding: 1rem !important;
  box-shadow: 0 4px 18px rgba(0, 0, 0, 0.35) !important;
}}

code {{
  font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
  color: #d8b4fe !important;
  font-size: 0.92rem !important;
}}

pre code {{
  color: #f3e8ff !important;
}}

/* Blockquotes */
blockquote {{
  border-left: 3px solid var(--purple-hover) !important;
  padding-left: 1rem !important;
  margin-left: 0 !important;
  color: var(--text-muted) !important;
}}

/* --- COMPACT CHAT INPUT (SEARCH BAR SMALL) --- */
[data-testid="stBottom"] {{
  background: linear-gradient(180deg, transparent 0%, rgba(9, 3, 18, 0.88) 30%, #090312 100%) !important;
  padding-bottom: 1.2rem !important;
}}

[data-testid="stBottom"] > div {{
  background: transparent !important;
  max-width: 600px !important; /* Compact search bar width */
  margin: 0 auto !important;
  padding: 0 1rem !important;
}}

[data-testid="stChatInput"] {{
  background-color: var(--bg-input) !important;
  border: 1px solid var(--border-medium) !important;
  border-radius: 24px !important;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5), 0 0 14px rgba(147, 51, 234, 0.2) !important;
  padding: 2px 8px 2px 14px !important;
  max-width: 600px !important;
  margin: 0 auto !important;
  min-height: 44px !important;
  backdrop-filter: blur(12px) !important;
  transition: all 0.2s ease !important;
}}

[data-testid="stChatInput"]:focus-within {{
  border-color: rgba(192, 132, 252, 0.7) !important;
  box-shadow: 0 10px 35px rgba(0, 0, 0, 0.6), 0 0 20px rgba(168, 85, 247, 0.4) !important;
}}

[data-testid="stChatInput"] textarea {{
  color: var(--text-main) !important;
  font-size: 0.92rem !important;
  font-family: inherit !important;
  background: transparent !important;
  padding: 8px 0 !important;
}}

[data-testid="stChatInput"] textarea::placeholder {{
  color: var(--text-dim) !important;
}}

/* Upward circular send button with Purple Glow */
[data-testid="stChatInput"] button {{
  background: linear-gradient(135deg, #7c3aed, #a855f7) !important;
  color: #ffffff !important;
  border-radius: 50% !important;
  width: 32px !important;
  height: 32px !important;
  min-height: 32px !important;
  min-width: 32px !important;
  padding: 0 !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  border: none !important;
  box-shadow: 0 0 10px rgba(168, 85, 247, 0.5) !important;
  transition: all 0.18s ease !important;
}}

[data-testid="stChatInput"] button:disabled {{
  background: rgba(88, 28, 135, 0.35) !important;
  color: rgba(216, 180, 254, 0.35) !important;
  box-shadow: none !important;
  opacity: 0.45 !important;
}}

[data-testid="stChatInput"] button:hover:not(:disabled) {{
  background: linear-gradient(135deg, #9333ea, #c084fc) !important;
  box-shadow: 0 0 18px rgba(192, 132, 252, 0.8) !important;
  transform: scale(1.06) !important;
}}

.chat-disclaimer {{
  text-align: center;
  font-size: 0.74rem;
  color: var(--text-dim);
  margin-top: 0.55rem;
}}

/* Scrollbars */
::-webkit-scrollbar {{
  width: 6px;
  height: 6px;
}}
::-webkit-scrollbar-track {{
  background: transparent;
}}
::-webkit-scrollbar-thumb {{
  background: rgba(168, 85, 247, 0.22);
  border-radius: 8px;
}}
::-webkit-scrollbar-thumb:hover {{
  background: rgba(192, 132, 252, 0.45);
}}
</style>
""", unsafe_allow_html=True)


# =========================================================
# SIDEBAR: STRICTLY CONVERSATION HISTORY
# =========================================================
with st.sidebar:
    # Sidebar Brand
    st.markdown("""
    <div class="sidebar-brand-wrapper">
      <div class="sidebar-brand-logo">✦</div>
      <div class="sidebar-brand-name">Swaraj's ChatGPT</div>
    </div>
    """, unsafe_allow_html=True)

    # New chat action
    if st.button("＋   New chat", key="new_chat_button", use_container_width=True):
        st.session_state.chat_id = create_chat()
        st.rerun()

    st.markdown('<div class="sidebar-section-title">Recent Chats</div>', unsafe_allow_html=True)

    all_chats = get_chats()
    if not all_chats:
        st.caption("No previous chats yet.")
    else:
        for cid, title in all_chats:
            is_active = (cid == st.session_state.chat_id)
            col_chat, col_del = st.columns([0.83, 0.17], gap="small")

            display_title = (title or "New conversation").strip()
            if len(display_title) > 24:
                display_title = display_title[:22] + "…"

            button_label = f"💬  {display_title}"
            if col_chat.button(
                button_label,
                key=f"chat_open_{cid}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state.chat_id = cid
                st.rerun()

            with col_del:
                st.markdown('<div class="del-btn">', unsafe_allow_html=True)
                if st.button("✕", key=f"chat_del_{cid}", help="Delete chat", use_container_width=True):
                    delete_chat(cid)
                    if is_active:
                        remaining = get_chats()
                        st.session_state.chat_id = remaining[0][0] if remaining else create_chat()
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    # Bottom User profile badge
    st.markdown("""
    <div class="sidebar-user-footer">
      <div class="user-avatar-badge">S</div>
      <div>
        <div class="user-name-text">Swaraj</div>
        <div class="user-tier-text"><span class="user-tier-dot"></span> ChatGPT Plus</div>
      </div>
    </div>
    """, unsafe_allow_html=True)


# =========================================================
# MAIN CHAT AREA
# =========================================================
chat_id = st.session_state.chat_id
messages = get_messages(chat_id)

# Top Bar Pill
st.markdown("""
<div class="top-navbar">
  <div class="top-model-pill">
    <span class="top-model-dot"></span>
    <span>Swaraj's ChatGPT</span>
    <span class="top-model-sub">• 4o Turbo</span>
  </div>
</div>
""", unsafe_allow_html=True)

# Front Page Hero: Clean branding without prompt suggestion boxes
if not messages:
    st.markdown("""
    <div class="hero-wrapper">
      <div class="hero-emblem">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <defs>
            <linearGradient id="heroSparkleGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#ffffff"/>
              <stop offset="100%" stop-color="#c084fc"/>
            </linearGradient>
          </defs>
          <path d="M12 2L14.7 9.3L22 12L14.7 14.7L12 22L9.3 14.7L2 12L9.3 9.3L12 2Z" fill="url(#heroSparkleGrad)"/>
        </svg>
      </div>
      <h1 class="hero-brand-title"><span>Swaraj's ChatGPT</span></h1>
      <p class="hero-brand-subtitle">What can I help with today, Swaraj?</p>
    </div>
    """, unsafe_allow_html=True)

else:
    # Render all chat history messages
    for msg in messages:
        if msg["role"] not in ("user", "assistant"):
            continue
        avatar_icon = ASSISTANT_AVATAR if msg["role"] == "assistant" else USER_AVATAR
        with st.chat_message(msg["role"], avatar=avatar_icon):
            st.markdown(msg["content"])

# Bottom compact chat input bar
user_input = st.chat_input("Message Swaraj's ChatGPT…")

# Disclaimer under chatbox
st.markdown(
    '<div class="chat-disclaimer">Swaraj\'s ChatGPT can make mistakes. Verify important information.</div>',
    unsafe_allow_html=True,
)

# Process message submission
if user_input:
    # 1. Save and display user message
    save_message(chat_id, "user", user_input)
    with st.chat_message("user", avatar=USER_AVATAR):
        st.markdown(user_input)

    # 2. Generate assistant response
    with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
        try:
            history = get_messages(chat_id)[-20:]
            api_messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                *history,
            ]

            def stream_response(active_model):
                stream = client.chat.completions.create(
                    model=active_model,
                    messages=api_messages,
                    stream=True,
                )
                for chunk in stream:
                    if chunk.choices and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta
                        if hasattr(delta, "content") and delta.content:
                            yield delta.content

            try:
                full_response = st.write_stream(stream_response(MODEL))
            except Exception:
                # Automatic fallback to secondary model if primary encounters an issue
                full_response = st.write_stream(stream_response(FALLBACK_MODEL))

            if isinstance(full_response, str) and full_response.strip():
                save_message(chat_id, "assistant", full_response)
                st.rerun()

        except Exception as err:
            st.error(
                "Unable to connect to the AI engine. Please verify your internet connection "
                "and Groq API limits."
            )
            # Remove un-answered user prompt to maintain clean state
            with connect_db() as conn:
                conn.execute(
                    """DELETE FROM messages WHERE id = (
                        SELECT MAX(id) FROM messages
                        WHERE chat_id = ? AND role = 'user'
                    )""",
                    (chat_id,),
                )
