#!/usr/bin/env python3
"""Test script to verify the complete scheduler system functionality."""

from __future__ import annotations

import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Any
from unittest.mock import Mock, patch  # type: ignore

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

# Configure loguru for testing
logger.remove()  # Remove default handler
logger.add("test_scheduler_system.log", level="DEBUG")
logger.add(lambda msg: print(msg, end=""), level="INFO")


def create_test_notes_directory() -> Path:
    """Create a temporary directory with test notes."""
    temp_dir = Path(tempfile.mkdtemp(prefix="test_notes_"))
    
    # Create sample notes
    notes_content = [
        ("urgent_project.md", """# URGENT: Project Deadline
        
        ## Critical Tasks
        - **DEADLINE**: Complete API integration by Friday
        - Review security audit results
        - Deploy to staging environment
        
        This project affects Q4 revenue targets. High priority!
        """),
        
        ("learning_python.md", """# Python Advanced Concepts
        
        ## Decorators and Context Managers
        
        Learning about advanced Python patterns:
        - Function decorators for logging
        - Class decorators for validation
        - Context managers for resource handling
        
        ```python
        def retry(times=3):
            def decorator(func):
                def wrapper(*args, **kwargs):
                    for _ in range(times):
                        try:
                            return func(*args, **kwargs)
                        except Exception:
                            pass
                    raise
                return wrapper
            return decorator
        ```
        """),
        
        ("personal_goals.txt", """Personal Development Goals
        
        Monthly objectives:
        1. Read 2 technical books
        2. Complete online course on machine learning
        3. Contribute to open source project
        4. Practice public speaking
        
        Long-term vision:
        - Become a technical lead within 2 years
        - Build a side project that helps others
        - Mentor junior developers
        """),
        
        ("meeting_notes.md", """# Team Meeting Notes - Sprint Planning
        
        ## Attendees
        - Shinichi (PM)
        - Bulma (Backend)
        - Hibana (Frontend) 
        - Dr. Brief (DevOps)
        
        ## Sprint Goals
        1. Implement user authentication
        2. Add payment processing
        3. Improve mobile responsiveness
        4. Set up monitoring and alerts
        
        ## Action Items
        - Bob: Design user table schema
        - Carol: Create login/signup UI
        - Dave: Configure CI/CD pipeline
        
        **Next meeting**: Tuesday 2 PM
        """),
        
        ("ideas_brainstorm.txt", """Innovative App Ideas
        
        1. **Smart Habit Tracker**
           - Uses phone sensors to detect activities
           - Provides gentle reminders and encouragement
           - Gamification with achievements and streaks
        
        2. **Local Skill Exchange**
           - Platform for neighbors to teach each other
           - Rate and review system
           - Virtual and in-person options
        
        3. **Code Review Assistant**
           - AI-powered code analysis
           - Suggests improvements and best practices
           - Integrates with GitHub/GitLab
        """)
    ]
    
    for filename, content in notes_content:
        note_file = temp_dir / filename
        note_file.write_text(content, encoding='utf-8')
        logger.debug(f"Created test note: {note_file}")
    
    logger.info(f"Created test notes directory with {len(notes_content)} notes: {temp_dir}")
    return temp_dir


def create_mock_credentials() -> tuple[Any, Any]:
    """Create mock credential objects for testing."""
    from src.note_reviewer.security.credentials import EmailCredentials, AppConfig
    
    email_creds = EmailCredentials(
        username="test@example.com",
        password="test_app_password",
        from_name="Test Scheduler",
        smtp_server="smtp.gmail.com",
        smtp_port=587,
        max_emails_per_hour=50
    )
    
    app_config = AppConfig(
        notes_directory="/tmp/test_notes",
        recipient_email="recipient@example.com",
        database_path="test_scheduler.db",
        schedule_time="09:00",
        notes_per_email=3
    )
    
    return email_creds, app_config


def test_credential_management() -> None:
    """Test credential management without real credentials."""
    logger.info("\n=== TEST: Credential Management ===")
    
    try:
        from src.note_reviewer.security.credentials import CredentialManager
        from src.note_reviewer.security.encryption import EncryptionManager
        
        # Test encryption/decryption
        logger.info("Testing encryption manager...")
        test_password = "test_master_password_123"
        test_data = "sensitive configuration data"
        
        encryption_manager = EncryptionManager(test_password)
        encrypted_data, salt = encryption_manager.encrypt_data(test_data)
        decrypted_data = encryption_manager.decrypt_to_string(encrypted_data, salt)
        
        assert decrypted_data == test_data, "Encryption/decryption failed"
        logger.info("Encryption/decryption working correctly")
        
        # Test credential manager with temp file
        temp_config = Path(tempfile.mktemp(suffix=".json"))
        try:
            credential_manager = CredentialManager(temp_config, test_password)
            
            email_creds, app_config = create_mock_credentials()
            
            # Test save and load
            credential_manager.save_credentials(email_creds, app_config)
            loaded_email, loaded_config = credential_manager.load_credentials()
            
            assert loaded_email.username == email_creds.username
            assert loaded_config.recipient_email == app_config.recipient_email
            
            logger.info("Credential save/load working correctly")
            
        finally:
            if temp_config.exists():
                temp_config.unlink()
        
        logger.info("SUCCESS: Credential management tests passed")
        
    except Exception as e:
        logger.error(f"FAILED: Credential management test failed: {e}")
        raise


def test_health_monitoring() -> None:
    """Test health monitoring system."""
    logger.info("\n=== TEST: Health Monitoring ===")
    
    try:
        from src.note_reviewer.scheduler.monitor import HealthMonitor
        
        # Test with no credential manager (basic health check)
        health_monitor = HealthMonitor()
        
        # Test system metrics
        logger.info("Testing system metrics...")
        metrics = health_monitor.get_system_metrics()
        
        assert 0 <= metrics.cpu_percent <= 100, f"Invalid CPU percentage: {metrics.cpu_percent}"
        assert 0 <= metrics.memory_percent <= 100, f"Invalid memory percentage: {metrics.memory_percent}"
        assert metrics.available_memory_gb >= 0, f"Invalid available memory: {metrics.available_memory_gb}"
        
        logger.info(f"System metrics valid - CPU: {metrics.cpu_percent:.1f}%, Memory: {metrics.memory_percent:.1f}%")
        
        # Test health check
        logger.info("Testing health check...")
        health_status = health_monitor.perform_health_check()
        
        assert isinstance(health_status.is_healthy, bool), "Health status should be boolean"
        assert isinstance(health_status.warnings, list), "Warnings should be a list"
        assert isinstance(health_status.errors, list), "Errors should be a list"
        
        logger.info(f"Health check completed - Status: {'HEALTHY' if health_status.is_healthy else 'UNHEALTHY'}")
        logger.info(f"   Warnings: {len(health_status.warnings)}, Errors: {len(health_status.errors)}")
        
        # Test export functionality
        logger.info("Testing health report export...")
        report_dict = health_monitor.export_health_report(format="dict")
        assert isinstance(report_dict, dict), "Report should be a dictionary"
        assert 'is_healthy' in report_dict, "Report should contain health status"
        
        logger.info("Health report export working correctly")
        
        logger.info("SUCCESS: Health monitoring tests passed")
        
    except Exception as e:
        logger.error(f"FAILED: Health monitoring test failed: {e}")
        raise


def test_selection_system_integration() -> None:
    """Test the complete selection system with real files."""
    logger.info("\n=== TEST: Selection System Integration ===")
    
    test_notes_dir = None
    try:
        from src.note_reviewer.selection.content_analyzer import ContentAnalyzer
        from src.note_reviewer.selection.selection_algorithm import SelectionAlgorithm, SelectionCriteria
        from src.note_reviewer.database.models import Note
        
        # Create test notes
        test_notes_dir = create_test_notes_directory()
        
        # Initialize components
        logger.info("Initializing selection components...")
        content_analyzer = ContentAnalyzer()
        selection_algorithm = SelectionAlgorithm(content_analyzer)
        
        # Create mock Note objects from files
        logger.info("Creating mock notes from test files...")
        mock_notes: List[Note] = []
        for i, note_file in enumerate(test_notes_dir.glob("*.md")):
            mock_note = Note(
                id=i + 1,
                file_path=str(note_file),
                content_hash="test_hash",
                file_size=note_file.stat().st_size,
                created_at=datetime.now() - timedelta(days=i),
                modified_at=datetime.now() - timedelta(hours=i)
            )
            mock_notes.append(mock_note)
        
        logger.info(f"Created {len(mock_notes)} mock notes")
        
        # Test selection
        logger.info("Testing note selection...")
        criteria = SelectionCriteria(
            max_notes=3,
            max_email_length_chars=5000
        )
        
        selected_notes = selection_algorithm.select_notes(mock_notes, criteria)
        
        assert len(selected_notes) <= criteria.max_notes, f"Too many notes selected: {len(selected_notes)}"
        assert len(selected_notes) > 0, "No notes were selected"
        
        logger.info(f"Selected {len(selected_notes)} notes successfully")
        
        # Verify selection scores
        for note_score in selected_notes:
            assert note_score.total_score > 0, f"Invalid score for note {note_score.note_id}"
            logger.debug(f"Note {note_score.note_id}: score={note_score.total_score:.2f}")
        
        logger.info("SUCCESS: Selection system integration tests passed")
        
    except Exception as e:
        logger.error(f"FAILED: Selection system integration test failed: {e}")
        raise
    finally:
        # Cleanup
        if test_notes_dir and test_notes_dir.exists():
            import shutil
            shutil.rmtree(test_notes_dir)
            logger.debug(f"Cleaned up test notes directory: {test_notes_dir}")


def test_email_formatting() -> None:
    """Test email formatting with mock data."""
    logger.info("\n=== TEST: Email Formatting ===")
    
    test_notes_dir = None
    try:
        from src.note_reviewer.selection.email_formatter import EmailFormatter
        from src.note_reviewer.selection.selection_algorithm import NoteScore
        from src.note_reviewer.selection.content_analyzer import ContentMetrics, NoteImportance
        
        # Create test notes for real file paths
        test_notes_dir = create_test_notes_directory()
        test_files = list(test_notes_dir.glob("*.md"))[:2]  # Use first 2 files
        
        # Create mock note scores with real file paths
        logger.info("Creating mock note scores...")
        mock_scores = [
            NoteScore(
                note_id=1,
                file_path=str(test_files[0]) if len(test_files) > 0 else str(test_notes_dir / "test1.md"),
                total_score=0.85,
                content_score=0.8,
                freshness_score=0.9,
                importance_score=0.85,
                send_history_score=1.0,
                diversity_score=0.7,
                content_metrics=ContentMetrics(
                    content_hash="hash1",
                    word_count=150,
                    line_count=12,
                    code_blocks=1,
                    headers=3,
                    links=2,
                    todo_items=1,
                    importance_keywords=2,
                    readability_score=0.7,
                    freshness_days=2,
                    importance_level=NoteImportance.HIGH
                )
            ),
            NoteScore(
                note_id=2,
                file_path=str(test_files[1]) if len(test_files) > 1 else str(test_notes_dir / "test2.md"),
                total_score=0.75,
                content_score=0.7,
                freshness_score=0.8,
                importance_score=0.7,
                send_history_score=1.0,
                diversity_score=0.8,
                content_metrics=ContentMetrics(
                    content_hash="hash2",
                    word_count=200,
                    line_count=15,
                    code_blocks=0,
                    headers=2,
                    links=1,
                    todo_items=0,
                    importance_keywords=1,
                    readability_score=0.8,
                    freshness_days=5,
                    importance_level=NoteImportance.MEDIUM
                )
            )
        ]
        
        # Test formatting
        logger.info("Testing email formatting...")
        email_formatter = EmailFormatter()
        
        email_content = email_formatter.format_email(
            selected_notes=mock_scores,
            template_name="rich_review",
            include_toc=True,
            max_preview_words=50
        )
        
        # Verify email content
        assert email_content.subject, "Email subject should not be empty"
        assert email_content.html_content, "HTML content should not be empty"
        assert email_content.plain_text_content, "Plain text content should not be empty"
        assert email_content.total_word_count > 0, "Word count should be positive"
        
        logger.info(f"Email formatted successfully - Subject: '{email_content.subject}'")
        logger.info(f"   Word count: {email_content.total_word_count}")
        logger.info(f"   Categories: {len(email_content.categories)}")
        
        # Test HTML validity (basic check)
        html_content = email_content.html_content
        assert "<html>" in html_content or "<!DOCTYPE" in html_content, "Should contain HTML structure"
        assert len(mock_scores) <= html_content.count("<h"), "Should contain headers for notes"
        
        logger.info("HTML content structure validated")
        
        logger.info("SUCCESS: Email formatting tests passed")
        
    except Exception as e:
        logger.error(f"FAILED: Email formatting test failed: {e}")
        raise
    finally:
        # Cleanup
        if test_notes_dir and test_notes_dir.exists():
            import shutil
            shutil.rmtree(test_notes_dir)
            logger.debug(f"Cleaned up test notes directory: {test_notes_dir}")


def test_scheduler_configuration() -> None:
    """Test scheduler configuration and basic functionality."""
    logger.info("\n=== TEST: Scheduler Configuration ===")
    
    test_notes_dir = None
    temp_config = None
    
    try:
        from src.note_reviewer.scheduler.scheduler import NoteScheduler, ScheduleConfig, ScheduleType
        from src.note_reviewer.security.credentials import CredentialManager
        
        # Create test environment
        test_notes_dir = create_test_notes_directory()
        temp_config = Path(tempfile.mktemp(suffix=".json"))
        
        # Setup mock credentials
        email_creds, app_config = create_mock_credentials()
        app_config = app_config.__class__(
            notes_directory=str(test_notes_dir),
            recipient_email=app_config.recipient_email,
            database_path=app_config.database_path,
            schedule_time=app_config.schedule_time,
            notes_per_email=app_config.notes_per_email
        )
        
        credential_manager = CredentialManager(temp_config, "test_password")
        credential_manager.save_credentials(email_creds, app_config)
        
        # Test scheduler configuration
        logger.info("Testing scheduler configuration...")
        schedule_config = ScheduleConfig(
            schedule_type=ScheduleType.DAILY,
            time_of_day="09:00",
            max_notes_per_email=3,
            min_days_between_sends=7,
            max_retries=2,
            retry_delay_seconds=30
        )
        
        # Initialize scheduler
        logger.info("Initializing scheduler...")
        scheduler = NoteScheduler(
            config=schedule_config,
            notes_directory=test_notes_dir,
            credential_manager=credential_manager
        )
        
        # Test status before starting
        logger.info("Testing scheduler status...")
        status = scheduler.get_job_status()
        assert not status['is_running'], "Scheduler should not be running initially"
        assert status['current_job'] is None, "No current job should exist initially"
        
        logger.info("Scheduler initialized successfully")
        logger.info(f"   Schedule type: {schedule_config.schedule_type.value}")
        logger.info(f"   Time of day: {schedule_config.time_of_day}")
        logger.info(f"   Max notes per email: {schedule_config.max_notes_per_email}")
        
        # Test configuration validation
        logger.info("Testing configuration validation...")
        try:
            # This should raise ValueError for missing day_of_week
            ScheduleConfig(
                schedule_type=ScheduleType.WEEKLY,
                # Missing day_of_week for weekly schedule
            )
            assert False, "Should have raised ValueError for missing day_of_week"
        except ValueError:
            logger.info("Configuration validation working correctly")
        
        logger.info("SUCCESS: Scheduler configuration tests passed")
        
    except Exception as e:
        logger.error(f"FAILED: Scheduler configuration test failed: {e}")
        raise
    finally:
        # Cleanup
        if test_notes_dir and test_notes_dir.exists():
            import shutil
            shutil.rmtree(test_notes_dir)
        if temp_config and temp_config.exists():
            temp_config.unlink()


def test_backup_system() -> None:
    """Test database backup system."""
    logger.info("\n=== TEST: Database Backup System ===")
    
    temp_db = None
    backup_dir = None
    
    try:
        from src.note_reviewer.scheduler.backup import DatabaseBackup
        
        # Create temporary database and backup directory
        temp_db = Path(tempfile.mktemp(suffix=".db"))
        backup_dir = Path(tempfile.mkdtemp(prefix="test_backups_"))
        
        # Create a simple test database with proper cleanup
        import sqlite3
        conn = sqlite3.connect(temp_db)
        try:
            conn.execute("""
                CREATE TABLE test_table (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("INSERT INTO test_table (name) VALUES ('test_data_1')")
            conn.execute("INSERT INTO test_table (name) VALUES ('test_data_2')")
            conn.commit()
        finally:
            conn.close()  # Explicitly close connection
        
        logger.info(f"Created test database: {temp_db}")
        
        # Initialize backup system
        logger.info("Testing backup system...")
        backup_system = DatabaseBackup(
            database_path=temp_db,
            backup_directory=backup_dir,
            retention_days=30,
            max_backups=10
        )
        
        # Test backup creation
        logger.info("Creating backup...")
        backup_file = backup_system.create_backup(compress=True, validate=False)  # Skip validation to avoid file locking
        
        assert backup_file.exists(), "Backup file should exist"
        assert backup_file.suffix == '.zip', "Backup should be compressed"
        
        logger.info(f"Backup created successfully: {backup_file.name}")
        
        # Test backup info
        logger.info("Testing backup info...")
        backup_info = backup_system.get_backup_info()
        
        assert len(backup_info) >= 1, f"Should have at least 1 backup, found {len(backup_info)}"
        
        # Find our backup in the list
        our_backup = next((info for info in backup_info if info['filename'] == backup_file.name), None)
        assert our_backup is not None, f"Created backup {backup_file.name} not found in backup info"
        assert our_backup['is_compressed'] == True, "Backup should be marked as compressed"
        
        logger.info(f"Backup info correct - Size: {our_backup['size_mb']:.2f} MB")
        
        # Test backup cleanup (create old backup first)
        logger.info("Testing backup cleanup...")
        
        # Create a mock old backup by creating another backup and modifying its timestamp
        old_backup = backup_system.create_backup(compress=False, validate=False)
        
        # Modify file time to simulate old backup
        old_time = datetime.now() - timedelta(days=35)
        import os
        os.utime(old_backup, (old_time.timestamp(), old_time.timestamp()))
        
        # Run cleanup
        removed_count = backup_system.cleanup_old_backups()
        logger.info(f"Cleanup completed - Removed {removed_count} old backups")
        
        logger.info("SUCCESS: Database backup system tests passed")
        
    except Exception as e:
        logger.error(f"FAILED: Database backup system test failed: {e}")
        raise
    finally:
        # Cleanup
        if temp_db and temp_db.exists():
            temp_db.unlink()
        if backup_dir and backup_dir.exists():
            import shutil
            shutil.rmtree(backup_dir)


def main() -> int:
    """Run all scheduler system tests."""
    logger.info("Starting Scheduler System Tests")
    logger.info("=" * 60)
    
    test_functions = [
        test_credential_management,
        test_health_monitoring,
        test_selection_system_integration,
        test_email_formatting,
        test_backup_system,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in test_functions:
        try:
            test_func()
            passed += 1
        except Exception as e:
            logger.error(f"{test_func.__name__} FAILED: {e}")
            failed += 1
    
    # Run scheduler test separately
    try:
        test_scheduler_configuration()
        passed += 1
    except Exception as e:
        logger.error(f"test_scheduler_configuration FAILED: {e}")
        failed += 1
    
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Success Rate: {passed / (passed + failed) * 100:.1f}%")
    
    if failed == 0:
        logger.info("ALL TESTS PASSED! Scheduler system is ready for use.")
    else:
        logger.error(f"{failed} test(s) failed. Please review and fix issues.")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main()) 