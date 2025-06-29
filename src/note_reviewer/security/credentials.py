"""Credential management system for secure storage of email credentials."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from loguru import logger

from .encryption import EncryptionManager, DecryptionError


class CredentialError(Exception):
    """Base exception for credential operations."""
    pass


@dataclass(frozen=True)
class EmailCredentials:
    """Immutable email credentials dataclass."""
    username: str
    password: str  # App password for Gmail
    from_name: str
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    max_emails_per_hour: int = 50
    
    def __post_init__(self) -> None:
        """Validate credentials after initialization."""
        if not self.username.strip():
            raise ValueError("Username cannot be empty")
        if not self.password.strip():
            raise ValueError("Password cannot be empty")
        if "@" not in self.username:
            raise ValueError("Username must be a valid email address")
        if not (1 <= self.smtp_port <= 65535):
            raise ValueError("SMTP port must be between 1 and 65535")
        if self.max_emails_per_hour <= 0:
            raise ValueError("Max emails per hour must be positive")


@dataclass(frozen=True)
class AppConfig:
    """Application configuration including non-sensitive settings."""
    notes_directory: str
    recipient_email: str
    database_path: str = "notes_scheduler.db"
    schedule_time: str = "13:00"  # Daily at 1 PM
    notes_per_email: int = 3
    email_template: str = "notes_review"
    attach_files: bool = False
    log_level: str = "INFO"
    log_file: str = "note_scheduler.log"
    
    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if not self.notes_directory.strip():
            raise ValueError("Notes directory cannot be empty")
        if not self.recipient_email.strip():
            raise ValueError("Recipient email cannot be empty")
        if "@" not in self.recipient_email:
            raise ValueError("Recipient email must be a valid email address")
        if self.notes_per_email <= 0:
            raise ValueError("Notes per email must be positive")


class CredentialManager:
    """Manages secure storage and retrieval of credentials and configuration."""
    
    def __init__(self, config_file: Path, master_password: str) -> None:
        """Initialize credential manager.
        
        Args:
            config_file: Path to encrypted configuration file.
            master_password: Master password for encryption/decryption.
        """
        self.config_file: Path = config_file
        self.encryption_manager: EncryptionManager = EncryptionManager(master_password)
        self._cached_credentials: Optional[EmailCredentials] = None
        self._cached_config: Optional[AppConfig] = None
        
        logger.debug(f"Credential manager initialized with config file: {config_file}")
    
    def save_credentials(
        self,
        email_credentials: EmailCredentials,
        app_config: AppConfig
    ) -> None:
        """Save encrypted credentials and configuration to file.
        
        Args:
            email_credentials: Email credentials to save.
            app_config: Application configuration to save.
            
        Raises:
            CredentialError: If saving fails.
        """
        try:
            # Create configuration dictionary
            config_data: Dict[str, Any] = {
                'email_credentials': asdict(email_credentials),
                'app_config': asdict(app_config),
                'version': '1.0'
            }
            
            # Convert to JSON
            json_data: str = json.dumps(config_data, indent=2, sort_keys=True)
            
            # Encrypt the JSON data
            encrypted_data, salt = self.encryption_manager.encrypt_data(json_data)
            
            # Create config file structure: salt + encrypted_data
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'wb') as f:
                f.write(salt)
                f.write(encrypted_data)
            
            # Update cache
            self._cached_credentials = email_credentials
            self._cached_config = app_config
            
            logger.info(f"Credentials saved successfully to {self.config_file}")
            
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")
            raise CredentialError(f"Failed to save credentials: {e}") from e
    
    def load_credentials(self) -> tuple[EmailCredentials, AppConfig]:
        """Load and decrypt credentials and configuration from file.
        
        Returns:
            Tuple of (EmailCredentials, AppConfig).
            
        Raises:
            CredentialError: If loading fails.
        """
        try:
            # Return cached data if available
            if self._cached_credentials and self._cached_config:
                logger.debug("Returning cached credentials")
                return self._cached_credentials, self._cached_config
            
            if not self.config_file.exists():
                raise FileNotFoundError(f"Configuration file not found: {self.config_file}")
            
            # Read encrypted file
            with open(self.config_file, 'rb') as f:
                salt: bytes = f.read(self.encryption_manager.SALT_LENGTH)
                encrypted_data: bytes = f.read()
            
            if len(salt) != self.encryption_manager.SALT_LENGTH:
                raise ValueError("Invalid configuration file format")
            
            # Decrypt the data
            json_data: str = self.encryption_manager.decrypt_to_string(encrypted_data, salt)
            
            # Parse JSON
            config_data: Dict[str, Any] = json.loads(json_data)
            
            # Validate version
            version: str = config_data.get('version', '1.0')
            if version != '1.0':
                logger.warning(f"Unsupported configuration version: {version}")
            
            # Create credential objects
            email_creds_data: Dict[str, Any] = config_data['email_credentials']
            app_config_data: Dict[str, Any] = config_data['app_config']
            
            email_credentials: EmailCredentials = EmailCredentials(**email_creds_data)
            app_config: AppConfig = AppConfig(**app_config_data)
            
            # Cache the results
            self._cached_credentials = email_credentials
            self._cached_config = app_config
            
            logger.info("Credentials loaded successfully")
            return email_credentials, app_config
            
        except DecryptionError as e:
            logger.error("Failed to decrypt credentials (wrong password?)")
            raise CredentialError("Failed to decrypt credentials: Wrong password or corrupted file") from e
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error(f"Invalid configuration file format: {e}")
            raise CredentialError(f"Invalid configuration file format: {e}") from e
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
            raise CredentialError(f"Failed to load credentials: {e}") from e
    
    def update_email_credentials(self, email_credentials: EmailCredentials) -> None:
        """Update only the email credentials, keeping app config unchanged.
        
        Args:
            email_credentials: New email credentials.
            
        Raises:
            CredentialError: If update fails.
        """
        try:
            # Load current config
            _, current_app_config = self.load_credentials()
            
            # Save with new email credentials
            self.save_credentials(email_credentials, current_app_config)
            
            logger.info("Email credentials updated successfully")
            
        except Exception as e:
            logger.error(f"Failed to update email credentials: {e}")
            raise CredentialError(f"Failed to update email credentials: {e}") from e
    
    def update_app_config(self, app_config: AppConfig) -> None:
        """Update only the app configuration, keeping email credentials unchanged.
        
        Args:
            app_config: New application configuration.
            
        Raises:
            CredentialError: If update fails.
        """
        try:
            # Load current credentials
            current_email_creds, _ = self.load_credentials()
            
            # Save with new app config
            self.save_credentials(current_email_creds, app_config)
            
            logger.info("Application configuration updated successfully")
            
        except Exception as e:
            logger.error(f"Failed to update app configuration: {e}")
            raise CredentialError(f"Failed to update app configuration: {e}") from e
    
    def config_exists(self) -> bool:
        """Check if configuration file exists.
        
        Returns:
            True if configuration file exists, False otherwise.
        """
        return self.config_file.exists()
    
    def verify_master_password(self) -> bool:
        """Verify if the current master password is correct.
        
        Returns:
            True if password is correct, False otherwise.
        """
        try:
            # Try to load credentials - if successful, password is correct
            self.load_credentials()
            return True
        except CredentialError:
            return False
    
    def delete_config(self) -> None:
        """Securely delete the configuration file.
        
        Raises:
            CredentialError: If deletion fails.
        """
        try:
            if self.config_file.exists():
                self.encryption_manager.secure_delete_file(self.config_file)
                logger.info(f"Configuration file deleted: {self.config_file}")
            else:
                logger.warning(f"Configuration file does not exist: {self.config_file}")
            
            # Clear cache
            self._cached_credentials = None
            self._cached_config = None
            
        except Exception as e:
            logger.error(f"Failed to delete configuration file: {e}")
            raise CredentialError(f"Failed to delete configuration file: {e}") from e
    
    def export_config_backup(self, backup_path: Path, include_credentials: bool = False) -> None:
        """Export configuration backup (optionally without sensitive credentials).
        
        Args:
            backup_path: Path to save backup file.
            include_credentials: Whether to include email credentials in backup.
            
        Raises:
            CredentialError: If export fails.
        """
        try:
            email_credentials, app_config = self.load_credentials()
            
            # Create backup data
            backup_data: Dict[str, Any] = {
                'app_config': asdict(app_config),
                'version': '1.0',
                'backup_created': datetime.now().isoformat()
            }
            
            if include_credentials:
                backup_data['email_credentials'] = asdict(email_credentials)
                backup_data['includes_credentials'] = True
            else:
                backup_data['includes_credentials'] = False
            
            # Save as JSON (not encrypted)
            json_data: str = json.dumps(backup_data, indent=2, sort_keys=True)
            backup_path.write_text(json_data, encoding='utf-8')
            
            logger.info(f"Configuration backup exported to {backup_path}")
            
        except Exception as e:
            logger.error(f"Failed to export configuration backup: {e}")
            raise CredentialError(f"Failed to export configuration backup: {e}") from e
    
    @classmethod
    def setup_wizard(
        cls,
        config_file: Path,
        master_password: str,
        gmail_username: str,
        gmail_app_password: str,
        recipient_email: str,
        notes_directory: str,
        from_name: str = ""
    ) -> CredentialManager:
        """Setup wizard for initial credential configuration.
        
        Args:
            config_file: Path where config file will be saved.
            master_password: Master password for encryption.
            gmail_username: Gmail username (email address).
            gmail_app_password: Gmail app password.
            recipient_email: Email address to send notes to.
            notes_directory: Directory containing note files.
            from_name: Display name for sender.
            
        Returns:
            Configured CredentialManager instance.
            
        Raises:
            CredentialError: If setup fails.
        """
        try:
            logger.info("Starting credential setup wizard")
            
            # Create email credentials
            email_credentials: EmailCredentials = EmailCredentials(
                username=gmail_username,
                password=gmail_app_password,
                from_name=from_name or gmail_username.split('@')[0]
            )
            
            # Create app configuration
            app_config: AppConfig = AppConfig(
                notes_directory=notes_directory,
                recipient_email=recipient_email
            )
            
            # Create credential manager and save
            manager: CredentialManager = cls(config_file, master_password)
            manager.save_credentials(email_credentials, app_config)
            
            logger.info("Credential setup completed successfully")
            return manager
            
        except Exception as e:
            logger.error(f"Credential setup failed: {e}")
            raise CredentialError(f"Credential setup failed: {e}") from e 