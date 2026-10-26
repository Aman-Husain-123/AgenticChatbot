
import json

import requests
import streamlit as st


API_URL = "https://agenticchatbot-1.onrender.com"

st.set_page_config(
    page_title="Agentic Chatbot",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 Agentic Chatbot")

# Store the current chat ID in Streamlit session state.
if "chat_id" not in st.session_state:
    st.session_state.chat_id = None

if "messages" not in st.session_state:
    st.session_state.messages = []


def create_chat():
    response = requests.post(
        f"{API_URL}/chats",
        json={"title": "New Chat"},
        timeout=30,
    )
    response.raise_for_status()

    chat = response.json()

    st.session_state.chat_id = chat["id"]
    st.session_state.messages = []


def load_chats():
    response = requests.get(
        f"{API_URL}/chats",
        timeout=30,
    )
    response.raise_for_status()

    return response.json()["chats"]


def load_messages(chat_id):
    response = requests.get(
        f"{API_URL}/chats/{chat_id}",
        timeout=30,
    )
    response.raise_for_status()

    return response.json()["messages"]


with st.sidebar:
    st.header("Conversations")

    if st.button("➕ New Chat", use_container_width=True):
        try:
            create_chat()
            st.rerun()
        except requests.RequestException as exc:
            st.error(f"Could not create chat: {exc}")

    try:
        chats = load_chats()

        for chat in chats:
            if st.button(
                chat["title"],
                key=f"chat_{chat['id']}",
                use_container_width=True,
            ):
                try:
                    st.session_state.chat_id = chat["id"]
                    st.session_state.messages = load_messages(
                        chat["id"]
                    )
                    st.rerun()
                except requests.RequestException as exc:
                    st.error(f"Could not load chat: {exc}")

    except requests.RequestException:
        st.warning("Could not connect to the chatbot backend.")


if st.session_state.chat_id is None:
    st.info("Create a new chat from the sidebar to get started.")

else:
    for message in st.session_state.messages:
        role = (
            "assistant"
            if message["role"] == "assistant"
            else "user"
        )

        with st.chat_message(role):
            st.markdown(message["content"])

    prompt = st.chat_input("Ask me anything...")

    if prompt:
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""

            try:
                with requests.post(
                    (
                        f"{API_URL}/chats/"
                        f"{st.session_state.chat_id}/messages"
                    ),
                    json={"message": prompt},
                    stream=True,
                    timeout=(15, 300),
                ) as response:

                    response.raise_for_status()

                    for line in response.iter_lines(
                        decode_unicode=True
                    ):
                        if not line or not line.startswith("data:"):
                            continue

                        event = json.loads(
                            line[len("data:"):].strip()
                        )

                        if event["type"] == "token":
                            full_response += event["content"]

                            response_placeholder.markdown(
                                full_response + "▌"
                            )

                        elif event["type"] == "error":
                            st.error(event["message"])
                            break

                response_placeholder.markdown(full_response)

                # Reload authoritative history from the backend.
                st.session_state.messages = load_messages(
                    st.session_state.chat_id
                )

            except requests.RequestException as exc:
                st.error(f"Request failed: {exc}")
            except (ValueError, KeyError) as exc:
                st.error(f"Unexpected server response: {exc}")

# **Important:** This is a starter frontend. It assumes the backend's chat API is accessible and that your database is configured correctly. We will improve chat switching, message error handling, authentication, and production security later.

# ### Step 4: Push your changes

# Run:

# ```powershell
# git add .
# git commit -m "Add Streamlit chatbot frontend"
# git push
# ```

# ### Step 5: Create another Render service

# Open the [Render Dashboard](https://dashboard.render.com/?utm_source=chatgpt.com).

# 1. Click **New → Web Service**.
# 2. Select your existing GitHub repository.
# 3. Give the new service the name `agenticchatbot-ui`.
# 4. Use the same Python version as your backend.

# Configure:

# **Build Command**

# ```bash
# uv sync --locked
# ```

# **Start Command**

# ```bash
# uv run streamlit run frontend/streamlit_app.py --server.port $PORT --server.address 0.0.0.0
# ```

# 6. Deploy the service.

# Render will give you a separate URL for your Streamlit interface.

# You can then open that URL to use the graphical chatbot.

# ---

# ## 4. One important storage warning

# Your current backend stores chats in SQLite. If you haven't configured persistent storage, your conversation history may disappear after a redeployment or instance replacement.

# Also, if the backend is running on Render's free tier, it may spin down when inactive. Your first request after inactivity may take some time.

# Before you share this chatbot with other users, we should address persistent storage, authentication, and chat ownership.

# ### What I recommend next

# **First, open your backend's `/docs` endpoint and confirm that you can create a chat and receive a response. Then deploy the Streamlit frontend.**

# Once that works, we can add the sidebar conversation management, message editing, Human-in-the-Loop approval interface, and monitoring step by step.