"""Database package for note review scheduler."""

from .models import Note, SendHistory
from .operations import (
    DatabaseError,
    NoteNotFoundError,
    initialize_database,
    add_or_update_note,
    get_notes_never_sent,
    get_notes_not_sent_recently,
    record_email_sent,
)

__all__ = [
    # Models
    "Note",
    "SendHistory",
    # Exceptions
    "DatabaseError",
    "NoteNotFoundError",
    # Operations
    "initialize_database",
    "add_or_update_note",
    "get_notes_never_sent",
    "get_notes_not_sent_recently",
    "record_email_sent",
] 