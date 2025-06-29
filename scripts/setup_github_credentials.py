#!/usr/bin/env python3
"""
Setup credentials from GitHub secrets for automated execution.

This script reads credentials from environment variables (populated by GitHub secrets)
and creates the encrypted configuration files needed by the note review system.
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.note_reviewer.security.credentials import CredentialManager, EmailCredentials, AppConfig
from loguru import logger


def main() -> None:
    """Setup credentials from GitHub secrets."""
    
    # Get required environment variables
    master_password = os.getenv('MASTER_PASSWORD')
    email_address = os.getenv('EMAIL_ADDRESS') 
    email_app_password = os.getenv('EMAIL_APP_PASSWORD')
    notes_directory = os.getenv('NOTES_DIRECTORY', '/tmp/notes')
    
    if not all([master_password, email_address, email_app_password]):
        logger.error("Missing required environment variables")
        logger.error("Required: MASTER_PASSWORD, EMAIL_ADDRESS, EMAIL_APP_PASSWORD")
        sys.exit(1)
    
    logger.info("Setting up credentials from GitHub secrets")
    
    try:
        # Type assertions - we've already checked these are not None
        assert master_password is not None
        assert email_address is not None
        assert email_app_password is not None
        
        # Initialize credential manager
        config_file = Path("config/encrypted_config.json")
        credential_manager = CredentialManager(config_file, master_password)
        
        # Create email credentials
        email_creds = EmailCredentials(
            username=email_address,
            password=email_app_password,
            from_name=email_address.split('@')[0].title()  # Use first part of email as name
        )
        
        # Create app config
        app_config = AppConfig(
            notes_directory=notes_directory,
            recipient_email=email_address,
            schedule_time="09:00",  # Default to 9 AM
            notes_per_email=5
        )
        
        # Save credentials
        credential_manager.save_credentials(email_creds, app_config)
        
        logger.info("Credentials setup completed successfully")
        
        # Verify credentials can be loaded
        loaded_email, loaded_config = credential_manager.load_credentials()
        
        logger.info(f"Verified credentials for: {loaded_email.username}")
        logger.info(f"Notes directory: {loaded_config.notes_directory}")
        
    except Exception as e:
        logger.error(f"Failed to setup credentials: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 