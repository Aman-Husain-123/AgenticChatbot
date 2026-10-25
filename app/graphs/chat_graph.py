import sqlite3

from langchain_core.messages import AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import MessagesState
from langgraph.types import interrupt

from app.config import settings


if not settings.OPENAI_API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY is missing. "
        "Add it to your .env file."
    )


SYSTEM_PROMPT = """You are a helpful, thoughtful AI assistant.
Be concise, clear, and friendly. When asked to perform actions
that could have real-world side effects (like sending emails,
making purchases, or deleting data), always describe what you
would do and ask for confirmation before proceeding."""


# Create the model.
model = ChatOpenAI(
    model=settings.OPENAI_MODEL,
    api_key=settings.OPENAI_API_KEY,
    temperature=0.7,
    streaming=True,
)


def chatbot_node(state: MessagesState):
    """Main LLM node — generates a response."""
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = model.invoke(messages)
    return {"messages": [response]}


def human_review_node(state: MessagesState):
    """
    Human-in-the-Loop node.
    Interrupts the graph and waits for the user to approve or reject
    the last AI message before it is committed to the chat history.
    Returns the human's decision via interrupt().
    """
    last_message = state["messages"][-1]

    # Pause execution and surface the pending message to the UI.
    decision = interrupt(
        {
            "type": "human_review",
            "pending_message": last_message.content,
        }
    )

    if decision == "reject":
        # Replace the AI message with a rejection notice.
        return {
            "messages": [
                AIMessage(
                    content="I've withdrawn my previous response as requested. "
                    "Please let me know how I can help differently."
                )
            ]
        }

    # "approve" — keep the message as-is.
    return {}


def should_review(state: MessagesState) -> str:
    """
    Routing function: decides whether the Human Review node should run.
    Currently always routes to review; can be made conditional
    (e.g. only when the AI message contains certain keywords).
    """
    last = state["messages"][-1]
    if not isinstance(last, AIMessage):
        return END

    # Check if the message mentions potentially impactful actions.
    sensitive_keywords = [
        "send", "delete", "remove", "purchase", "buy",
        "submit", "confirm", "execute", "run", "deploy",
    ]
    content_lower = last.content.lower()
    needs_review = any(kw in content_lower for kw in sensitive_keywords)

    return "human_review" if needs_review else END


# ── Build the graph ───────────────────────────────────────────────
builder = StateGraph(MessagesState)

builder.add_node("chatbot", chatbot_node)
builder.add_node("human_review", human_review_node)

builder.add_edge(START, "chatbot")
builder.add_conditional_edges("chatbot", should_review)
builder.add_edge("human_review", END)


# ── Persistent SQLite checkpointer ───────────────────────────────
checkpoint_connection = sqlite3.connect(
    settings.CHECKPOINT_DATABASE_PATH,
    check_same_thread=False,
    timeout=30,
)

checkpointer = SqliteSaver(checkpoint_connection)
checkpointer.setup()

# ── Compile ───────────────────────────────────────────────────────
chat_graph = builder.compile(checkpointer=checkpointer)