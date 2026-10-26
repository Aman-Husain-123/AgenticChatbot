import json
import logging

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessageChunk, HumanMessage
from pydantic import BaseModel, Field

from app.database.connection import (
    create_chat,
    delete_chat,
    get_chat,
    get_messages,
    list_chats,
    save_message,
)
from app.graphs.chat_graph import chat_graph


router = APIRouter(prefix="/chats", tags=["Chats"])

logger = logging.getLogger(__name__)


def current_time():
    return datetime.now(timezone.utc).isoformat()


def encode_event(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


class CreateChatRequest(BaseModel):
    title: str = Field(
        default="New chat",
        min_length=1,
        max_length=200,
    )


class SendMessageRequest(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=20000,
    )


@router.post("")
def create_new_chat(request: CreateChatRequest):
    chat_id = str(uuid4())

    create_chat(
        chat_id=chat_id,
        title=request.title,
        created_at=current_time(),
    )

    return {
        "id": chat_id,
        "title": request.title,
    }


@router.get("")
def get_all_chats():
    return {
        "chats": list_chats()
    }


@router.get("/{chat_id}")
def get_single_chat(chat_id: str):
    chat = get_chat(chat_id)

    if chat is None:
        raise HTTPException(
            status_code=404,
            detail="Chat not found",
        )

    return {
        "chat": chat,
        "messages": get_messages(chat_id),
    }


@router.delete("/{chat_id}")
def remove_chat(chat_id: str):
    deleted = delete_chat(chat_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Chat not found",
        )

    return {
        "success": True,
        "message": "Chat deleted",
    }


@router.post("/{chat_id}/messages")
def send_message(
    chat_id: str,
    request: SendMessageRequest,
):
    chat = get_chat(chat_id)

    if chat is None:
        raise HTTPException(
            status_code=404,
            detail="Chat not found",
        )

    user_message = request.message.strip()

    if not user_message:
        raise HTTPException(
            status_code=422,
            detail="Message cannot be empty",
        )

    save_message(
        chat_id=chat_id,
        role="user",
        content=user_message,
        created_at=current_time(),
    )

    config = {
        "configurable": {
            "thread_id": chat_id,
        }
    }

    def event_generator():
        assistant_parts = []

        try:
            # Stream model message chunks from LangGraph.
            for message, metadata in chat_graph.stream(
                {
                    "messages": [
                        HumanMessage(content=user_message)
                    ]
                },
                config=config,
                stream_mode="messages",
            ):
                if not isinstance(message, AIMessageChunk):
                    continue

                if not isinstance(message.content, str):
                    continue

                if not message.content:
                    continue

                assistant_parts.append(message.content)

                yield encode_event({
                    "type": "token",
                    "content": message.content,
                })

            assistant_message = "".join(assistant_parts)

            if assistant_message:
                save_message(
                    chat_id=chat_id,
                    role="assistant",
                    content=assistant_message,
                    created_at=current_time(),
                )

            yield encode_event({
                "type": "done",
                "chat_id": chat_id,
            })

        except Exception:
            logger.exception(
                "Error generating response for chat %s",
                chat_id,
            )

            yield encode_event({
                "type": "error",
                "message": "An error occurred while generating the response.",
            })

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )