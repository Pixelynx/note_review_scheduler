## Changelog

### [Unreleased]

### [2025-22-06]
#### Added
- **Database Foundation**: Created SQLite database schema and operations
  - `src/note_reviewer/database/models.py`: Defined `notes` and `send_history` table schemas with proper data models
  - `src/note_reviewer/database/operations.py`: Implemented core database operations with context managers and error handling
    - `initialize_database()`: Creates tables if they don't exist
    - `add_or_update_note()`: Upserts note records based on file_path
    - `get_notes_never_sent()`: Returns notes with no send history
    - `get_notes_not_sent_recently(days)`: Returns notes not sent in X days
    - `record_email_sent()`: Adds send history records
  - `src/note_reviewer/database/__init__.py`: Clean package imports
  - All functions use modern Python practices with type hints, pathlib, and loguru logging
  - **Strict Typing Compliance**: Enhanced all database code to meet strict typing guidelines
    - Complete type annotations with modern union syntax (`int | None` vs `Optional[int]`)
    - Explicit variable type declarations for all assignments
    - Custom typed exceptions (`DatabaseError`, `NoteNotFoundError`)
    - Immutable frozen dataclasses to prevent accidental mutations
    - Input validation with proper error messages
    - Zero implicit `Any` types - complete type coverage
    - `Final` constants and proper generic usage