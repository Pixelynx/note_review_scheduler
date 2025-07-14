"""
Automated Database Backup System

Provides reliable database backup with retention policies, validation,
and integration with cloud storage or artifact systems.
"""

from __future__ import annotations

import hashlib
import shutil
import sqlite3
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from ..config.logging_config import StructuredLogger, LoggingConfig


class DatabaseBackup:
    """
    Automated database backup system with retention and validation.
    
    Features:
    - Automated scheduled backups
    - Configurable retention policies
    - Backup integrity validation
    - Compression and encryption support
    - Integration with artifact storage
    """
    
    def __init__(
        self,
        database_path: Path = Path("data/notes_tracker.db"),
        backup_directory: Path = Path("data/backups"),
        retention_days: int = 30,
        max_backups: int = 100
    ) -> None:
        """
        Initialize backup system.
        
        Args:
            database_path: Path to source database.
            backup_directory: Directory for backup storage.
            retention_days: Days to retain backups.
            max_backups: Maximum number of backups to keep.
        """
        self.database_path = Path(database_path)
        self.backup_directory = Path(backup_directory)
        self.retention_days = retention_days
        self.max_backups = max_backups
        
        # Initialize structured logger with default config
        try:
            config = LoggingConfig()
            self.structured_logger = StructuredLogger(config)
        except Exception as e:
            logger.warning(f"Failed to initialize StructuredLogger: {e}")
            self.structured_logger = None
        
        # Ensure backup directory exists
        self.backup_directory.mkdir(parents=True, exist_ok=True)
        
        logger.info(
            "DatabaseBackup initialized",
            extra={
                'database_path': str(self.database_path),
                'backup_directory': str(self.backup_directory),
                'retention_days': self.retention_days,
                'max_backups': self.max_backups
            }
        )
    
    def create_backup(self, compress: bool = True, validate: bool = True) -> Path:
        """
        Create a new database backup.
        
        Args:
            compress: Whether to compress the backup.
            validate: Whether to validate backup integrity.
            
        Returns:
            Path to created backup file.
        """
        if not self.database_path.exists():
            raise FileNotFoundError(f"Database not found: {self.database_path}")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Use context manager if structured logger is available
        if self.structured_logger:
            from contextlib import nullcontext
            try:
                from ..config.logging_config import LoggedOperation
                context_manager = LoggedOperation(
                    self.structured_logger, f"database_backup_{timestamp}"
                )
            except Exception:
                context_manager = nullcontext()
        else:
            from contextlib import nullcontext
            context_manager = nullcontext()
        
        with context_manager:
            logger.info(f"Creating database backup: {timestamp}")
            
            # Create backup filename
            backup_name = f"notes_tracker_backup_{timestamp}"
            if compress:
                backup_file = self.backup_directory / f"{backup_name}.zip"
            else:
                backup_file = self.backup_directory / f"{backup_name}.db"
            
            try:
                if compress:
                    # Create compressed backup
                    with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                        zf.write(self.database_path, self.database_path.name)
                        
                        # Add metadata
                        metadata = { # type: ignore
                            'backup_timestamp': timestamp,
                            'original_size_bytes': self.database_path.stat().st_size,
                            'database_path': str(self.database_path),
                            'backup_version': '1.0'
                        }
                        
                        import json
                        zf.writestr('backup_metadata.json', json.dumps(metadata, indent=2))
                else:
                    # Simple file copy
                    shutil.copy2(self.database_path, backup_file)
                
                # Validate backup if requested
                if validate:
                    self._validate_backup(backup_file, compress)
                
                logger.info(
                    f"Database backup created successfully: {backup_file.name}",
                    extra={
                        'backup_file': str(backup_file),
                        'backup_size_bytes': backup_file.stat().st_size,
                        'compressed': compress,
                        'validated': validate
                    }
                )
                
                return backup_file
                
            except Exception as e:
                # Clean up failed backup
                if backup_file.exists():
                    backup_file.unlink()
                
                logger.error(f"Backup creation failed: {e}")
                raise
    
    def _validate_backup(self, backup_file: Path, is_compressed: bool) -> None:
        """
        Validate backup integrity.
        
        Args:
            backup_file: Path to backup file.
            is_compressed: Whether backup is compressed.
        """
        logger.info(f"Validating backup: {backup_file.name}")
        
        try:
            if is_compressed:
                # Validate ZIP file and database within
                with zipfile.ZipFile(backup_file, 'r') as zf:
                    # Check ZIP integrity
                    bad_files = zf.testzip()
                    if bad_files:
                        raise RuntimeError(f"Corrupted files in ZIP: {bad_files}")
                    
                    # Extract and test database
                    with zf.open(self.database_path.name) as db_file:
                        # Create temporary file to test database
                        temp_db = self.backup_directory / f"temp_validation_{backup_file.stem}.db"
                        try:
                            with open(temp_db, 'wb') as temp_file:
                                temp_file.write(db_file.read())
                            
                            # Test database connection and integrity
                            self._test_database_integrity(temp_db)
                            
                        finally:
                            # Retry deletion with better error handling for Windows
                            self._safe_file_delete(temp_db)
            else:
                # Test database directly
                self._test_database_integrity(backup_file)
            
            logger.info(f"Backup validation successful: {backup_file.name}")
            
        except Exception as e:
            logger.error(f"Backup validation failed: {e}")
            raise
    
    def _safe_file_delete(self, file_path: Path) -> None:
        """Safely delete a file with retry logic for Windows file locking issues."""
        import time
        
        if not file_path.exists():
            return
        
        max_retries = 3
        retry_delay = 0.1
        
        for attempt in range(max_retries):
            try:
                file_path.unlink()
                return
            except (PermissionError, OSError) as e:
                if attempt < max_retries - 1:
                    logger.debug(f"File deletion attempt {attempt + 1} failed, retrying: {e}")
                    time.sleep(retry_delay * (attempt + 1))
                else:
                    logger.warning(f"Failed to delete temporary file after {max_retries} attempts: {file_path}")
                    # Don't raise exception, just log warning since this is cleanup
    
    def _test_database_integrity(self, db_path: Path) -> None:
        """
        Test database integrity by performing basic operations.
        
        Args:
            db_path: Path to database file.
        """
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # Check database integrity
                cursor.execute("PRAGMA integrity_check")
                result = cursor.fetchone()
                if result[0] != "ok":
                    raise RuntimeError(f"Database integrity check failed: {result[0]}")
                
                # Test basic queries
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                
                if not tables:
                    raise RuntimeError("No tables found in database")
                
                # Test each table
                for table_name, in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                    logger.debug(f"Table {table_name}: {count} rows")
                
        except sqlite3.Error as e:
            raise RuntimeError(f"Database test failed: {e}")
    
    def cleanup_old_backups(self) -> int:
        """
        Remove old backups based on retention policy.
        
        Returns:
            Number of backups removed.
        """
        logger.info("Cleaning up old backups")
        
        # Get all backup files
        backup_files: List[Path] = []
        for pattern in ["*.db", "*.zip"]:
            backup_files.extend(self.backup_directory.glob(pattern))
        
        # Sort by modification time (newest first)
        backup_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        
        removed_count = 0
        cutoff_time = datetime.now() - timedelta(days=self.retention_days)
        
        for backup_file in backup_files:
            file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
            file_age_days = (datetime.now() - file_time).days
            
            # Remove if older than retention period or exceeds max count
            should_remove = (
                file_time < cutoff_time or 
                len(backup_files) - removed_count > self.max_backups
            )
            
            if should_remove:
                try:
                    if backup_file.exists():  # Check if file still exists
                        file_size = backup_file.stat().st_size  # Get size before deletion
                        backup_file.unlink()
                        removed_count += 1
                        
                        logger.info(
                            f"Removed old backup: {backup_file.name}",
                            extra={
                                'file_age_days': file_age_days,
                                'file_size_bytes': file_size
                            }
                        )
                    
                except Exception as e:
                    logger.error(f"Failed to remove backup {backup_file.name}: {e}")
        
        logger.info(f"Cleanup completed - removed {removed_count} old backups")
        return removed_count
    
    def restore_backup(self, backup_file: Path, target_path: Optional[Path] = None) -> None:
        """
        Restore database from backup.
        
        Args:
            backup_file: Path to backup file.
            target_path: Target path for restored database (default: original path).
        """
        if not backup_file.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_file}")
        
        target_path = target_path or self.database_path
        
        logger.info(f"Restoring database from backup: {backup_file.name}")
        
        try:
            # Validate backup before restore
            is_compressed = backup_file.suffix.lower() == '.zip'
            self._validate_backup(backup_file, is_compressed)
            
            # Create backup of current database if it exists
            if target_path.exists():
                backup_current_name = f"{target_path.stem}_pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                backup_current_path = target_path.parent / backup_current_name
                shutil.copy2(target_path, backup_current_path)
                logger.info(f"Created backup of current database: {backup_current_name}")
            
            # Restore from backup
            if is_compressed:
                with zipfile.ZipFile(backup_file, 'r') as zf:
                    with zf.open(self.database_path.name) as source:
                        with open(target_path, 'wb') as target:
                            target.write(source.read())
            else:
                shutil.copy2(backup_file, target_path)
            
            # Validate restored database
            self._test_database_integrity(target_path)
            
            logger.info(f"Database restore completed successfully")
            
        except Exception as e:
            logger.error(f"Database restore failed: {e}")
            raise
    
    def get_backup_info(self) -> List[Dict[str, Any]]:
        """
        Get information about existing backups.
        
        Returns:
            List of backup information dictionaries.
        """
        backup_files: List[Path] = []
        for pattern in ["*.db", "*.zip"]:
            backup_files.extend(self.backup_directory.glob(pattern))
        
        backup_info: List[Dict[str, Any]] = []
        for backup_file in sorted(backup_files, key=lambda p: p.stat().st_mtime, reverse=True):
            stat = backup_file.stat()
            
            info: Dict[str, Any] = {
                'filename': backup_file.name,
                'path': str(backup_file),
                'size_bytes': stat.st_size,
                'size_mb': stat.st_size / (1024 * 1024),
                'created_timestamp': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'age_days': (datetime.now() - datetime.fromtimestamp(stat.st_mtime)).days,
                'is_compressed': backup_file.suffix.lower() == '.zip'
            }
            
            # Add checksum for integrity verification
            info['checksum'] = self._calculate_file_checksum(backup_file)
            
            backup_info.append(info)
        
        return backup_info
    
    def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def create_scheduled_backup(self) -> Path:
        """
        Create a scheduled backup with cleanup.
        
        This method is designed to be called by the scheduler.
        
        Returns:
            Path to created backup file.
        """
        logger.info("Starting scheduled database backup")
        
        try:
            # Create backup
            backup_file = self.create_backup(compress=True, validate=True)
            
            # Cleanup old backups
            removed_count = self.cleanup_old_backups()
            
            logger.info(
                f"Scheduled backup completed successfully",
                extra={
                    'backup_file': backup_file.name,
                    'backups_cleaned': removed_count
                }
            )
            
            return backup_file
            
        except Exception as e:
            logger.error(f"Scheduled backup failed: {e}")
            raise 