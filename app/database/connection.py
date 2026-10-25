import sqlite3
from contextlib import contextmanager

from app.config import settings


@contextmanager
def get_db():
    """
    Create a database connection for one operation
    and close it when the operation finishes.
    """
    connection = sqlite3.connect(
        settings.DATABASE_PATH,
        timeout=30,
    )

    connection.row_factory = sqlite3.Row

    try:
        connection.execute("PRAGMA foreign_keys = ON")

        yield connection

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def initialize_database():
    """
    Create the application tables if they do not exist.
    """

    with get_db() as connection:

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS chats (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,

                FOREIGN KEY (chat_id)
                    REFERENCES chats(id)
                    ON DELETE CASCADE
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_messages_chat_id
            ON messages(chat_id)
            """
        )


def create_chat(chat_id: str, title: str, created_at: str):
    with get_db() as connection:
        connection.execute(
            """
            INSERT INTO chats (id, title, created_at)
            VALUES (?, ?, ?)
            """,
            (chat_id, title, created_at),
        )


def list_chats():
    with get_db() as connection:
        rows = connection.execute(
            """
            SELECT id, title, created_at
            FROM chats
            ORDER BY created_at DESC
            """
        ).fetchall()

        return [dict(row) for row in rows]


def get_chat(chat_id: str):
    with get_db() as connection:
        row = connection.execute(
            """
            SELECT id, title, created_at
            FROM chats
            WHERE id = ?
            """,
            (chat_id,),
        ).fetchone()

        return dict(row) if row else None


def save_message(
    chat_id: str,
    role: str,
    content: str,
    created_at: str,
):
    with get_db() as connection:
        connection.execute(
            """
            INSERT INTO messages (
                chat_id,
                role,
                content,
                created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (chat_id, role, content, created_at),
        )


def get_messages(chat_id: str):
    with get_db() as connection:
        rows = connection.execute(
            """
            SELECT id, chat_id, role, content, created_at
            FROM messages
            WHERE chat_id = ?
            ORDER BY id ASC
            """,
            (chat_id,),
        ).fetchall()

        return [dict(row) for row in rows]


def update_chat_title(chat_id: str, title: str):
    with get_db() as connection:
        connection.execute(
            """
            UPDATE chats
            SET title = ?
            WHERE id = ?
            """,
            (title, chat_id),
        )


def delete_chat(chat_id: str):
    with get_db() as connection:
        cursor = connection.execute(
            """
            DELETE FROM chats
            WHERE id = ?
            """,
            (chat_id,),
        )

        return cursor.rowcount > 0