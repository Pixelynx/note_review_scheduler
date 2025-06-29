"""Encryption module for secure credential storage using Fernet encryption."""

from __future__ import annotations

import os
import base64
import hashlib
import secrets
from pathlib import Path
from typing import Final

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from loguru import logger


class EncryptionError(Exception):
    """Base exception for encryption operations."""
    pass


class DecryptionError(EncryptionError):
    """Raised when decryption fails."""
    pass


class EncryptionManager:
    """Manages encryption and decryption of sensitive data using Fernet encryption.
    
    Uses PBKDF2 key derivation from a master password for secure key generation.
    """
    
    # Constants for key derivation
    PBKDF2_ITERATIONS: Final[int] = 100_000  # NIST recommended minimum
    SALT_LENGTH: Final[int] = 32  # 256 bits
    KEY_LENGTH: Final[int] = 32   # 256 bits for Fernet
    
    def __init__(self, master_password: str) -> None:
        """Initialize encryption manager with master password.
        
        Args:
            master_password: Master password for key derivation.
            
        Raises:
            ValueError: If master password is empty or too weak.
        """
        if not master_password or len(master_password.strip()) < 8:
            raise ValueError("Master password must be at least 8 characters long")
        
        self.master_password: str = master_password.strip()
        logger.debug("Encryption manager initialized")
    
    def _derive_key(self, salt: bytes) -> bytes:
        """Derive encryption key from master password using PBKDF2.
        
        Args:
            salt: Random salt for key derivation.
            
        Returns:
            Derived encryption key.
        """
        kdf: PBKDF2HMAC = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=self.KEY_LENGTH,
            salt=salt,
            iterations=self.PBKDF2_ITERATIONS,
        )
        
        password_bytes: bytes = self.master_password.encode('utf-8')
        key: bytes = kdf.derive(password_bytes)
        return key
    
    def generate_salt(self) -> bytes:
        """Generate a cryptographically secure random salt.
        
        Returns:
            Random salt bytes.
        """
        return secrets.token_bytes(self.SALT_LENGTH)
    
    def encrypt_data(self, data: str | bytes, salt: bytes | None = None) -> tuple[bytes, bytes]:
        """Encrypt data using Fernet encryption.
        
        Args:
            data: Data to encrypt (string or bytes).
            salt: Optional salt for key derivation. If None, generates new salt.
            
        Returns:
            Tuple of (encrypted_data, salt).
            
        Raises:
            EncryptionError: If encryption fails.
        """
        try:
            # Convert string to bytes if necessary
            if isinstance(data, str):
                data_bytes: bytes = data.encode('utf-8')
            else:
                data_bytes = data
            
            # Generate salt if not provided
            if salt is None:
                salt = self.generate_salt()
            
            # Derive key and create Fernet instance
            key: bytes = self._derive_key(salt)
            fernet: Fernet = Fernet(base64.urlsafe_b64encode(key))
            
            # Encrypt data
            encrypted_data: bytes = fernet.encrypt(data_bytes)
            
            logger.debug(f"Successfully encrypted {len(data_bytes)} bytes of data")
            return encrypted_data, salt
            
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise EncryptionError(f"Failed to encrypt data: {e}") from e
    
    def decrypt_data(self, encrypted_data: bytes, salt: bytes) -> bytes:
        """Decrypt data using Fernet encryption.
        
        Args:
            encrypted_data: Encrypted data bytes.
            salt: Salt used for key derivation.
            
        Returns:
            Decrypted data bytes.
            
        Raises:
            DecryptionError: If decryption fails.
        """
        try:
            # Derive key and create Fernet instance
            key: bytes = self._derive_key(salt)
            fernet: Fernet = Fernet(base64.urlsafe_b64encode(key))
            
            # Decrypt data
            decrypted_data: bytes = fernet.decrypt(encrypted_data)
            
            logger.debug(f"Successfully decrypted {len(decrypted_data)} bytes of data")
            return decrypted_data
            
        except InvalidToken as e:
            logger.error("Decryption failed: Invalid token (wrong password or corrupted data)")
            raise DecryptionError("Decryption failed: Invalid password or corrupted data") from e
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise DecryptionError(f"Failed to decrypt data: {e}") from e
    
    def decrypt_to_string(self, encrypted_data: bytes, salt: bytes) -> str:
        """Decrypt data and return as UTF-8 string.
        
        Args:
            encrypted_data: Encrypted data bytes.
            salt: Salt used for key derivation.
            
        Returns:
            Decrypted data as string.
            
        Raises:
            DecryptionError: If decryption fails.
        """
        try:
            decrypted_bytes: bytes = self.decrypt_data(encrypted_data, salt)
            return decrypted_bytes.decode('utf-8')
        except UnicodeDecodeError as e:
            logger.error(f"Failed to decode decrypted data as UTF-8: {e}")
            raise DecryptionError(f"Decrypted data is not valid UTF-8: {e}") from e
    
    def encrypt_file(self, file_path: Path, output_path: Path | None = None) -> Path:
        """Encrypt a file and save to disk.
        
        Args:
            file_path: Path to file to encrypt.
            output_path: Optional output path. If None, uses file_path + '.enc'.
            
        Returns:
            Path to encrypted file.
            
        Raises:
            EncryptionError: If file encryption fails.
        """
        try:
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Read file content
            file_content: bytes = file_path.read_bytes()
            
            # Encrypt content
            encrypted_data, salt = self.encrypt_data(file_content)
            
            # Determine output path
            if output_path is None:
                output_path = file_path.with_suffix(file_path.suffix + '.enc')
            
            # Write encrypted file (salt + encrypted_data)
            with open(output_path, 'wb') as f:
                f.write(salt)
                f.write(encrypted_data)
            
            logger.info(f"File encrypted successfully: {file_path} -> {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"File encryption failed: {e}")
            raise EncryptionError(f"Failed to encrypt file {file_path}: {e}") from e
    
    def decrypt_file(self, encrypted_file_path: Path, output_path: Path | None = None) -> Path:
        """Decrypt a file and save to disk.
        
        Args:
            encrypted_file_path: Path to encrypted file.
            output_path: Optional output path. If None, removes '.enc' extension.
            
        Returns:
            Path to decrypted file.
            
        Raises:
            DecryptionError: If file decryption fails.
        """
        try:
            if not encrypted_file_path.exists():
                raise FileNotFoundError(f"Encrypted file not found: {encrypted_file_path}")
            
            # Read encrypted file
            with open(encrypted_file_path, 'rb') as f:
                salt: bytes = f.read(self.SALT_LENGTH)
                encrypted_data: bytes = f.read()
            
            if len(salt) != self.SALT_LENGTH:
                raise ValueError(f"Invalid encrypted file format: expected {self.SALT_LENGTH} byte salt")
            
            # Decrypt content
            decrypted_data: bytes = self.decrypt_data(encrypted_data, salt)
            
            # Determine output path
            if output_path is None:
                if encrypted_file_path.suffix == '.enc':
                    output_path = encrypted_file_path.with_suffix('')
                else:
                    output_path = encrypted_file_path.with_suffix('.decrypted')
            
            # Write decrypted file
            output_path.write_bytes(decrypted_data)
            
            logger.info(f"File decrypted successfully: {encrypted_file_path} -> {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"File decryption failed: {e}")
            raise DecryptionError(f"Failed to decrypt file {encrypted_file_path}: {e}") from e
    
    def verify_password(self, test_data: str, encrypted_data: bytes, salt: bytes) -> bool:
        """Verify if the master password is correct by testing decryption.
        
        Args:
            test_data: Known plaintext data.
            encrypted_data: Encrypted version of test_data.
            salt: Salt used for encryption.
            
        Returns:
            True if password is correct, False otherwise.
        """
        try:
            decrypted: str = self.decrypt_to_string(encrypted_data, salt)
            return decrypted == test_data
        except DecryptionError:
            return False
    
    def create_password_test_data(self) -> tuple[bytes, bytes]:
        """Create test data for password verification.
        
        Returns:
            Tuple of (encrypted_test_data, salt).
        """
        test_string: str = "password_verification_test_" + secrets.token_hex(16)
        encrypted_data, salt = self.encrypt_data(test_string)
        return encrypted_data, salt
    
    @staticmethod
    def generate_strong_password(length: int = 16) -> str:
        """Generate a cryptographically secure random password.
        
        Args:
            length: Length of password to generate.
            
        Returns:
            Random password string.
        """
        if length < 8:
            raise ValueError("Password length must be at least 8 characters")
        
        # Use a mix of alphanumeric and special characters
        chars: str = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()-_=+[]{}|;:,.<>?"
        password: str = ''.join(secrets.choice(chars) for _ in range(length))
        
        logger.debug(f"Generated strong password of length {length}")
        return password
    
    @staticmethod
    def hash_password(password: str, salt: bytes | None = None) -> tuple[str, bytes]:
        """Hash a password using SHA-256 with salt.
        
        Args:
            password: Password to hash.
            salt: Optional salt. If None, generates new salt.
            
        Returns:
            Tuple of (hex_hash, salt).
        """
        if salt is None:
            salt = secrets.token_bytes(32)
        
        password_bytes: bytes = password.encode('utf-8')
        hash_obj = hashlib.sha256()
        hash_obj.update(salt)
        hash_obj.update(password_bytes)
        
        return hash_obj.hexdigest(), salt
    
    def secure_delete_file(self, file_path: Path) -> None:
        """Securely delete a file by overwriting it with random data.
        
        Args:
            file_path: Path to file to securely delete.
            
        Note:
            This provides basic secure deletion. For highly sensitive data,
            consider using specialized secure deletion tools.
        """
        try:
            if not file_path.exists():
                logger.warning(f"Cannot securely delete non-existent file: {file_path}")
                return
            
            file_size: int = file_path.stat().st_size
            
            # Overwrite with random data 3 times
            for i in range(3):
                with open(file_path, 'wb') as f:
                    f.write(os.urandom(file_size))
                    f.flush()
                    os.fsync(f.fileno())
                logger.debug(f"Secure delete pass {i+1}/3 completed for {file_path}")
            
            # Finally delete the file
            file_path.unlink()
            logger.info(f"File securely deleted: {file_path}")
            
        except Exception as e:
            logger.error(f"Secure file deletion failed: {e}")
            # Try regular deletion as fallback
            try:
                file_path.unlink()
                logger.warning(f"Fell back to regular deletion for {file_path}")
            except Exception:
                logger.error(f"Failed to delete file {file_path}")
                raise 