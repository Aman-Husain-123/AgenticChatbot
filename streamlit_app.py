"""
AI Chatbot — Streamlit UI
Features: Streaming · SQLite Persistence · Human-in-the-Loop
"""

import time
from datetime import datetime, timezone
from uuid import uuid4

import streamlit as st
from langchain_core.messages import HumanMessage

from app.config import settings
from app.database.connection import (
    create_chat,
    delete_chat,
    get_chat,
    get_messages,
    initialize_database,
    list_chats,
    save_message,
    update_chat_title,
)
from app.graphs.chat_graph import chat_graph


# ── Page config ───────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Chatbot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── CSS ───────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* ── Global reset ───────────────────────────────── */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* ── Hide default Streamlit chrome ─────────────── */
    #MainMenu, footer, header { visibility: hidden; }
    .stDeployButton { display: none; }

    /* ── Root background ────────────────────────────── */
    .stApp {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
        min-height: 100vh;
    }

    /* ── Sidebar ────────────────────────────────────── */
    [data-testid="stSidebar"] {
        background: rgba(15, 12, 41, 0.85) !important;
        backdrop-filter: blur(20px);
        border-right: 1px solid rgba(255,255,255,0.08);
    }
    [data-testid="stSidebar"] * { color: #e2e8f0 !important; }

    /* ── Sidebar header ────────────────────────────── */
    .sidebar-header {
        text-align: center;
        padding: 1.5rem 0 1rem 0;
        border-bottom: 1px solid rgba(255,255,255,0.08);
        margin-bottom: 1rem;
    }
    .sidebar-header h1 {
        font-size: 1.4rem;
        font-weight: 700;
        background: linear-gradient(90deg, #a78bfa, #60a5fa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0.3rem 0 0 0;
    }
    .sidebar-header p {
        font-size: 0.75rem;
        color: rgba(255,255,255,0.45) !important;
        margin: 0;
    }

    /* ── Chat list item ─────────────────────────────── */
    .chat-item {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.65rem 0.75rem;
        border-radius: 10px;
        cursor: pointer;
        transition: background 0.2s;
        margin-bottom: 0.25rem;
        border: 1px solid transparent;
    }
    .chat-item:hover {
        background: rgba(167,139,250,0.12);
        border-color: rgba(167,139,250,0.3);
    }
    .chat-item.active {
        background: rgba(167,139,250,0.2);
        border-color: rgba(167,139,250,0.5);
    }
    .chat-item-title {
        flex: 1;
        font-size: 0.85rem;
        font-weight: 500;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .chat-item-date {
        font-size: 0.65rem;
        color: rgba(255,255,255,0.4) !important;
    }

    /* ── New chat button ─────────────────────────────── */
    .stButton > button {
        background: linear-gradient(135deg, #7c3aed, #2563eb) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        font-size: 0.875rem !important;
        padding: 0.6rem 1.2rem !important;
        width: 100% !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(124,58,237,0.4) !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(124,58,237,0.6) !important;
    }

    /* ── Main chat area ─────────────────────────────── */
    .main-container {
        max-width: 860px;
        margin: 0 auto;
        padding: 1rem 1.5rem 6rem 1.5rem;
    }

    /* ── Chat header ────────────────────────────────── */
    .chat-header {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 1rem 0 1.5rem 0;
        border-bottom: 1px solid rgba(255,255,255,0.08);
        margin-bottom: 1.5rem;
    }
    .chat-title {
        font-size: 1.3rem;
        font-weight: 600;
        color: white;
    }
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        background: rgba(16,185,129,0.15);
        border: 1px solid rgba(16,185,129,0.3);
        color: #10b981 !important;
        font-size: 0.7rem;
        font-weight: 600;
        padding: 0.2rem 0.6rem;
        border-radius: 20px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* ── Message bubbles ─────────────────────────────── */
    .message-row {
        display: flex;
        gap: 0.75rem;
        margin-bottom: 1.25rem;
        animation: fadeInUp 0.3s ease;
    }
    .message-row.user { flex-direction: row-reverse; }

    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(12px); }
        to   { opacity: 1; transform: translateY(0); }
    }

    .avatar {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1rem;
        flex-shrink: 0;
        margin-top: 2px;
    }
    .avatar.ai   { background: linear-gradient(135deg, #7c3aed, #2563eb); }
    .avatar.user { background: linear-gradient(135deg, #059669, #0284c7); }

    .bubble {
        max-width: 72%;
        padding: 0.85rem 1.1rem;
        border-radius: 16px;
        font-size: 0.9rem;
        line-height: 1.65;
        word-break: break-word;
    }
    .bubble.ai {
        background: rgba(255,255,255,0.07);
        border: 1px solid rgba(255,255,255,0.1);
        color: #e2e8f0;
        border-top-left-radius: 4px;
    }
    .bubble.user {
        background: linear-gradient(135deg, rgba(124,58,237,0.5), rgba(37,99,235,0.5));
        border: 1px solid rgba(124,58,237,0.4);
        color: white;
        border-top-right-radius: 4px;
    }
    .bubble-time {
        font-size: 0.65rem;
        color: rgba(255,255,255,0.35);
        margin-top: 0.35rem;
        text-align: right;
    }

    /* ── Human-in-the-Loop review card ──────────────── */
    .hitl-card {
        background: linear-gradient(135deg,
            rgba(234,179,8,0.12), rgba(239,68,68,0.08));
        border: 1px solid rgba(234,179,8,0.35);
        border-radius: 16px;
        padding: 1.2rem 1.4rem;
        margin: 1rem 0;
        animation: fadeInUp 0.3s ease;
    }
    .hitl-title {
        font-size: 0.78rem;
        font-weight: 700;
        color: #fbbf24 !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.6rem;
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }
    .hitl-message {
        background: rgba(0,0,0,0.25);
        border-radius: 10px;
        padding: 0.8rem 1rem;
        font-size: 0.88rem;
        color: #e2e8f0 !important;
        margin-bottom: 1rem;
        line-height: 1.6;
        border-left: 3px solid #fbbf24;
    }

    /* ── Welcome screen ─────────────────────────────── */
    .welcome-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 60vh;
        text-align: center;
        padding: 2rem;
    }
    .welcome-orb {
        width: 90px;
        height: 90px;
        background: linear-gradient(135deg, #7c3aed, #2563eb);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 2.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 0 40px rgba(124,58,237,0.5);
        animation: pulse 2.5s ease-in-out infinite;
    }
    @keyframes pulse {
        0%, 100% { box-shadow: 0 0 40px rgba(124,58,237,0.5); }
        50%       { box-shadow: 0 0 70px rgba(124,58,237,0.8); }
    }
    .welcome-title {
        font-size: 2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #a78bfa, #60a5fa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.75rem;
    }
    .welcome-sub {
        color: rgba(255,255,255,0.5);
        font-size: 0.95rem;
        max-width: 400px;
        line-height: 1.6;
    }

    /* ── Feature pills ──────────────────────────────── */
    .feature-pills {
        display: flex;
        gap: 0.6rem;
        margin-top: 1.5rem;
        flex-wrap: wrap;
        justify-content: center;
    }
    .pill {
        background: rgba(255,255,255,0.06);
        border: 1px solid rgba(255,255,255,0.12);
        border-radius: 20px;
        padding: 0.35rem 0.9rem;
        font-size: 0.78rem;
        color: rgba(255,255,255,0.7);
    }

    /* ── Chat input ─────────────────────────────────── */
    .stChatInputContainer {
        position: fixed !important;
        bottom: 0 !important;
        left: 0 !important;
        right: 0 !important;
        background: rgba(15,12,41,0.9) !important;
        backdrop-filter: blur(20px) !important;
        border-top: 1px solid rgba(255,255,255,0.08) !important;
        padding: 1rem 2rem !important;
        z-index: 999 !important;
    }
    [data-testid="stChatInput"] {
        background: rgba(255,255,255,0.07) !important;
        border: 1px solid rgba(255,255,255,0.15) !important;
        border-radius: 12px !important;
        color: white !important;
    }
    [data-testid="stChatInput"]:focus {
        border-color: rgba(167,139,250,0.6) !important;
        box-shadow: 0 0 0 3px rgba(124,58,237,0.2) !important;
    }

    /* ── Typing indicator ───────────────────────────── */
    .typing-dots {
        display: flex;
        gap: 5px;
        align-items: center;
        padding: 0.6rem 0;
    }
    .typing-dots span {
        width: 8px;
        height: 8px;
        background: #7c3aed;
        border-radius: 50%;
        animation: bounce 1.2s infinite;
    }
    .typing-dots span:nth-child(2) { animation-delay: 0.2s; }
    .typing-dots span:nth-child(3) { animation-delay: 0.4s; }
    @keyframes bounce {
        0%, 60%, 100% { transform: translateY(0); }
        30%            { transform: translateY(-8px); }
    }

    /* ── Model badge ────────────────────────────────── */
    .model-badge {
        background: rgba(167,139,250,0.12);
        border: 1px solid rgba(167,139,250,0.25);
        color: #a78bfa !important;
        font-size: 0.7rem;
        padding: 0.2rem 0.6rem;
        border-radius: 20px;
        font-weight: 500;
    }

    /* ── Scrollbar ──────────────────────────────────── */
    ::-webkit-scrollbar { width: 5px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb {
        background: rgba(167,139,250,0.3);
        border-radius: 3px;
    }
    ::-webkit-scrollbar-thumb:hover { background: rgba(167,139,250,0.5); }

    /* ── Delete button  ─────────────────────────────── */
    .delete-btn button {
        background: rgba(239,68,68,0.15) !important;
        border: 1px solid rgba(239,68,68,0.3) !important;
        color: #f87171 !important;
        padding: 0.25rem 0.6rem !important;
        font-size: 0.75rem !important;
        box-shadow: none !important;
        width: auto !important;
    }
    .delete-btn button:hover {
        background: rgba(239,68,68,0.3) !important;
        transform: none !important;
        box-shadow: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Helpers ───────────────────────────────────────────────────────

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def fmt_time(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%H:%M")
    except Exception:
        return ""


def fmt_date(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso)
        today = datetime.now(timezone.utc).date()
        d = dt.date() if dt.tzinfo else dt.date()
        if d == today:
            return "Today"
        return dt.strftime("%b %d")
    except Exception:
        return ""


def truncate(text: str, n: int = 28) -> str:
    return text[:n] + "…" if len(text) > n else text


# ── Init ──────────────────────────────────────────────────────────

initialize_database()

if "active_chat_id" not in st.session_state:
    st.session_state.active_chat_id = None
if "pending_hitl" not in st.session_state:
    st.session_state.pending_hitl = None   # {"message": str, "config": dict}
if "is_generating" not in st.session_state:
    st.session_state.is_generating = False
if "rename_mode" not in st.session_state:
    st.session_state.rename_mode = False


# ── Sidebar ───────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-header">
            <div style="font-size:2rem">🤖</div>
            <h1>AI Chatbot</h1>
            <p>Powered by LangGraph</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("＋  New Chat", key="new_chat_btn"):
        chat_id = str(uuid4())
        create_chat(
            chat_id=chat_id,
            title="New Chat",
            created_at=now_iso(),
        )
        st.session_state.active_chat_id = chat_id
        st.session_state.pending_hitl = None
        st.rerun()

    st.markdown(
        "<div style='margin: 1rem 0 0.5rem 0; font-size:0.7rem;"
        "text-transform:uppercase; letter-spacing:0.08em;"
        "color:rgba(255,255,255,0.35); font-weight:600;'>Conversations</div>",
        unsafe_allow_html=True,
    )

    chats = list_chats()

    if not chats:
        st.markdown(
            "<div style='color:rgba(255,255,255,0.35); font-size:0.8rem;"
            "text-align:center; padding:1rem 0;'>No conversations yet.<br>"
            "Start one above!</div>",
            unsafe_allow_html=True,
        )
    else:
        for chat in chats:
            is_active = chat["id"] == st.session_state.active_chat_id
            active_class = "active" if is_active else ""

            col_btn, col_del = st.columns([5, 1])

            with col_btn:
                label = f"{'💬' if is_active else '🗨️'}  {truncate(chat['title'])}"
                if st.button(
                    label,
                    key=f"chat_{chat['id']}",
                    use_container_width=True,
                ):
                    st.session_state.active_chat_id = chat["id"]
                    st.session_state.pending_hitl = None
                    st.session_state.rename_mode = False
                    st.rerun()

            with col_del:
                st.markdown('<div class="delete-btn">', unsafe_allow_html=True)
                if st.button("🗑", key=f"del_{chat['id']}"):
                    delete_chat(chat["id"])
                    if st.session_state.active_chat_id == chat["id"]:
                        st.session_state.active_chat_id = None
                        st.session_state.pending_hitl = None
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

    # ── Model info ────────────────────────────────────
    st.markdown("<div style='margin-top:auto; padding-top:2rem;'>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div style='border-top:1px solid rgba(255,255,255,0.08);
        padding-top:1rem; margin-top:1rem;'>
            <div style='font-size:0.7rem; color:rgba(255,255,255,0.35);
            margin-bottom:0.4rem;'>MODEL</div>
            <span class="model-badge">✦ {settings.OPENAI_MODEL}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div style='margin-top:0.75rem;'>
            <div style='font-size:0.7rem; color:rgba(255,255,255,0.35);
            margin-bottom:0.4rem;'>FEATURES</div>
            <div style='display:flex; flex-direction:column; gap:0.3rem;
            font-size:0.75rem; color:rgba(255,255,255,0.55);'>
                <span>⚡ Token streaming</span>
                <span>🗄️ SQLite persistence</span>
                <span>🧠 LangGraph memory</span>
                <span>👁️ Human-in-the-Loop</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)


# ── Main area ─────────────────────────────────────────────────────

chat_id = st.session_state.active_chat_id

if chat_id is None:
    # Welcome screen
    st.markdown(
        """
        <div class="welcome-container">
            <div class="welcome-orb">🤖</div>
            <div class="welcome-title">Welcome to AI Chatbot</div>
            <div class="welcome-sub">
                A LangGraph-powered assistant with streaming responses,
                persistent memory, and human-in-the-loop review.
            </div>
            <div class="feature-pills">
                <span class="pill">⚡ Streaming</span>
                <span class="pill">🗄️ Persistence</span>
                <span class="pill">🧠 Memory</span>
                <span class="pill">👁️ Human Review</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

else:
    chat_meta = get_chat(chat_id)

    if chat_meta is None:
        st.error("Chat not found. Please select another.")
    else:
        # ── Chat header ───────────────────────────────
        h_col1, h_col2 = st.columns([6, 1])

        with h_col1:
            if st.session_state.rename_mode:
                new_title = st.text_input(
                    "Rename chat",
                    value=chat_meta["title"],
                    key="rename_input",
                    label_visibility="collapsed",
                )
                r1, r2 = st.columns([1, 1])
                with r1:
                    if st.button("✓ Save", key="save_rename"):
                        update_chat_title(chat_id, new_title.strip() or chat_meta["title"])
                        st.session_state.rename_mode = False
                        st.rerun()
                with r2:
                    if st.button("✕ Cancel", key="cancel_rename"):
                        st.session_state.rename_mode = False
                        st.rerun()
            else:
                st.markdown(
                    f"""
                    <div class="chat-header">
                        <div class="chat-title">{chat_meta['title']}</div>
                        <span class="status-badge">● Live</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        with h_col2:
            if not st.session_state.rename_mode:
                if st.button("✏️ Rename", key="rename_btn"):
                    st.session_state.rename_mode = True
                    st.rerun()

        # ── Load and render messages ──────────────────
        db_messages = get_messages(chat_id)

        for msg in db_messages:
            role = msg["role"]
            content = msg["content"]
            ts = fmt_time(msg["created_at"])

            if role == "user":
                st.markdown(
                    f"""
                    <div class="message-row user">
                        <div>
                            <div class="bubble user">{content}</div>
                            <div class="bubble-time">{ts}</div>
                        </div>
                        <div class="avatar user">👤</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"""
                    <div class="message-row">
                        <div class="avatar ai">🤖</div>
                        <div>
                            <div class="bubble ai">{content}</div>
                            <div class="bubble-time">{ts}</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        # ── Human-in-the-Loop review panel ───────────
        pending = st.session_state.pending_hitl

        if pending:
            st.markdown(
                f"""
                <div class="hitl-card">
                    <div class="hitl-title">⚠️ Human Review Required</div>
                    <p style="font-size:0.8rem; color:rgba(255,255,255,0.55);
                    margin-bottom:0.75rem;">
                        The AI wants to send the response below.
                        Please review and approve or reject it.
                    </p>
                    <div class="hitl-message">{pending['message']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            col_a, col_r, _ = st.columns([2, 2, 3])

            with col_a:
                if st.button("✅ Approve", key="hitl_approve", type="primary"):
                    config = pending["config"]

                    # Resume graph with "approve"
                    final_parts = []
                    for msg_chunk, meta in chat_graph.stream(
                        {"messages": None},
                        config=config,
                        stream_mode="messages",
                    ):
                        pass  # graph resumes & ends

                    # The approved message was already yielded during the
                    # interrupted run; save it to DB.
                    save_message(
                        chat_id=chat_id,
                        role="assistant",
                        content=pending["message"],
                        created_at=now_iso(),
                    )

                    # Resume the graph to pass the "approve" decision
                    chat_graph.invoke(
                        {"messages": None},
                        config={**config, "input": "approve"},
                    )

                    st.session_state.pending_hitl = None
                    st.rerun()

            with col_r:
                if st.button("❌ Reject", key="hitl_reject"):
                    config = pending["config"]

                    # Resume graph with "reject" decision
                    result = chat_graph.invoke(
                        None,
                        config={
                            **config,
                            "configurable": {
                                **config.get("configurable", {}),
                                "interrupt_input": "reject",
                            },
                        },
                    )

                    # Save the replacement message
                    if result and result.get("messages"):
                        last = result["messages"][-1]
                        save_message(
                            chat_id=chat_id,
                            role="assistant",
                            content=last.content,
                            created_at=now_iso(),
                        )

                    st.session_state.pending_hitl = None
                    st.rerun()

        # ── Empty state ───────────────────────────────
        if not db_messages and not pending:
            st.markdown(
                """
                <div style="text-align:center; padding:3rem 0;
                color:rgba(255,255,255,0.3);">
                    <div style="font-size:2.5rem; margin-bottom:0.75rem;">💬</div>
                    <div style="font-size:0.9rem;">Send a message to start chatting</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # ── Chat input ────────────────────────────────
        user_input = st.chat_input(
            "Message AI Chatbot...",
            key="chat_input",
            disabled=bool(pending),
        )

        if user_input and user_input.strip():
            user_text = user_input.strip()
            ts_now = now_iso()

            # Save user message to DB
            save_message(
                chat_id=chat_id,
                role="user",
                content=user_text,
                created_at=ts_now,
            )

            # Auto-title the chat from first message
            if chat_meta["title"] == "New Chat":
                short = user_text[:40] + ("…" if len(user_text) > 40 else "")
                update_chat_title(chat_id, short)

            # Show user bubble immediately
            st.markdown(
                f"""
                <div class="message-row user">
                    <div>
                        <div class="bubble user">{user_text}</div>
                        <div class="bubble-time">{fmt_time(ts_now)}</div>
                    </div>
                    <div class="avatar user">👤</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Typing indicator + streaming response
            with st.empty():
                st.markdown(
                    """
                    <div class="message-row">
                        <div class="avatar ai">🤖</div>
                        <div class="bubble ai">
                            <div class="typing-dots">
                                <span></span><span></span><span></span>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                config = {
                    "configurable": {"thread_id": chat_id}
                }

                collected_tokens: list[str] = []
                interrupted = False
                interrupt_payload = None
                streaming_placeholder = st.empty()

                try:
                    for event in chat_graph.stream(
                        {"messages": [HumanMessage(content=user_text)]},
                        config=config,
                        stream_mode="messages",
                    ):
                        msg_chunk, metadata = event

                        # Detect interrupt
                        if hasattr(msg_chunk, "type") and msg_chunk.type == "__interrupt__":
                            interrupted = True
                            interrupt_payload = msg_chunk.value[0].value
                            break

                        from langchain_core.messages import AIMessageChunk
                        if not isinstance(msg_chunk, AIMessageChunk):
                            continue
                        if not isinstance(msg_chunk.content, str):
                            continue
                        if not msg_chunk.content:
                            continue

                        collected_tokens.append(msg_chunk.content)
                        partial = "".join(collected_tokens)

                        streaming_placeholder.markdown(
                            f"""
                            <div class="message-row">
                                <div class="avatar ai">🤖</div>
                                <div class="bubble ai">{partial} ▍</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                except Exception as e:
                    # Handle LangGraph interrupt signal
                    exc_str = str(e)
                    if "interrupt" in exc_str.lower() or "GraphInterrupt" in type(e).__name__:
                        interrupted = True
                        # Try to get the interrupt value
                        try:
                            state = chat_graph.get_state(config)
                            if state.tasks:
                                for task in state.tasks:
                                    if hasattr(task, "interrupts") and task.interrupts:
                                        interrupt_payload = task.interrupts[0].value
                                        break
                        except Exception:
                            pass
                    else:
                        streaming_placeholder.markdown(
                            f"""
                            <div class="message-row">
                                <div class="avatar ai">🤖</div>
                                <div class="bubble ai" style="color:#f87171;">
                                    ⚠️ Error: {exc_str}
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                full_response = "".join(collected_tokens)

                if interrupted and interrupt_payload:
                    # Human review needed — surface the review UI
                    pending_msg = interrupt_payload.get(
                        "pending_message", full_response
                    )
                    st.session_state.pending_hitl = {
                        "message": pending_msg,
                        "config": config,
                    }
                    streaming_placeholder.empty()
                elif full_response:
                    # No interruption — show final bubble & save
                    streaming_placeholder.markdown(
                        f"""
                        <div class="message-row">
                            <div class="avatar ai">🤖</div>
                            <div>
                                <div class="bubble ai">{full_response}</div>
                                <div class="bubble-time">{fmt_time(now_iso())}</div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    save_message(
                        chat_id=chat_id,
                        role="assistant",
                        content=full_response,
                        created_at=now_iso(),
                    )

            st.rerun()
