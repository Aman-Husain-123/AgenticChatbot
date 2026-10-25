import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

    OPENAI_MODEL = os.getenv(
        "OPENAI_MODEL",
        "gpt-4.1-mini",
    )

    DATABASE_PATH = os.getenv(
        "DATABASE_PATH",
        "chatbot.db",
    )

    CHECKPOINT_DATABASE_PATH = os.getenv(
        "CHECKPOINT_DATABASE_PATH",
        "checkpoints.db",
    )

    LANGSMITH_TRACING = (
        os.getenv("LANGSMITH_TRACING", "false").lower()
        == "true"
    )

    LANGSMITH_API_KEY = os.getenv(
        "LANGSMITH_API_KEY",
        "",
    )

    LANGSMITH_PROJECT = os.getenv(
        "LANGSMITH_PROJECT",
        "ai-chatbot",
    )


settings = Settings()