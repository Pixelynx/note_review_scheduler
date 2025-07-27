#!/usr/bin/env python3
"""
GitHub Actions Scanning Integration

This script handles automated note scanning in GitHub Actions environments,
providing silent operation, comprehensive scanning, and artifact generation.
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.note_reviewer.scanner.file_scanner import FileScanner
from src.note_reviewer.database.operations import initialize_database, add_or_update_note
from src.note_reviewer.security.credentials import CredentialManager
from loguru import logger


def is_github_actions() -> bool:
    """Detect if running in GitHub Actions environment."""
    return os.getenv('GITHUB_ACTIONS') == 'true'


def setup_silent_logging() -> None:
    """Configure logging for CI environment."""
    # Remove default logger
    logger.remove()
    
    # Add minimal console logger for CI
    logger.add(
        sys.stderr,
        format="{time} | {level} | {message}",
        level="INFO",
        enqueue=True
    )
    
    # Add file logger for detailed diagnostics
    log_file = Path("logs/github_scan.log")
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        level="DEBUG",
        rotation="1 week",
        retention="1 month",
        compression="zip"
    )


def has_supported_files(directory: Path, recursive: bool = True) -> bool:
    """Check if directory contains supported note files."""
    extensions = {'.md', '.txt', '.org', '.rst'}
    
    if recursive:
        for ext in extensions:
            if list(directory.rglob(f"*{ext}")):
                return True
    else:
        for ext in extensions:
            if list(directory.glob(f"*{ext}")):
                return True
    
    return False


def discover_repository_notes(repo_root: Path) -> List[Path]:
    """Discover note directories in repository structure."""
    potential_dirs = [
        repo_root / "notes",
        repo_root / "docs", 
        repo_root / "wiki",
        repo_root / "content",
        repo_root  # Root level notes
    ]
    
    found_dirs = []
    for dir_path in potential_dirs:
        if dir_path.exists() and has_supported_files(dir_path, recursive=True):
            found_dirs.append(dir_path)
            
    return found_dirs


def setup_credentials_from_environment() -> Tuple[bool, Optional[CredentialManager]]:
    """Setup credentials from GitHub secrets environment variables."""
    try:
        master_password = os.getenv('MASTER_PASSWORD')
        if not master_password:
            logger.error("MASTER_PASSWORD environment variable not set")
            if is_github_actions():
                print("::error::MASTER_PASSWORD secret not configured")
            return False, None
        
        config_file = Path("config/encrypted_config.json")
        credential_manager = CredentialManager(config_file, master_password)
        
        # Load and validate credentials
        try:
            email_creds, app_config = credential_manager.load_credentials()
            logger.info(f"Loaded credentials for: {email_creds.username}")
            return True, credential_manager
            
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
            if is_github_actions():
                print(f"::error::Failed to load credentials: {e}")
            return False, None
            
    except Exception as e:
        logger.error(f"Failed to setup credentials: {e}")
        if is_github_actions():
            print(f"::error::Failed to setup credentials: {e}")
        return False, None


def set_github_outputs(stats: Dict[str, Any]) -> None:
    """Set GitHub Actions step outputs for workflow integration."""
    if not is_github_actions():
        return
        
    # Set outputs that other workflow steps can use
    outputs = {
        'scan-status': 'success' if stats.get('error_files', 0) == 0 else 'warning',
        'files-scanned': str(stats.get('scanned_files', 0)),
        'scan-duration': f"{stats.get('scan_duration_seconds', 0):.2f}",
        'database-updates': str(stats.get('database_updates', 0))
    }
    
    for key, value in outputs.items():
        print(f"::set-output name={key}::{value}")
        
    # Set environment variables for later steps
    github_env_file = os.getenv('GITHUB_ENV')
    if github_env_file:
        with open(github_env_file, 'a') as f:
            for key, value in outputs.items():
                f.write(f"SCAN_{key.upper().replace('-', '_')}={value}\n")


def run_with_github_formatting(
    notes_path: Path,
    database_path: Path,
    scanner: FileScanner
) -> Tuple[bool, Dict[str, Any]]:
    """Run scan with GitHub Actions specific formatting."""
    print(f"::group::Scanning notes directory: {notes_path}")
    
    try:
        # Run comprehensive scan
        results, stats = scanner.scan_directory(notes_path, recursive=True)
        
        # Convert stats to dict for easier handling
        stats_dict = {
            "total_files": stats.total_files,
            "scanned_files": stats.scanned_files,
            "success_rate": stats.success_rate,
            "error_files": stats.error_files,
            "scan_duration_seconds": stats.scan_duration_seconds
        }
        
        # Update database with results
        success_count = 0
        for result in results:
            if result.is_valid:
                try:
                    add_or_update_note(
                        file_path=result.file_path,
                        content_hash=result.content_hash,
                        file_size=result.file_size,
                        created_at=result.created_at,
                        modified_at=result.modified_at,
                        db_path=database_path
                    )
                    success_count += 1
                except Exception as e:
                    logger.error(f"Failed to add {result.file_path} to database: {e}")
                    continue
        
        stats_dict["database_updates"] = success_count
        
        print(f"::notice::Successfully scanned {stats.scanned_files} files")
        if stats.error_files > 0:
            print(f"::warning::Found {stats.error_files} files with errors")
            
        return True, stats_dict
        
    except Exception as e:
        print(f"::error::Scan failed: {e}")
        return False, {}
    finally:
        print("::endgroup::")


def generate_scan_report(stats: Dict[str, Any], output_file: Path) -> None:
    """Generate a JSON report of scan results for workflow artifacts."""
    report = {
        "timestamp": datetime.now().isoformat(),
        "environment": "github_actions",
        "statistics": stats,
        "status": "success" if stats.get("error_files", 0) == 0 else "warning"
    }
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(report, indent=2))
    logger.info(f"Scan report generated: {output_file}")


def setup_github_scanning(
    notes_dir: Optional[str] = None,
    db_path: Optional[str] = None
) -> bool:
    """Setup and run scanning in GitHub Actions environment.
    
    Args:
        notes_dir: Override for notes directory path
        db_path: Override for database path
        
    Returns:
        bool: True if scan completed successfully
    """
    if is_github_actions():
        setup_silent_logging()
        print("::group::Setting up note scanning")
    
    try:
        # 1. Load credentials from GitHub secrets
        success, credential_manager = setup_credentials_from_environment()
        if not success or credential_manager is None:
            return False
            
        # Get configuration
        _, app_config = credential_manager.load_credentials()
        
        # Use config values or overrides
        database_path = Path(db_path if db_path is not None else app_config.database_path)
        database_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        logger.info(f"Initializing database at {database_path}")
        initialize_database(database_path)
        
        # 2. Discover repository structure  
        if notes_dir:
            repo_notes_dirs = [Path(notes_dir)]
        else:
            repo_notes_dirs = discover_repository_notes(Path('.'))
            
        if not repo_notes_dirs:
            logger.warning("No note directories found in repository")
            if is_github_actions():
                print("::warning::No note directories found in repository")
            return True
            
        # Initialize scanner with all features
        scanner = FileScanner(
            extract_tags=True,
            extract_links=True,
            generate_summary=True
        )
        
        # 3. Run scan with GitHub formatting
        all_stats: Dict[str, Any] = {
            "total_files": 0,
            "scanned_files": 0,
            "error_files": 0,
            "database_updates": 0,
            "scan_duration_seconds": 0.0
        }
        
        for notes_directory in repo_notes_dirs:  # ✅ Different variable name
            success, stats = run_with_github_formatting(notes_directory, database_path, scanner)
            if success:
                # Aggregate statistics
                all_stats["total_files"] += stats.get("total_files", 0)
                all_stats["scanned_files"] += stats.get("scanned_files", 0)
                all_stats["error_files"] += stats.get("error_files", 0)
                all_stats["database_updates"] += stats.get("database_updates", 0)
                all_stats["scan_duration_seconds"] += stats.get("scan_duration_seconds", 0)
        
        # 4. Set GitHub outputs
        set_github_outputs(all_stats)
        
        # 5. Generate artifacts
        artifacts_dir = Path("artifacts")
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        generate_scan_report(all_stats, artifacts_dir / "scan_report.json")
        
        logger.info("GitHub Actions scan completed successfully")
        return True
        
    except Exception as e:
        if is_github_actions():
            print(f"::error::Setup failed: {e}")
        logger.error(f"GitHub Actions scan failed: {e}")
        return False
    finally:
        if is_github_actions():
            print("::endgroup::")


if __name__ == "__main__":
    success = setup_github_scanning()
    sys.exit(0 if success else 1) 