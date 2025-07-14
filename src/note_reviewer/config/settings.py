"""Centralized settings management for note review scheduler."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from loguru import logger

from ..security.credentials import CredentialManager, EmailCredentials, CredentialError


@dataclass(frozen=True)
class Settings:
    """Centralized application settings."""
    
    # Paths
    config_file: Path
    notes_directory: Path
    database_path: Path
    templates_directory: Optional[Path]
    
    # Email configuration
    email_credentials: EmailCredentials
    recipient_email: str
    attach_files: bool
    
    # Scheduling
    schedule_time: str
    notes_per_email: int
    email_template: str
    
    # Logging
    log_level: str
    log_file: Path
    
    @classmethod
    def from_credential_manager(
        cls,
        credential_manager: CredentialManager,
        templates_directory: Optional[Path] = None
    ) -> Settings:
        """Create Settings from CredentialManager.
        
        Args:
            credential_manager: Configured CredentialManager instance.
            templates_directory: Optional custom templates directory.
            
        Returns:
            Settings instance.
            
        Raises:
            CredentialError: If loading credentials fails.
        """
        try:
            email_credentials, app_config = credential_manager.load_credentials()
            
            return cls(
                config_file=credential_manager.config_file,
                notes_directory=Path(app_config.notes_directory),
                database_path=Path(app_config.database_path),
                templates_directory=templates_directory,
                email_credentials=email_credentials,
                recipient_email=app_config.recipient_email,
                attach_files=app_config.attach_files,
                schedule_time=app_config.schedule_time,
                notes_per_email=app_config.notes_per_email,
                email_template=app_config.email_template,
                log_level=app_config.log_level,
                log_file=Path(app_config.log_file)
            )
            
        except Exception as e:
            logger.error(f"Failed to create settings from credential manager: {e}")
            raise CredentialError(f"Failed to load settings: {e}") from e


def load_settings(
    config_file: Path,
    master_password: str,
    templates_directory: Optional[Path] = None
) -> Settings:
    """Load application settings from encrypted configuration.
    
    Args:
        config_file: Path to encrypted configuration file.
        master_password: Master password for decryption.
        templates_directory: Optional custom templates directory.
        
    Returns:
        Loaded Settings instance.
        
    Raises:
        CredentialError: If loading fails.
    """
    try:
        credential_manager: CredentialManager = CredentialManager(config_file, master_password)
        settings: Settings = Settings.from_credential_manager(credential_manager, templates_directory)
        
        logger.info(f"Settings loaded successfully from {config_file}")
        return settings
        
    except Exception as e:
        logger.error(f"Failed to load settings: {e}")
        raise CredentialError(f"Failed to load settings: {e}") from e 