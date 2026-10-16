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

QUICK_STARTERS = [
    {
        "icon": "💡",
        "title": "Brainstorm AI ideas",
        "subtitle": "Discover innovative project & startup concepts",
        "prompt": "Give me 5 innovative, high-impact AI project ideas for my portfolio with technical stack recommendations.",
    },
    {
        "icon": "💻",
        "title": "Write & debug code",
        "subtitle": "Generate clean Python or full-stack snippets",
        "prompt": "Write a robust, production-ready Python script that fetches data from an API with exponential backoff and error handling.",
    },
    {
        "icon": "📝",
        "title": "Summarize & explain",
        "subtitle": "Break down complex topics into clear logic",
        "prompt": "Explain how modern transformer attention mechanisms work in simple, intuitive terms with an analogy.",
    },
    {
        "icon": "⚡",
        "title": "Plan & organize",
        "subtitle": "Create actionable routines and roadmaps",
        "prompt": "Design a high-productivity 7-day masterplan to sharpen advanced software engineering and system design skills.",
    },
]

# SVG Avatars for authentic ChatGPT feel
ASSISTANT_AVATAR = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 36 36' width='36' height='36'%3E"
    "%3Cdefs%3E%3ClinearGradient id='cgGrad' x1='0%25' y1='0%25' x2='100%25' y2='100%25'%3E"
    "%3Cstop offset='0%25' stop-color='%2310a37f'/%3E%3Cstop offset='100%25' stop-color='%2319c37d'/%3E"
    "%3C/linearGradient%3E%3C/defs%3E"
    "%3Crect width='36' height='36' rx='18' fill='url(%23cgGrad)'/%3E"
    "%3Cpath fill='%23ffffff' d='M18 7.5c-5.8 0-10.5 4.7-10.5 10.5 0 2.2.7 4.2 1.9 5.8l-1.2 4.4 4.5-1.2c1.6 1 3.4 1.5 5.3 1.5 5.8 0 10.5-4.7 10.5-10.5S23.8 7.5 18 7.5zm0 17.5c-1.6 0-3.1-.4-4.4-1.2l-.3-.2-3.1.8.8-3-.2-.3c-.9-1.3-1.4-2.8-1.4-4.4 0-4.7 3.8-8.5 8.5-8.5s8.5 3.8 8.5 8.5-3.8 8.3-8.4 8.3z'/%3E"
    "%3Ccircle cx='18' cy='18' r='3.2' fill='%23ffffff'/%3E"
    "%3C/svg%3E"
)

USER_AVATAR = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 36 36' width='36' height='36'%3E"
    "%3Cdefs%3E%3ClinearGradient id='uGrad' x1='0%25' y1='0%25' x2='100%25' y2='100%25'%3E"
    "%3Cstop offset='0%25' stop-color='%233b82f6'/%3E%3Cstop offset='100%25' stop-color='%238b5cf6'/%3E"
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

if "queued_prompt" not in st.session_state:
    st.session_state.queued_prompt = None


# =========================================================
# CHATGPT DARK THEME CSS
# =========================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

/* --- Root & Reset --- */
:root {
  --bg-app: #212121;
  --bg-sidebar: #171717;
  --bg-input: #2f2f2f;
  --bg-card: #262626;
  --bg-card-hover: #2f2f2f;
  --border-subtle: rgba(255, 255, 255, 0.08);
  --border-medium: rgba(255, 255, 255, 0.15);
  --border-hover: rgba(255, 255, 255, 0.28);
  --text-main: #ececec;
  --text-muted: #8e8e8e;
  --text-dim: #676767;
  --emerald: #10a37f;
  --emerald-hover: #19c37d;
  --emerald-glow: rgba(16, 163, 127, 0.35);
}

* {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
  box-sizing: border-box;
}

/* Hide default streamlit decorations */
#MainMenu, footer, header[data-testid="stHeader"] .stDeployButton, [data-testid="stDecoration"] {
  display: none !important;
}

header[data-testid="stHeader"] {
  background: transparent !important;
  border-bottom: none !important;
}

/* Main App background */
.stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
  background-color: var(--bg-app) !important;
  color: var(--text-main) !important;
}

.block-container {
  max-width: 820px !important;
  padding: 1.5rem 1.2rem 8.5rem !important;
}

/* --- SIDEBAR STYLING --- */
[data-testid="stSidebar"] {
  background-color: var(--bg-sidebar) !important;
  border-right: 1px solid var(--border-subtle) !important;
}

[data-testid="stSidebar"] > div:first-child {
  background-color: var(--bg-sidebar) !important;
  padding: 1rem 0.75rem !important;
}

/* Brand header in sidebar */
.sidebar-brand-wrapper {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0.4rem 0.5rem 1rem;
  border-bottom: 1px solid var(--border-subtle);
  margin-bottom: 1rem;
}

.sidebar-brand-logo {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: linear-gradient(135deg, var(--emerald), var(--emerald-hover));
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 12px var(--emerald-glow);
  color: white;
  font-size: 14px;
}

.sidebar-brand-name {
  font-weight: 700;
  font-size: 1.05rem;
  letter-spacing: -0.02em;
  color: #ffffff;
}

.sidebar-section-title {
  color: var(--text-dim);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin: 1.1rem 0.5rem 0.5rem;
}

/* New chat button */
[data-testid="stSidebar"] .stButton.new-chat-button > button,
[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:nth-child(2) .stButton > button {
  background: #212121 !important;
  border: 1px solid var(--border-medium) !important;
  color: var(--text-main) !important;
  border-radius: 10px !important;
  font-weight: 500 !important;
  font-size: 0.88rem !important;
  padding: 0.65rem 0.85rem !important;
  transition: all 0.2s ease !important;
  text-align: left !important;
  justify-content: flex-start !important;
}

[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:nth-child(2) .stButton > button:hover {
  background: #2a2a2a !important;
  border-color: var(--border-hover) !important;
  color: #ffffff !important;
  transform: translateY(-1px);
}

/* Conversation item buttons */
[data-testid="stSidebar"] .stButton > button {
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
}

/* Active chat button */
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
  background-color: #262626 !important;
  border: 1px solid var(--border-medium) !important;
  color: #ffffff !important;
  font-weight: 600 !important;
}

[data-testid="stSidebar"] .stButton > button:hover {
  background-color: #212121 !important;
  border-color: var(--border-subtle) !important;
  color: #ffffff !important;
}

/* Delete button styling */
[data-testid="stSidebar"] .del-btn .stButton > button {
  text-align: center !important;
  justify-content: center !important;
  padding: 0.45rem 0.3rem !important;
  color: var(--text-dim) !important;
}

[data-testid="stSidebar"] .del-btn .stButton > button:hover {
  background: rgba(239, 68, 68, 0.15) !important;
  border-color: rgba(239, 68, 68, 0.3) !important;
  color: #ef4444 !important;
}

/* Sidebar user profile badge */
.sidebar-user-footer {
  margin-top: 1.5rem;
  padding-top: 0.85rem;
  border-top: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0.75rem 0.6rem;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.02);
}

.user-avatar-badge {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 14px;
  color: white;
}

.user-name-text {
  font-weight: 600;
  font-size: 0.88rem;
  color: #ffffff;
  line-height: 1.2;
}

.user-tier-text {
  font-size: 0.72rem;
  color: var(--emerald-hover);
  display: flex;
  align-items: center;
  gap: 4px;
}

.user-tier-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--emerald);
  box-shadow: 0 0 6px var(--emerald);
}

/* --- TOP NAVBAR --- */
.top-navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.2rem 0 1.2rem;
  margin-bottom: 0.5rem;
}

.top-model-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--border-subtle);
  border-radius: 20px;
  padding: 6px 14px 6px 10px;
  font-size: 0.86rem;
  font-weight: 600;
  color: var(--text-main);
  backdrop-filter: blur(8px);
}

.top-model-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--emerald);
  box-shadow: 0 0 8px var(--emerald);
}

.top-model-sub {
  color: var(--text-muted);
  font-size: 0.75rem;
  font-weight: 500;
}

/* --- HERO FRONT PAGE BRANDING --- */
.hero-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 7vh 1rem 2.8rem;
  animation: fadeIn 0.4s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.hero-emblem {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: linear-gradient(135deg, #10a37f, #19c37d);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 35px var(--emerald-glow), 0 0 70px rgba(16, 163, 127, 0.15);
  margin-bottom: 1.5rem;
}

.hero-emblem svg {
  width: 34px;
  height: 34px;
  color: #ffffff;
}

.hero-brand-title {
  font-size: clamp(2.2rem, 5vw, 3.2rem);
  font-weight: 700;
  letter-spacing: -0.04em;
  color: #ffffff;
  margin: 0 0 0.55rem;
  line-height: 1.1;
}

.hero-brand-title span {
  background: linear-gradient(120deg, #ffffff 40%, #6ee7b7 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.hero-brand-subtitle {
  font-size: 1.15rem;
  color: var(--text-muted);
  font-weight: 400;
  margin: 0 0 2rem;
  max-width: 500px;
}

/* Prompt starter cards */
.prompt-grid-container .stButton > button {
  background: var(--bg-card) !important;
  border: 1px solid var(--border-subtle) !important;
  border-radius: 14px !important;
  padding: 0.95rem 1.1rem !important;
  text-align: left !important;
  justify-content: flex-start !important;
  color: var(--text-main) !important;
  min-height: 4.8rem !important;
  width: 100% !important;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
}

.prompt-grid-container .stButton > button:hover {
  background: var(--bg-card-hover) !important;
  border-color: var(--border-hover) !important;
  color: #ffffff !important;
  transform: translateY(-2px) !important;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3) !important;
}

/* --- CHAT MESSAGES STYLING --- */
[data-testid="stChatMessage"] {
  background: transparent !important;
  border: none !important;
  padding: 1.25rem 0.5rem !important;
  gap: 1rem !important;
  margin-bottom: 0.25rem !important;
}

/* User Message Bubble */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
  background: rgba(47, 47, 47, 0.45) !important;
  border-radius: 16px !important;
  border: 1px solid var(--border-subtle) !important;
}

[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] li {
  line-height: 1.75;
  font-size: 1rem;
  color: #ececec;
  overflow-wrap: anywhere;
}

/* Code block formatting */
pre {
  background-color: #181818 !important;
  border: 1px solid var(--border-medium) !important;
  border-radius: 10px !important;
  padding: 1rem !important;
  box-shadow: 0 4px 15px rgba(0,0,0,0.2) !important;
}

code {
  font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
  color: #6ee7b7 !important;
  font-size: 0.92rem !important;
}

pre code {
  color: #e2e8f0 !important;
}

/* Blockquotes */
blockquote {
  border-left: 3px solid var(--emerald) !important;
  padding-left: 1rem !important;
  margin-left: 0 !important;
  color: var(--text-muted) !important;
}

/* --- CHAT INPUT & BOTTOM BAR --- */
[data-testid="stBottom"] {
  background: linear-gradient(180deg, transparent 0%, #212121 28%, #212121 100%) !important;
  padding-bottom: 1.2rem !important;
}

[data-testid="stBottom"] > div {
  background: transparent !important;
  max-width: 820px !important;
  margin: 0 auto !important;
}

[data-testid="stChatInput"] {
  background-color: var(--bg-input) !important;
  border: 1px solid var(--border-medium) !important;
  border-radius: 26px !important;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.35) !important;
  padding: 4px 8px 4px 14px !important;
  transition: all 0.2s ease !important;
}

[data-testid="stChatInput"]:focus-within {
  border-color: rgba(255, 255, 255, 0.35) !important;
  box-shadow: 0 10px 35px rgba(0, 0, 0, 0.45), 0 0 0 1px rgba(255, 255, 255, 0.15) !important;
}

[data-testid="stChatInput"] textarea {
  color: var(--text-main) !important;
  font-size: 0.98rem !important;
  font-family: inherit !important;
  background: transparent !important;
}

[data-testid="stChatInput"] textarea::placeholder {
  color: var(--text-muted) !important;
}

/* Upward circular send button */
[data-testid="stChatInput"] button {
  background-color: #ececec !important;
  color: #171717 !important;
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
  transition: all 0.15s ease !important;
}

[data-testid="stChatInput"] button:disabled {
  background-color: #3e3e3e !important;
  color: #676767 !important;
  opacity: 0.45 !important;
}

[data-testid="stChatInput"] button:hover:not(:disabled) {
  background-color: #ffffff !important;
  transform: scale(1.05) !important;
}

.chat-disclaimer {
  text-align: center;
  font-size: 0.74rem;
  color: var(--text-dim);
  margin-top: 0.55rem;
}

/* Scrollbars */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.16);
  border-radius: 8px;
}
::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.28);
}
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
        st.session_state.queued_prompt = None
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
                st.session_state.queued_prompt = None
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

    # Bottom User profile badge (ChatGPT style)
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
queued_prompt = st.session_state.pop("queued_prompt", None)

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

# Front Page Hero when conversation is fresh
if not messages and not queued_prompt:
    st.markdown("""
    <div class="hero-wrapper">
      <div class="hero-emblem">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
        </svg>
      </div>
      <h1 class="hero-brand-title"><span>Swaraj's ChatGPT</span></h1>
      <p class="hero-brand-subtitle">What can I help with today, Swaraj?</p>
    </div>
    """, unsafe_allow_html=True)

    # Interactive ChatGPT Prompt Cards
    st.markdown('<div class="prompt-grid-container">', unsafe_allow_html=True)
    c1, c2 = st.columns(2, gap="small")
    for idx, item in enumerate(QUICK_STARTERS):
        target = c1 if idx % 2 == 0 else c2
        card_text = f"{item['icon']}  {item['title']}\n\n{item['subtitle']}"
        if target.button(card_text, key=f"quick_starter_{idx}", use_container_width=True):
            st.session_state.queued_prompt = item["prompt"]
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

else:
    # Render all chat history messages
    for msg in messages:
        if msg["role"] not in ("user", "assistant"):
            continue
        avatar_icon = ASSISTANT_AVATAR if msg["role"] == "assistant" else USER_AVATAR
        with st.chat_message(msg["role"], avatar=avatar_icon):
            st.markdown(msg["content"])

# Bottom chat input bar
user_input = st.chat_input("Message Swaraj's ChatGPT…") or queued_prompt

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
