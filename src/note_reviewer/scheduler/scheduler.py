"""
Scheduler for note review system.

Handles scheduling and execution of note review jobs.
"""

from __future__ import annotations

import time
import threading
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from loguru import logger

from ..config.logging_config import StructuredLogger, LoggingConfig, LoggedOperation
from ..database.operations import get_notes_not_sent_recently, record_email_sent, initialize_database, DATABASE_PATH
from ..selection.selection_algorithm import SelectionAlgorithm, SelectionCriteria
from ..selection.email_formatter import EmailFormatter
from ..selection.content_analyzer import ContentAnalyzer
from ..security.credentials import CredentialManager


class ScheduleType(Enum):
    """Type of schedule for note review."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class JobStatus(Enum):
    """Status of a job execution."""
    INITIALIZING = "initializing"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ScheduleConfig:
    """Configuration for note review scheduling."""
    schedule_type: ScheduleType
    max_notes_per_email: int
    min_days_between_sends: int
    time_of_day: str  # Format: "HH:MM" in 24-hour format
    max_retries: int = 3
    retry_delay_seconds: int = 300


@dataclass
class JobExecution:
    """Represents a single job execution."""
    job_id: str
    start_time: datetime
    status: JobStatus
    error: Optional[str] = None
    completion_time: Optional[datetime] = None


class NoteScheduler:
    def __init__(
        self,
        config: ScheduleConfig,
        notes_directory: Path,
        credential_manager: CredentialManager
    ) -> None:
        """Initialize note scheduler."""
        self.config = config
        self.notes_directory = notes_directory
        self.credential_manager = credential_manager
        self._current_job: Optional[JobExecution] = None
        self._job_history: List[JobExecution] = []
        
        # Ensure database exists
        initialize_database(DATABASE_PATH)
        
        logger.info(
            "Scheduler initialized",
            extra={
                'config': asdict(config),
                'notes_directory': str(notes_directory)
            }
        )
        
        # Execution tracking
        self.is_running: bool = False  # Tracks if scheduler is running
        self.is_job_running: bool = False  # Tracks if a job is currently running
        self.shutdown_requested: bool = False
        self._last_run_date: Optional[datetime] = None  # Track last run date to prevent duplicate runs
        
        # Initialize components
        self.content_analyzer = ContentAnalyzer()
        self.selection_algorithm = SelectionAlgorithm(self.content_analyzer)
        self.email_formatter = EmailFormatter()
        
        # Setup logging
        try:
            logging_config = LoggingConfig()
            self.structured_logger = StructuredLogger(logging_config)
        except Exception as e:
            logger.warning(f"Failed to initialize structured logging: {e}")
            self.structured_logger = None

    def run_job_now(self) -> str:
        """Run a note review job immediately."""
        job_id = f"manual_{int(time.time())}"
        
        # Initialize job before starting thread
        self._current_job = JobExecution(
            job_id=job_id,
            start_time=datetime.now(),
            status=JobStatus.INITIALIZING
        )
        
        # Set job running state
        self.is_job_running = True
        
        try:
            # Start job in background thread
            thread = threading.Thread(target=self._execute_job, args=(job_id,))
            thread.start()
            
            # Wait briefly to ensure job starts
            time.sleep(0.1)
            
            # Update status to running
            if self._current_job and self._current_job.status == JobStatus.INITIALIZING:
                self._current_job.status = JobStatus.RUNNING
            
            return job_id
            
        except Exception as e:
            # Handle initialization failure
            if self._current_job:
                self._current_job.status = JobStatus.FAILED
                self._current_job.error = str(e)
                self._current_job.completion_time = datetime.now()
                self._job_history.append(self._current_job)
            self.is_job_running = False
            raise

    def _execute_job(self, job_id: str) -> None:
        """Execute a single note review job."""
        try:
            # Get notes not sent recently
            notes = get_notes_not_sent_recently(
                days=self.config.min_days_between_sends,
                db_path=DATABASE_PATH
            )
            
            if not notes:
                logger.info("No notes due for review")
                if self._current_job:
                    self._current_job.status = JobStatus.COMPLETED
                    self._current_job.completion_time = datetime.now()
                return
            
            # Select notes for this email
            selected_notes = self.selection_algorithm.select_notes(
                notes,
                SelectionCriteria(max_notes=self.config.max_notes_per_email)
            )
            
            if not selected_notes:
                logger.info("No notes selected for review")
                if self._current_job:
                    self._current_job.status = JobStatus.COMPLETED
                    self._current_job.completion_time = datetime.now()
                return
            
            # Format and send email
            email_content = self.email_formatter.format_email(selected_notes)
            
            # Record successful send
            for note in selected_notes:
                record_email_sent(
                    note_id=note.note_id,
                    sent_at=datetime.now(),
                    email_subject=email_content.subject,
                    notes_count_in_email=len(selected_notes),
                    db_path=DATABASE_PATH
                )
            
            if self._current_job:
                self._current_job.status = JobStatus.COMPLETED
                self._current_job.completion_time = datetime.now()
            
            # Add to history
            if self._current_job:
                self._job_history.append(self._current_job)
            
            # Update last run date
            self._last_run_date = datetime.now()
            
        except Exception as e:
            logger.error(f"Job execution failed: {e}")
            if self._current_job:
                self._current_job.status = JobStatus.FAILED
                self._current_job.error = str(e)
                self._current_job.completion_time = datetime.now()
                self._job_history.append(self._current_job)
        finally:
            self.is_job_running = False

    def get_job_status(self) -> Dict[str, Any]:
        """Get current job status and execution history."""
        status: Dict[str, Any] = {
            'is_running': self.is_running,
            'current_job': None,
            'history': [],
            'statistics': self._calculate_statistics()
        }
        
        if self._current_job:
            status['current_job'] = {
                'job_id': self._current_job.job_id,
                'status': self._current_job.status.value,
                'start_time': self._current_job.start_time.isoformat(),
                'completion_time': self._current_job.completion_time.isoformat() if self._current_job.completion_time else None,
                'error': self._current_job.error
            }
        
        status['history'] = [
            {
                'job_id': job.job_id,
                'status': job.status.value,
                'start_time': job.start_time.isoformat(),
                'completion_time': job.completion_time.isoformat() if job.completion_time else None,
                'error': job.error
            }
            for job in self._job_history[-10:]  # Last 10 jobs
        ]
        
        return status

    def _calculate_statistics(self) -> Dict[str, Any]:
        """Calculate job execution statistics."""
        total_jobs = len(self._job_history)
        if total_jobs == 0:
            return {
                'total_jobs': 0,
                'successful_jobs': 0,
                'failed_jobs': 0,
                'success_rate': 0.0,
                'average_execution_time_seconds': 0.0
            }
        
        successful_jobs = sum(1 for job in self._job_history if job.status == JobStatus.COMPLETED)
        failed_jobs = sum(1 for job in self._job_history if job.status == JobStatus.FAILED)
        
        # Calculate average execution time for completed jobs
        execution_times = [
            (job.completion_time - job.start_time).total_seconds()
            for job in self._job_history
            if job.status == JobStatus.COMPLETED and job.completion_time
        ]
        
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0.0
        
        return {
            'total_jobs': total_jobs,
            'successful_jobs': successful_jobs,
            'failed_jobs': failed_jobs,
            'success_rate': successful_jobs / total_jobs,
            'average_execution_time_seconds': avg_execution_time
        }

    def start(self) -> None:
        """Start the scheduler."""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return

        self.shutdown_requested = False
        self.is_running = True
        self.is_job_running = False
        
        # Start the scheduler thread
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop)
        self._scheduler_thread.daemon = True  # Make thread daemon so it exits when main thread exits
        self._scheduler_thread.start()
        
        # Log next scheduled run
        scheduled_time = datetime.strptime(self.config.time_of_day, "%H:%M").time()
        logger.info(f"Scheduler started. Next run scheduled for {scheduled_time}")

    def stop(self) -> None:
        """Stop the scheduler."""
        if not self.is_running:
            logger.warning("Scheduler is not running")
            return

        self.shutdown_requested = True
        self.is_running = False
        
        # Wait for scheduler thread to finish if it exists
        if hasattr(self, '_scheduler_thread') and self._scheduler_thread.is_alive():
            self._scheduler_thread.join(timeout=5.0)  # Wait up to 5 seconds
        
        logger.info("Scheduler stopped")

    def wait_for_shutdown(self) -> None:
        """Wait for the scheduler to shut down."""
        if hasattr(self, '_scheduler_thread'):
            self._scheduler_thread.join()

    def _scheduler_loop(self) -> None:
        """Main scheduler loop that runs in a separate thread."""
        while not self.shutdown_requested:
            try:
                # Check if it's time to run a job based on schedule
                current_time = datetime.now()
                scheduled_time = datetime.strptime(self.config.time_of_day, "%H:%M").time()
                
                # Check if we should run (within the same minute and not already run today)
                should_run = (
                    current_time.hour == scheduled_time.hour and
                    current_time.minute == scheduled_time.minute and
                    (self._last_run_date is None or
                     self._last_run_date.date() < current_time.date()) and
                    not self.is_job_running
                )
                
                if should_run:
                    logger.info("Scheduled time reached, starting job")
                    self.run_job_now()
                
                # Sleep for 30 seconds before next check (more frequent checks to avoid missing the time)
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(self.config.retry_delay_seconds)  # Wait before retrying 