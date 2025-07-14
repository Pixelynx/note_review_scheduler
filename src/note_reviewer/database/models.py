"""Database models for the note review scheduler."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Final


@dataclass(frozen=True)
class Note:
    """Model representing a note file.
    
    Immutable dataclass to prevent accidental mutation of database records.
    """
    id: int | None
    file_path: str
    content_hash: str
    file_size: int
    created_at: datetime
    modified_at: datetime


@dataclass(frozen=True)
class SendHistory:
    """Model representing email send history for notes.
    
    Immutable dataclass to prevent accidental mutation of database records.
    """
    id: int | None
    note_id: int
    sent_at: datetime
    email_subject: str
    notes_count_in_email: int


def create_tables_sql() -> tuple[str, str]:
    """Return SQL statements for creating the database tables.
    
    Returns:
        A tuple containing (notes_table_sql, send_history_table_sql).
    """
    notes_table_sql: Final[str] = """
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_path TEXT UNIQUE NOT NULL,
        content_hash TEXT NOT NULL,
        file_size INTEGER NOT NULL,
        created_at TIMESTAMP NOT NULL,
        modified_at TIMESTAMP NOT NULL
    )
    """
    
    send_history_table_sql: Final[str] = """
    CREATE TABLE IF NOT EXISTS send_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        note_id INTEGER NOT NULL,
        sent_at TIMESTAMP NOT NULL,
        email_subject TEXT NOT NULL,
        notes_count_in_email INTEGER NOT NULL,
        FOREIGN KEY (note_id) REFERENCES notes (id) ON DELETE CASCADE
    )
    """
    
    return notes_table_sql, send_history_table_sql 