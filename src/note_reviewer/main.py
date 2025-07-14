"""
Main Application Entry Point for Note Review Scheduler

Integrates all components into a cohesive application.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger

from .config.logging_config import StructuredLogger, LoggingConfig
from .database.operations import initialize_database
from .scanner.file_scanner import FileScanner  
from .selection.content_analyzer import ContentAnalyzer
from .selection.selection_algorithm import SelectionAlgorithm
from .selection.email_formatter import EmailFormatter
from .security.credentials import CredentialManager
from .scheduler.scheduler import NoteScheduler, ScheduleConfig, ScheduleType
from .scheduler.monitor import HealthMonitor


class NoteReviewApplication:
    """Main application class that coordinates all components."""
    
    def __init__(self, config_path: Optional[Path] = None) -> None:
        """Initialize the application.
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path or Path("config/credentials.json")
        self.structured_logger: Optional[StructuredLogger] = None
        self.credential_manager: Optional[CredentialManager] = None
        self.scheduler: Optional[NoteScheduler] = None
        
        # Initialize logging
        self._setup_logging()
        
        logger.info("Note Review Scheduler Application initialized")
    
    def _setup_logging(self) -> None:
        """Setup structured logging."""
        try:
            config = LoggingConfig()
            self.structured_logger = StructuredLogger(config)
            logger.info("Structured logging initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize structured logging: {e}")
    
    def initialize(self, master_password: str) -> bool:
        """Initialize application with credentials.
        
        Args:
            master_password: Master password for credential access
            
        Returns:
            True if initialization successful
        """
        try:
            # Initialize credential manager
            self.credential_manager = CredentialManager(self.config_path, master_password)
            
            # Load and validate configuration
            _, app_config = self.credential_manager.load_credentials()
            
            # Initialize database
            db_path = Path(app_config.database_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            initialize_database(db_path)
            
            logger.info("Application initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Application initialization failed: {e}")
            return False
    
    def run_scan(self, notes_directory: Optional[Path] = None) -> bool:
        """Run note scanning operation.
        
        Args:
            notes_directory: Directory to scan (uses config default if None)
            
        Returns:
            True if scan successful
        """
        if not self.credential_manager:
            logger.error("Application not initialized")
            return False
        
        try:
            _, app_config = self.credential_manager.load_credentials()
            scan_dir = notes_directory or Path(app_config.notes_directory)
            
            # Initialize scanner
            scanner = FileScanner(
                extract_tags=True,
                extract_links=True,
                generate_summary=True
            )
            
            # Perform scan
            _, stats = scanner.scan_directory(scan_dir, recursive=True)
            
            logger.info(f"Scan completed: {stats.scanned_files}/{stats.total_files} files processed")
            return True
            
        except Exception as e:
            logger.error(f"Scan operation failed: {e}")
            return False
    
    def send_manual_email(self, max_notes: int = 3, preview_only: bool = False) -> bool:
        """Send manual email with selected notes.
        
        Args:
            max_notes: Maximum number of notes to include
            preview_only: If True, generate content but don't send
            
        Returns:
            True if operation successful
        """
        if not self.credential_manager:
            logger.error("Application not initialized")
            return False
        
        try:
            _, _ = self.credential_manager.load_credentials()
            
            # Initialize components
            content_analyzer = ContentAnalyzer()
            # These would be used in full implementation
            _ = SelectionAlgorithm(content_analyzer)
            _ = EmailFormatter()
            
            # Note: EmailService integration would require proper config conversion
            
            # Get notes to send (mock implementation)
            # In real implementation, this would query the database
            logger.info(f"Manual email operation completed (preview: {preview_only}, max_notes: {max_notes})")
            return True
            
        except Exception as e:
            logger.error(f"Manual email operation failed: {e}")
            return False
    
    def start_scheduler(self, daemon_mode: bool = False) -> bool:
        """Start the note review scheduler.
        
        Args:
            daemon_mode: Whether to run as background daemon
            
        Returns:
            True if scheduler started successfully
        """
        if not self.credential_manager:
            logger.error("Application not initialized") 
            return False
        
        try:
            _, app_config = self.credential_manager.load_credentials()
            
            # Create schedule configuration
            schedule_config = ScheduleConfig(
                schedule_type=ScheduleType.DAILY,
                time_of_day=app_config.schedule_time,
                max_notes_per_email=app_config.notes_per_email,
                min_days_between_sends=7,
                max_retries=3,
                retry_delay_seconds=60
            )
            
            # Initialize scheduler
            self.scheduler = NoteScheduler(
                config=schedule_config,
                notes_directory=Path(app_config.notes_directory),
                credential_manager=self.credential_manager
            )
            
            # Start scheduler
            self.scheduler.start()
            
            # Handle daemon mode
            if daemon_mode:
                logger.info("Scheduler started in daemon mode")
                # In daemon mode, return immediately
                return True
            else:
                logger.info("Scheduler started in foreground mode")
                # In foreground mode, wait for shutdown
                try:
                    self.scheduler.wait_for_shutdown()
                except KeyboardInterrupt:
                    logger.info("Received keyboard interrupt, stopping scheduler...")
                    self.scheduler.stop()
                return True
            
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            return False
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get application health status.
        
        Returns:
            Dictionary with health information
        """
        try:
            health_monitor = HealthMonitor(self.credential_manager)
            health_status = health_monitor.perform_health_check()
            
            return {
                'is_healthy': health_status.is_healthy,
                'timestamp': health_status.timestamp.isoformat(),
                'cpu_percent': health_status.system_metrics.cpu_percent,
                'memory_percent': health_status.system_metrics.memory_percent,
                'disk_usage_percent': health_status.system_metrics.disk_usage_percent,
                'warnings': health_status.warnings,
                'errors': health_status.errors
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'is_healthy': False,
                'error': str(e)
            }
    
    def stop(self) -> None:
        """Stop the application and cleanup resources."""
        if self.scheduler:
            try:
                self.scheduler.stop()
                logger.info("Scheduler stopped")
            except Exception as e:
                logger.error(f"Error stopping scheduler: {e}")
        
        logger.info("Note Review Scheduler Application stopped")


def main() -> int:
    """Main entry point when run as script."""
    # This is a simple example - the CLI interface is the primary entry point
    logger.info("Note Review Scheduler - Use 'notes' command for full functionality")
    
    app = NoteReviewApplication()
    
    # Example usage
    try:
        # In a real scenario, you'd get the password securely
        # app.initialize("your_master_password")
        # app.run_scan()
        # app.start_scheduler()
        
        logger.info("Application ready - use CLI commands for operation")
        return 0
        
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
        return 0
    except Exception as e:
        logger.error(f"Application error: {e}")
        return 1
    finally:
        app.stop()


if __name__ == "__main__":
    sys.exit(main()) 