#!/usr/bin/env python3
"""Test script for Phase 2: Email System & Security functionality."""

from __future__ import annotations

import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

# Configure loguru for testing
logger.remove()  # Remove default handler
logger.add("test_email_system.log", level="DEBUG")
logger.add(lambda msg: print(msg, end=""), level="INFO")


def test_email_system_integration() -> None:
    """Test the integrated email system and security functionality."""
    logger.info("TEST: Starting Email System & Security integration test")
    
    try:
        # Import modules
        from src.note_reviewer.email import EmailService, EmailTemplateManager, TemplateContext
        from src.note_reviewer.security import EncryptionManager, CredentialManager
        from src.note_reviewer.security.credentials import EmailCredentials, AppConfig
        from src.note_reviewer.config import setup_logging, LoggingConfig
        from src.note_reviewer.database.models import Note
        
        # Test 1: Setup structured logging
        logger.info("\nTEST 1: Setting up structured logging")
        logging_config = LoggingConfig(
            log_file=Path("test_structured.log"),
            log_level="DEBUG",
            console_enabled=True,
            enable_performance_logging=True
        )
        structured_logger = setup_logging(logging_config)
        logger.info("SUCCESS: Structured logging initialized")
        
        # Test 2: Test encryption functionality
        logger.info("\nTEST 2: Testing encryption functionality")
        master_password = "test_master_password_123!"
        encryption_manager = EncryptionManager(master_password)
        
        # Test data encryption
        test_data = "This is sensitive credential data"
        encrypted_data, salt = encryption_manager.encrypt_data(test_data)
        decrypted_data = encryption_manager.decrypt_to_string(encrypted_data, salt)
        
        assert decrypted_data == test_data, "Encryption/decryption failed"
        logger.info("SUCCESS: Encryption/decryption working correctly")
        
        # Test 3: Create and save credentials
        logger.info("\nTEST 3: Testing credential management")
        
        # Create temporary config file
        with tempfile.NamedTemporaryFile(suffix='.enc', delete=False) as temp_file:
            config_file = Path(temp_file.name)
        
        try:
            # Create test credentials
            email_credentials = EmailCredentials(
                username="test@gmail.com",
                password="test_app_password",
                from_name="Test Scheduler"
            )
            
            app_config = AppConfig(
                notes_directory="/tmp/test_notes",
                recipient_email="recipient@example.com",
                notes_per_email=3
            )
            
            # Save credentials
            credential_manager = CredentialManager(config_file, master_password)
            credential_manager.save_credentials(email_credentials, app_config)
            
            # Load credentials back
            loaded_email_creds, loaded_app_config = credential_manager.load_credentials()
            
            assert loaded_email_creds.username == email_credentials.username
            assert loaded_app_config.notes_directory == app_config.notes_directory
            logger.info("SUCCESS: Credential storage and retrieval working")
            
        finally:
            # Clean up
            if config_file.exists():
                config_file.unlink()
        
        # Test 4: Create email service
        logger.info("\nTEST 4: Testing email service creation")
        email_config = EmailService.create_gmail_config(
            username="test@gmail.com",
            app_password="test_password",
            from_name="Test Note Scheduler",
            max_emails_per_hour=10
        )
        
        email_service = EmailService(email_config)
        
        # Test rate limiting
        rate_status = email_service.get_rate_limit_status()
        assert rate_status["max_emails_per_hour"] == 10
        assert rate_status["emails_sent_last_hour"] == 0
        logger.info("SUCCESS: Email service created with rate limiting")
        
        # Test 5: Test email templates
        logger.info("\nTEST 5: Testing email template system")
        
        # Create test notes
        test_notes = [
            Note(
                id=1,
                file_path="/tmp/note1.txt",
                content_hash="hash1",
                file_size=100,
                created_at=datetime.now(),
                modified_at=datetime.now()
            ),
            Note(
                id=2,
                file_path="/tmp/note2.md",
                content_hash="hash2", 
                file_size=200,
                created_at=datetime.now(),
                modified_at=datetime.now()
            )
        ]
        
        # Create test note files
        for note in test_notes:
            note_path = Path(note.file_path)
            note_path.parent.mkdir(parents=True, exist_ok=True)
            note_path.write_text(f"This is test content for {note_path.name}")
        
        try:
            # Create template context
            template_context = TemplateContext(
                notes=test_notes,
                recipient_email="test@example.com",
                total_notes_count=10,
                send_timestamp=datetime.now()
            )
            
            # Create template manager
            template_manager = EmailTemplateManager()
            
            # Render HTML template
            html_content = template_manager.render_email(
                "notes_review",
                template_context,
                "html"
            )
            
            # Render text template
            text_content = template_manager.render_email(
                "notes_review",
                template_context,
                "text"
            )
            
            assert "Note Review Scheduler" in html_content
            assert "Note Review Scheduler" in text_content
            assert "note1.txt" in html_content and "note1.txt" in text_content
            assert "note2.md" in html_content and "note2.md" in text_content
            
            logger.info("SUCCESS: Email templates rendered correctly")
            
            # Test 6: Test custom templates directory
            logger.info("\nTEST 6: Testing custom template creation")
            
            with tempfile.TemporaryDirectory() as temp_dir:
                template_dir = Path(temp_dir)
                template_manager.create_custom_template_files(template_dir)
                
                # Verify template files were created
                html_template = template_dir / "notes_review.html"
                text_template = template_dir / "notes_review.text"
                
                assert html_template.exists(), "HTML template file not created"
                assert text_template.exists(), "Text template file not created"
                
                # Test custom template manager
                custom_template_manager = EmailTemplateManager(template_dir)
                custom_html = custom_template_manager.render_email(
                    "notes_review",
                    template_context,
                    "html"
                )
                
                assert "Note Review Scheduler" in custom_html
                logger.info("SUCCESS: Custom templates working correctly")
            
            # Test 7: Test security logging
            logger.info("\nTEST 7: Testing structured logging features")
            
            # Test operation logging
            operation_id = structured_logger.log_operation_start(
                "email_send_test",
                recipient="test@example.com",
                notes_count=2
            )
            
            # Test performance metric
            structured_logger.log_performance_metric(
                "template_render_duration_seconds",
                0.5,
                "seconds",
                template_name="notes_review"
            )
            
            # Test email operation logging
            structured_logger.log_email_operation(
                "send",
                "test@example.com",
                True,
                notes_count=2
            )
            
            # Test security event logging
            structured_logger.log_security_event(
                "credential_access",
                True,
                "Configuration loaded successfully"
            )
            
            structured_logger.log_operation_end(
                operation_id,
                "email_send_test",
                success=True
            )
            
            logger.info("SUCCESS: Structured logging features working")
            
        finally:
            # Clean up test files
            for note in test_notes:
                note_path = Path(note.file_path)
                if note_path.exists():
                    note_path.unlink()
                # Clean up parent directory if empty
                try:
                    note_path.parent.rmdir()
                except OSError:
                    pass  # Directory not empty or doesn't exist
        
        # Test 8: Test error handling
        logger.info("\nTEST 8: Testing error handling")
        
        try:
            # Test invalid encryption
            EncryptionManager("short")
            assert False, "Should have raised ValueError for short password"
        except ValueError as e:
            logger.info(f"SUCCESS: Correctly caught weak password error: {e}")
        
        try:
            # Test invalid email credentials
            EmailCredentials(
                username="invalid_email",
                password="test",
                from_name="Test"
            )
            assert False, "Should have raised ValueError for invalid email"
        except ValueError as e:
            logger.info(f"SUCCESS: Correctly caught invalid email error: {e}")
        
        logger.info("\nSUCCESS: All Email System & Security tests passed!")
        logger.info("Phase 2 implementation is complete and functional!")
        
    except Exception as e:
        logger.error(f"FAILED: Email system test failed: {e}")
        raise


if __name__ == "__main__":
    test_email_system_integration() 