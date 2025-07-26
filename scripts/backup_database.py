#!/usr/bin/env python3
"""
Database Backup Script for Note Review Scheduler

Creates database backups with validation and cleanup for both manual use
and GitHub Actions integration.
"""

import argparse
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.note_reviewer.scheduler.backup import DatabaseBackup
from loguru import logger


def main() -> None:
    """Main backup execution."""
    parser = argparse.ArgumentParser(description="Create database backup")
    parser.add_argument('--compress', action='store_true', default=True,
                       help='Compress backup (default: True)')
    parser.add_argument('--validate', action='store_true', default=True,
                       help='Validate backup integrity (default: True)')
    parser.add_argument('--cleanup', action='store_true', default=True,
                       help='Clean up old backups (default: True)')
    parser.add_argument('--upload-to-artifacts', action='store_true',
                       help='Prepare backup for GitHub Actions artifacts')
    parser.add_argument('--output-dir', 
                       help='Custom backup directory')
    
    args = parser.parse_args()
    
    # Setup logging
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss} | {level} | {message}")
    
    try:
        # Initialize backup system
        backup_dir = Path(args.output_dir) if args.output_dir else Path("data/backups")
        backup_system = DatabaseBackup(backup_directory=backup_dir)
        
        # Check if database exists
        if not backup_system.database_path.exists():
            logger.warning(f"No database found at {backup_system.database_path}. Nothing to backup.")
            if args.upload_to_artifacts:
                # Ensure backup directory exists for artifacts even if empty
                backup_dir.mkdir(parents=True, exist_ok=True)
            return

        # Create backup
        logger.info("Starting database backup...")
        backup_file = backup_system.create_backup(
            compress=args.compress,
            validate=args.validate
        )
        
        # Cleanup old backups
        if args.cleanup:
            removed_count = backup_system.cleanup_old_backups()
            logger.info(f"Cleaned up {removed_count} old backups")
        
        # Prepare for GitHub Actions artifacts
        if args.upload_to_artifacts:
            logger.info("Preparing backup for GitHub Actions artifacts")
            # Ensure the backup directory is accessible for artifacts
            backup_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Backup completed successfully: {backup_file}")
        
        # Output backup information
        backup_info = backup_system.get_backup_info()
        if backup_info:
            latest = backup_info[0]
            logger.info(f"Backup size: {latest['size_mb']:.1f} MB")
            logger.info(f"Backup checksum: {latest['checksum'][:16]}...")
        
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 