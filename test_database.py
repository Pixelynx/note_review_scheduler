#!/usr/bin/env python3
"""Test script to verify database operations work correctly."""

from __future__ import annotations

import hashlib
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from loguru import logger

# Configure loguru for testing
logger.remove()  # Remove default handler
logger.add("test_database.log", level="DEBUG")
logger.add(lambda msg: print(msg, end=""), level="INFO")


def create_test_note_file(content: str) -> Path:
    """Create a temporary note file with given content.
    
    Args:
        content: The text content for the note file.
        
    Returns:
        Path to the created temporary note file.
    """
    temp_file: Path = Path(tempfile.mktemp(suffix=".txt"))
    temp_file.write_text(content, encoding="utf-8")
    return temp_file


def calculate_content_hash(file_path: Path) -> str:
    """Calculate SHA-256 hash of file content.
    
    Args:
        file_path: Path to the file to hash.
        
    Returns:
        Hexadecimal SHA-256 hash of the file content.
    """
    content: str = file_path.read_text(encoding="utf-8")
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def test_database_operations() -> None:
    """Test all database operations with comprehensive validation."""
    # Use a test database
    test_db_path: Path = Path("test_notes_scheduler.db")
    
    # Clean up any existing test database
    if test_db_path.exists():
        test_db_path.unlink()
    
    note_files: list[Path] = []
    
    try:
        # Import after setting up logging
        from src.note_reviewer.database.operations import (
            initialize_database,
            add_or_update_note,
            get_notes_never_sent,
            get_notes_not_sent_recently,
            record_email_sent,
        )
        from src.note_reviewer.database.models import Note
        
        logger.info("TEST: Starting database operations test")
        
        # Test 1: Initialize database
        logger.info("\nTEST 1: Initializing database")
        initialize_database(test_db_path)
        assert test_db_path.exists(), "Database file should be created"
        logger.info("SUCCESS: Database initialized successfully")
        
        # Test 2: Create test note files
        logger.info("\nTEST 2: Creating test note files")
        for i in range(3):
            content: str = f"This is test note {i+1}\nContent for testing purposes."
            note_file: Path = create_test_note_file(content)
            note_files.append(note_file)
            logger.info(f"Created test file: {note_file}")
        
        # Test 3: Add notes to database
        logger.info("\nTEST 3: Adding notes to database")
        note_ids: list[int] = []
        for note_file in note_files:
            content_hash: str = calculate_content_hash(note_file)
            file_size: int = note_file.stat().st_size
            created_at: datetime = datetime.now()
            modified_at: datetime = created_at
            
            note_id: int = add_or_update_note(
                note_file, content_hash, file_size, created_at, modified_at, test_db_path
            )
            note_ids.append(note_id)
            logger.info(f"Added note ID {note_id} for {note_file.name}")
        
        # Test 4: Update an existing note
        logger.info("\nTEST 4: Updating existing note")
        updated_content: str = "This is updated content for test note 1"
        note_files[0].write_text(updated_content, encoding="utf-8")
        updated_hash: str = calculate_content_hash(note_files[0])
        updated_size: int = note_files[0].stat().st_size
        
        updated_id: int = add_or_update_note(
            note_files[0], updated_hash, updated_size, 
            datetime.now(), datetime.now(), test_db_path
        )
        assert updated_id == note_ids[0], "Should return same ID for existing note"
        logger.info(f"SUCCESS: Updated note ID {updated_id}")
        
        # Test 5: Record email sent for first note
        logger.info("\nTEST 5: Recording email send")
        send_timestamp: datetime = datetime.now()
        send_id: int = record_email_sent(
            note_ids[0], send_timestamp, "Test Email Subject", 1, test_db_path
        )
        logger.info(f"SUCCESS: Recorded email send ID {send_id}")
        
        # Test 6: Get notes never sent (should be 2 now)
        logger.info("\nTEST 6: Getting notes never sent (after email)")
        never_sent_after: list[Note] = get_notes_never_sent(test_db_path)
        assert len(never_sent_after) == 2, f"Expected 2 notes, got {len(never_sent_after)}"
        logger.info(f"SUCCESS: Found {len(never_sent_after)} notes never sent")
        
        # Test 7: Get notes not sent recently
        logger.info("\nTEST 7: Getting notes not sent recently")
        not_sent_recently: list[Note] = get_notes_not_sent_recently(1, test_db_path)  # 1 day
        assert len(not_sent_recently) == 2, f"Expected 2 notes, got {len(not_sent_recently)}"
        logger.info(f"SUCCESS: Found {len(not_sent_recently)} notes not sent in last 1 day")
        
        # Test 8: Test with older send date
        logger.info("\nTEST 8: Testing with older send date")
        old_timestamp: datetime = datetime.now() - timedelta(days=2)
        old_send_id: int = record_email_sent(
            note_ids[1], old_timestamp, "Old Email Subject", 1, test_db_path
        )
        logger.info(f"SUCCESS: Recorded past email send ID {old_send_id}")
        
        not_sent_recently_1day: list[Note] = get_notes_not_sent_recently(1, test_db_path)
        assert len(not_sent_recently_1day) == 2, f"Expected 2 notes, got {len(not_sent_recently_1day)}"
        logger.info(f"SUCCESS: Found {len(not_sent_recently_1day)} notes not sent in last 1 day (after old send)")
        
        logger.info("\nSUCCESS: All database tests passed successfully!")
        
    except Exception as e:
        logger.error(f"FAILED: Test failed: {e}")
        raise
    finally:
        # Clean up test files
        logger.info("\nCLEANUP: Cleaning up test files")
        for note_file in note_files:
            if note_file.exists():
                note_file.unlink()
                logger.debug(f"Deleted test file: {note_file}")
        
        # Optionally clean up test database (comment out to inspect)
        if test_db_path.exists():
            test_db_path.unlink()
            logger.info("CLEANUP: Test database cleaned up")


if __name__ == "__main__":
    test_database_operations() 