"""Database operations for the note review scheduler."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Final, Generator

from loguru import logger

from .models import Note, create_tables_sql


DATABASE_PATH: Final[Path] = Path("notes_scheduler.db")


class DatabaseError(Exception):
    """Base exception for database operations."""
    pass


class NoteNotFoundError(DatabaseError):
    """Raised when a note cannot be found."""
    pass


@contextmanager
def get_db_connection(db_path: Path = DATABASE_PATH) -> Generator[sqlite3.Connection, None, None]:
    """Context manager for database connections with proper cleanup.
    
    Args:
        db_path: Path to the SQLite database file.
        
    Yields:
        A configured SQLite connection with row factory enabled.
        
    Raises:
        DatabaseError: If database connection or operations fail.
    """
    db_connection: sqlite3.Connection | None = None
    try:
        db_connection = sqlite3.connect(str(db_path))
        db_connection.row_factory = sqlite3.Row  # Enable dict-like access
        logger.debug(f"Database connection established to {db_path}")
        yield db_connection
    except sqlite3.Error as e:
        logger.error(f"Database error occurred: {e}")
        if db_connection is not None:
            db_connection.rollback()
        raise DatabaseError(f"Database operation failed: {e}") from e
    except Exception as e:
        logger.error(f"Unexpected error with database connection: {e}")
        if db_connection is not None:
            db_connection.rollback()
        raise DatabaseError(f"Unexpected database error: {e}") from e
    finally:
        if db_connection is not None:
            db_connection.close()
            logger.debug("Database connection closed")


def initialize_database(db_path: Path = DATABASE_PATH) -> None:
    """Create database tables if they don't exist.
    
    Args:
        db_path: Path to the SQLite database file.
        
    Raises:
        DatabaseError: If table creation fails.
    """
    try:
        with get_db_connection(db_path) as db_connection:
            notes_sql: str
            send_history_sql: str
            notes_sql, send_history_sql = create_tables_sql()
            
            db_connection.execute(notes_sql)
            db_connection.execute(send_history_sql)
            db_connection.commit()
            
            logger.info("Database tables initialized successfully")
            
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise DatabaseError(f"Database initialization failed: {e}") from e


def add_or_update_note(
    file_path: Path,
    content_hash: str,
    file_size: int,
    created_at: datetime,
    modified_at: datetime,
    db_path: Path = DATABASE_PATH
) -> int:
    """Upsert a note record based on file_path.
    
    Args:
        file_path: Path to the note file.
        content_hash: SHA-256 hash of file content.
        file_size: Size of the file in bytes.
        created_at: When the file was created.
        modified_at: When the file was last modified.
        db_path: Path to the SQLite database file.
        
    Returns:
        The database ID of the inserted or updated note.
        
    Raises:
        DatabaseError: If the database operation fails.
    """
    try:
        with get_db_connection(db_path) as db_connection:
            # Check if note exists
            existing_note: sqlite3.Row | None = db_connection.execute(
                "SELECT id FROM notes WHERE file_path = ?",
                (str(file_path),)
            ).fetchone()
            
            note_id: int
            if existing_note is not None:
                # Update existing note
                note_id = int(existing_note["id"])
                db_connection.execute(
                    """UPDATE notes 
                       SET content_hash = ?, file_size = ?, modified_at = ?
                       WHERE id = ?""",
                    (content_hash, file_size, modified_at.isoformat(), note_id)
                )
                logger.debug(f"Updated existing note: {file_path}")
            else:
                # Insert new note
                cursor: sqlite3.Cursor = db_connection.execute(
                    """INSERT INTO notes (file_path, content_hash, file_size, created_at, modified_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (str(file_path), content_hash, file_size, created_at.isoformat(), modified_at.isoformat())
                )
                last_row_id: int | None = cursor.lastrowid
                if last_row_id is None:
                    raise DatabaseError("Failed to get last row ID after insert")
                note_id = last_row_id
                logger.debug(f"Added new note: {file_path}")
            
            db_connection.commit()
            logger.info(f"Note processed successfully: {file_path} (ID: {note_id})")
            return note_id
            
    except Exception as e:
        logger.error(f"Failed to add/update note {file_path}: {e}")
        raise DatabaseError(f"Failed to add/update note {file_path}: {e}") from e


def get_notes_never_sent(db_path: Path = DATABASE_PATH, limit: int | None = None) -> list[Note]:
    """Return notes that have never been sent via email.
    
    Args:
        db_path: Path to the SQLite database file.
        limit: Maximum number of notes to return. If None, returns all notes.
               Useful for processing notes in batches to avoid overwhelming emails.
        
    Returns:
        List of Note objects that have never been sent, ordered by creation date.
        When limit is specified, returns at most 'limit' notes.
        
    Raises:
        DatabaseError: If the database query fails.
        ValueError: If limit is not a positive integer when provided.
        
    Examples:
        >>> # Get all notes never sent
        >>> notes = get_notes_never_sent()
        
        >>> # Get up to 5 notes for batch processing
        >>> notes = get_notes_never_sent(limit=5)
        
        >>> # Custom database path with limit
        >>> notes = get_notes_never_sent(Path("custom.db"), limit=10)
    """
    # Parameter validation
    if limit is not None and limit <= 0:
        raise ValueError("Limit must be positive when provided")
    
    try:
        with get_db_connection(db_path) as db_connection:
            base_query: str = """SELECT n.* FROM notes n
                                LEFT JOIN send_history sh ON n.id = sh.note_id
                                WHERE sh.note_id IS NULL
                                ORDER BY n.created_at ASC"""
            
            rows: list[sqlite3.Row]
            if limit is not None:
                rows = db_connection.execute(base_query + " LIMIT ?", (limit,)).fetchall()
            else:
                rows = db_connection.execute(base_query).fetchall()
            
            notes: list[Note] = [
                Note(
                    id=int(row["id"]),
                    file_path=str(row["file_path"]),
                    content_hash=str(row["content_hash"]),
                    file_size=int(row["file_size"]),
                    created_at=datetime.fromisoformat(str(row["created_at"])),
                    modified_at=datetime.fromisoformat(str(row["modified_at"]))
                )
                for row in rows
            ]
            
            if limit is not None:
                logger.info(f"Found {len(notes)} notes never sent (limited to {limit} results)")
            else:
                logger.info(f"Found {len(notes)} notes never sent")
            return notes
            
    except Exception as e:
        logger.error(f"Failed to get notes never sent: {e}")
        raise DatabaseError(f"Failed to get notes never sent: {e}") from e


def get_notes_not_sent_recently(days: int, db_path: Path = DATABASE_PATH) -> list[Note]:
    """Return notes that haven't been sent in the specified number of days.
    
    Args:
        days: Number of days to look back for recent sends.
        db_path: Path to the SQLite database file.
        
    Returns:
        List of Note objects not sent recently, ordered by creation date.
        
    Raises:
        DatabaseError: If the database query fails.
        ValueError: If days is negative.
    """
    if days < 0:
        raise ValueError("Days must be non-negative")
        
    try:
        cutoff_date: datetime = datetime.now() - timedelta(days=days)
        
        with get_db_connection(db_path) as db_connection:
            rows: list[sqlite3.Row] = db_connection.execute(
                """SELECT n.* FROM notes n
                   LEFT JOIN (
                       SELECT note_id, MAX(sent_at) as last_sent
                       FROM send_history
                       GROUP BY note_id
                   ) sh ON n.id = sh.note_id
                   WHERE sh.last_sent IS NULL OR sh.last_sent < ?
                   ORDER BY n.created_at ASC""",
                (cutoff_date.isoformat(),)
            ).fetchall()
            
            notes: list[Note] = [
                Note(
                    id=int(row["id"]),
                    file_path=str(row["file_path"]),
                    content_hash=str(row["content_hash"]),
                    file_size=int(row["file_size"]),
                    created_at=datetime.fromisoformat(str(row["created_at"])),
                    modified_at=datetime.fromisoformat(str(row["modified_at"]))
                )
                for row in rows
            ]
            
            logger.info(f"Found {len(notes)} notes not sent in last {days} days")
            return notes
            
    except Exception as e:
        logger.error(f"Failed to get notes not sent recently: {e}")
        raise DatabaseError(f"Failed to get notes not sent recently: {e}") from e


def record_email_sent(
    note_id: int,
    sent_at: datetime,
    email_subject: str,
    notes_count_in_email: int,
    db_path: Path = DATABASE_PATH
) -> int:
    """Record that an email was sent containing the specified note.
    
    Args:
        note_id: Database ID of the note that was sent.
        sent_at: When the email was sent.
        email_subject: Subject line of the email.
        notes_count_in_email: Total number of notes included in the email.
        db_path: Path to the SQLite database file.
        
    Returns:
        The database ID of the send history record.
        
    Raises:
        DatabaseError: If the database operation fails.
        ValueError: If note_id or notes_count_in_email is invalid.
    """
    if note_id <= 0:
        raise ValueError("Note ID must be positive")
    if notes_count_in_email <= 0:
        raise ValueError("Notes count in email must be positive")
    if not email_subject.strip():
        raise ValueError("Email subject cannot be empty")
        
    try:
        with get_db_connection(db_path) as db_connection:
            cursor: sqlite3.Cursor = db_connection.execute(
                """INSERT INTO send_history (note_id, sent_at, email_subject, notes_count_in_email)
                   VALUES (?, ?, ?, ?)""",
                (note_id, sent_at.isoformat(), email_subject, notes_count_in_email)
            )
            last_row_id: int | None = cursor.lastrowid
            if last_row_id is None:
                raise DatabaseError("Failed to get last row ID after insert")
            send_history_id: int = last_row_id
            db_connection.commit()
            
            logger.info(f"Recorded email send for note ID {note_id} (Send ID: {send_history_id})")
            return send_history_id
            
    except Exception as e:
        logger.error(f"Failed to record email sent for note ID {note_id}: {e}")
        raise DatabaseError(f"Failed to record email sent for note ID {note_id}: {e}") from e 