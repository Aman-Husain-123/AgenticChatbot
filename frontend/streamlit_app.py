import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import streamlit as st

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load direct app modules
from app.database.connection import (
    create_chat as db_create_chat,
    delete_chat as db_delete_chat,
    get_chat as db_get_chat,
    get_messages as db_get_messages,
    initialize_database,
    list_chats as db_list_chats,
    save_message as db_save_message,
)
from app.graphs.chat_graph import chat_graph
from langchain_core.messages import AIMessageChunk, HumanMessage
from langgraph.types import Command

# Initialize SQLite database on startup
initialize_database()

st.set_page_config(
    page_title="Agentic Chatbot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling for polished UI
st.markdown(
    """
    <style>
    .chat-header {
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        color: #ffffff;
    }
    .chat-sub {
        color: #94a3b8;
        font-size: 0.95rem;
        margin-bottom: 1.5rem;
    }
    .hitl-box {
        background: rgba(245, 158, 11, 0.1);
        border: 1px solid rgba(245, 158, 11, 0.4);
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Session State Initialization ──────────────────────────────────────────────
if "chat_id" not in st.session_state:
    st.session_state.chat_id = None

if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_hitl" not in st.session_state:
    st.session_state.pending_hitl = None


def current_time_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_new_chat():
    new_id = str(uuid4())
    db_create_chat(
        chat_id=new_id,
        title="New Chat",
        created_at=current_time_iso(),
    )
    st.session_state.chat_id = new_id
    st.session_state.messages = []
    st.session_state.pending_hitl = None


def delete_existing_chat(chat_id: str):
    db_delete_chat(chat_id)
    if st.session_state.chat_id == chat_id:
        st.session_state.chat_id = None
        st.session_state.messages = []
        st.session_state.pending_hitl = None


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 💬 Conversations")

    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        create_new_chat()
        st.rerun()

    st.divider()

    chats = db_list_chats()

    if not chats:
        st.caption("No conversations yet. Start one above!")
    else:
        for chat in chats:
            col_chat, col_del = st.columns([0.82, 0.18])
            is_active = chat["id"] == st.session_state.chat_id
            btn_label = f"▸ {chat['title']}" if is_active else chat["title"]

            with col_chat:
                if st.button(
                    btn_label,
                    key=f"select_{chat['id']}",
                    use_container_width=True,
                ):
                    st.session_state.chat_id = chat["id"]
                    st.session_state.messages = db_get_messages(chat["id"])
                    st.session_state.pending_hitl = None
                    st.rerun()

            with col_del:
                if st.button("🗑️", key=f"del_{chat['id']}", help="Delete chat"):
                    delete_existing_chat(chat["id"])
                    st.rerun()


# ── Main Chat Area ────────────────────────────────────────────────────────────
st.markdown('<div class="chat-header">🤖 Agentic Chatbot</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="chat-sub">Powered by LangGraph, SQLite Persistence & Human-in-the-Loop</div>',
    unsafe_allow_html=True,
)

if st.session_state.chat_id is None:
    st.info("👈 Click **➕ New Chat** in the sidebar to start a conversation.")
else:
    # Display existing messages from database
    st.session_state.messages = db_get_messages(st.session_state.chat_id)

    for message in st.session_state.messages:
        role = "assistant" if message["role"] == "assistant" else "user"
        with st.chat_message(role):
            st.markdown(message["content"])

    # Human-in-the-Loop Approval UI (if paused)
    if st.session_state.pending_hitl:
        hitl = st.session_state.pending_hitl
        st.warning("⚠️ **Human-in-the-Loop: Review Required**")
        st.info(f"**Proposed Response:**\n\n{hitl['pending_message']}")

        col_approve, col_reject = st.columns(2)
        with col_approve:
            if st.button("✅ Approve Action", use_container_width=True, type="primary"):
                config = {"configurable": {"thread_id": st.session_state.chat_id}}
                try:
                    # Resume LangGraph with approval
                    for chunk, _ in chat_graph.stream(
                        Command(resume="approve"),
                        config=config,
                        stream_mode="messages",
                    ):
                        pass
                except Exception:
                    pass

                db_save_message(
                    chat_id=st.session_state.chat_id,
                    role="assistant",
                    content=hitl["pending_message"],
                    created_at=current_time_iso(),
                )
                st.session_state.pending_hitl = None
                st.rerun()

        with col_reject:
            if st.button("❌ Reject Action", use_container_width=True):
                config = {"configurable": {"thread_id": st.session_state.chat_id}}
                try:
                    for chunk, _ in chat_graph.stream(
                        Command(resume="reject"),
                        config=config,
                        stream_mode="messages",
                    ):
                        pass
                except Exception:
                    pass

                db_save_message(
                    chat_id=st.session_state.chat_id,
                    role="assistant",
                    content="I've cancelled the requested action based on your review.",
                    created_at=current_time_iso(),
                )
                st.session_state.pending_hitl = None
                st.rerun()

    # Chat Input
    prompt = st.chat_input("Ask me anything...")

    if prompt:
        # Save user message to database
        db_save_message(
            chat_id=st.session_state.chat_id,
            role="user",
            content=prompt,
            created_at=current_time_iso(),
        )

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""
            config = {"configurable": {"thread_id": st.session_state.chat_id}}

            interrupted = False
            interrupt_payload = None

            try:
                for message_chunk, metadata in chat_graph.stream(
                    {"messages": [HumanMessage(content=prompt)]},
                    config=config,
                    stream_mode="messages",
                ):
                    # Check for LangGraph interrupt
                    if hasattr(message_chunk, "type") and message_chunk.type == "__interrupt__":
                        interrupted = True
                        interrupt_payload = message_chunk.value[0].value
                        break

                    if isinstance(message_chunk, AIMessageChunk) and isinstance(message_chunk.content, str):
                        full_response += message_chunk.content
                        response_placeholder.markdown(full_response + "▌")

                response_placeholder.markdown(full_response)

            except Exception as exc:
                exc_str = str(exc)
                if "interrupt" in exc_str.lower() or "GraphInterrupt" in type(exc).__name__:
                    interrupted = True
                    # Check state for interrupt value
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
                    st.error(f"Error during response generation: {exc}")

            if interrupted and interrupt_payload:
                pending_msg = interrupt_payload.get("pending_message", full_response)
                st.session_state.pending_hitl = {
                    "pending_message": pending_msg,
                }
                st.rerun()
            elif full_response:
                # Save assistant response to database
                db_save_message(
                    chat_id=st.session_state.chat_id,
                    role="assistant",
                    content=full_response,
                    created_at=current_time_iso(),
                )
                st.rerun()