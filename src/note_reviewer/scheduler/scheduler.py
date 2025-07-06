"""
Local Scheduling System for Note Review Automation

Provides reliable scheduling with the `schedule` library, supporting various 
schedule types with proper error handling and graceful shutdown.
"""

from __future__ import annotations

import signal
import time
import threading
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import schedule
from loguru import logger

from ..config.logging_config import StructuredLogger, LoggingConfig, LoggedOperation
from ..database.operations import get_notes_not_sent_recently, record_email_sent
from ..selection.selection_algorithm import SelectionAlgorithm, SelectionCriteria
from ..selection.email_formatter import EmailFormatter
from ..selection.content_analyzer import ContentAnalyzer
from ..email.service import EmailService
from ..security.credentials import CredentialManager


class ScheduleType(Enum):
    """Supported schedule types."""
    DAILY = "daily"
    WEEKLY = "weekly"
    HOURLY = "hourly"
    EVERY_N_HOURS = "every_n_hours"
    CUSTOM = "custom"


class JobStatus(Enum):
    """Job execution status."""
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class ScheduleConfig:
    """Configuration for scheduling behavior."""
    
    # Schedule settings
    schedule_type: ScheduleType = ScheduleType.DAILY
    time_of_day: str = "09:00"  # HH:MM format
    day_of_week: Optional[str] = None  # For weekly: monday, tuesday, etc.
    interval_hours: int = 24  # For every_n_hours
    
    # Email settings
    max_notes_per_email: int = 5
    min_days_between_sends: int = 7
    
    # System settings
    check_interval_seconds: int = 60
    max_retries: int = 3
    retry_delay_seconds: int = 300  # 5 minutes
    
    # Graceful shutdown
    shutdown_timeout_seconds: int = 30
    
    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if self.schedule_type == ScheduleType.WEEKLY and not self.day_of_week:
            raise ValueError("day_of_week required for weekly schedule")
        
        if not (0 <= int(self.time_of_day.split(':')[0]) <= 23):
            raise ValueError("Invalid hour in time_of_day")
            
        if not (0 <= int(self.time_of_day.split(':')[1]) <= 59):
            raise ValueError("Invalid minute in time_of_day")


@dataclass
class JobExecution:
    """Represents a job execution instance."""
    job_id: str
    status: JobStatus
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    notes_processed: int = 0
    emails_sent: int = 0
    retry_count: int = 0


class NoteScheduler:
    """
    Reliable local scheduling system for note review automation.
    
    Features:
    - Multiple schedule types (daily, weekly, hourly, custom)
    - Graceful shutdown with signal handling
    - Comprehensive error handling and retries
    - Job status tracking and logging
    - Clean event loop with proper sleep intervals
    """
    
    def __init__(
        self,
        config: ScheduleConfig,
        notes_directory: Path,
        credential_manager: CredentialManager
    ) -> None:
        """
        Initialize the scheduler.
        
        Args:
            config: Scheduling configuration.
            notes_directory: Directory containing notes to process.
            credential_manager: For accessing email credentials.
        """
        self.config = config
        self.notes_directory = Path(notes_directory)
        self.credential_manager = credential_manager
        
        # Execution tracking
        self.job_history: List[JobExecution] = []
        self.is_running: bool = False
        self.shutdown_requested: bool = False
        self.current_job: Optional[JobExecution] = None
        
        # Initialize components
        content_analyzer = ContentAnalyzer()
        self.selection_algorithm = SelectionAlgorithm(content_analyzer)
        self.email_formatter = EmailFormatter()
        self.email_service: Optional[EmailService] = None
        
        # Initialize structured logger
        try:
            config_obj = LoggingConfig()
            self.structured_logger = StructuredLogger(config_obj)
        except Exception as e:
            logger.warning(f"Failed to initialize StructuredLogger: {e}")
            self.structured_logger = None
        
        # Threading
        self.scheduler_thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()
        
        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()
        
        logger.info(
            "NoteScheduler initialized",
            extra={
                'schedule_type': config.schedule_type.value,
                'time_of_day': config.time_of_day,
                'notes_directory': str(notes_directory),
                'max_notes_per_email': config.max_notes_per_email
            }
        )
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum: int, frame: Any) -> None:
            signal_name = signal.Signals(signum).name
            logger.info(f"Received {signal_name}, initiating graceful shutdown...")
            self.stop()
        
        # Handle common shutdown signals
        signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler)  # Termination
        
        # Windows doesn't have SIGHUP
        if hasattr(signal, 'SIGHUP'):
            signal.signal(signal.SIGHUP, signal_handler)  # type: ignore
    
    def start(self) -> None:
        """Start the scheduler in a separate thread."""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        self.is_running = True
        self.shutdown_requested = False
        
        # Initialize email service
        try:
            email_creds, _ = self.credential_manager.load_credentials()
            
            from ..email.service import EmailConfig
            email_config = EmailConfig(
                smtp_server="smtp.gmail.com",
                smtp_port=587,
                username=email_creds.username,
                password=email_creds.password,
                from_email=email_creds.username,
                from_name=email_creds.from_name,
                max_emails_per_hour=email_creds.max_emails_per_hour
            )
            
            self.email_service = EmailService(email_config)
            
        except Exception as e:
            logger.error(f"Failed to initialize email service: {e}")
            self.is_running = False
            raise
        
        # Setup schedule based on config
        self._setup_schedule()
        
        # Start scheduler thread (non-daemon so it keeps process alive)
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=False)
        self.scheduler_thread.start()
        
        logger.info("NoteScheduler started successfully")
    
    def wait_for_shutdown(self) -> None:
        """Wait for scheduler to shutdown (blocking call)."""
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            try:
                self.scheduler_thread.join()
            except KeyboardInterrupt:
                logger.info("Shutdown requested via keyboard interrupt")
                self.stop()
    
    def stop(self) -> None:
        """Stop the scheduler gracefully."""
        if not self.is_running:
            return
        
        logger.info("Stopping NoteScheduler...")
        self.shutdown_requested = True
        
        # Wait for current job to complete or timeout
        start_time = time.time()
        while (self.current_job and 
               self.current_job.status == JobStatus.RUNNING and
               time.time() - start_time < self.config.shutdown_timeout_seconds):
            time.sleep(1)
        
        # Force stop if timeout exceeded
        if self.current_job and self.current_job.status == JobStatus.RUNNING:
            logger.warning("Forcefully stopping current job due to timeout")
            with self.lock:
                if self.current_job:
                    self.current_job.status = JobStatus.CANCELLED
                    self.current_job.end_time = datetime.now()
        
        self.is_running = False
        
        # Wait for scheduler thread to finish
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)
        
        logger.info("NoteScheduler stopped")
    
    def _setup_schedule(self) -> None:
        """Setup the schedule based on configuration."""
        schedule.clear()  # Clear any existing schedules
        
        job_func = self._execute_note_review_job
        
        if self.config.schedule_type == ScheduleType.DAILY:
            schedule.every().day.at(self.config.time_of_day).do(job_func)  # type: ignore
            logger.info(f"Scheduled daily job at {self.config.time_of_day}")
            
            # Log next run time
            next_run = schedule.next_run()
            if next_run:
                logger.info(f"Next scheduled run: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            
        elif self.config.schedule_type == ScheduleType.WEEKLY:
            if not self.config.day_of_week:
                raise ValueError("day_of_week required for weekly schedule")
            
            getattr(schedule.every(), self.config.day_of_week.lower()).at(
                self.config.time_of_day
            ).do(job_func)  # type: ignore
            logger.info(
                f"Scheduled weekly job on {self.config.day_of_week} at {self.config.time_of_day}"
            )
            
        elif self.config.schedule_type == ScheduleType.HOURLY:
            schedule.every().hour.do(job_func)  # type: ignore
            logger.info("Scheduled hourly job")
            
        elif self.config.schedule_type == ScheduleType.EVERY_N_HOURS:
            schedule.every(self.config.interval_hours).hours.do(job_func)  # type: ignore
            logger.info(f"Scheduled job every {self.config.interval_hours} hours")
            
        else:
            raise ValueError(f"Unsupported schedule type: {self.config.schedule_type}")
    
    def _run_scheduler(self) -> None:
        """Main scheduler event loop."""
        logger.info("Scheduler event loop started")
        
        while self.is_running and not self.shutdown_requested:
            try:
                # Run pending jobs
                schedule.run_pending()
                
                # Sleep for check interval
                time.sleep(self.config.check_interval_seconds)
                
            except Exception as e:
                logger.error(f"Error in scheduler event loop: {e}")
                time.sleep(self.config.check_interval_seconds)
        
        logger.info("Scheduler event loop stopped")
    
    def _execute_note_review_job(self) -> None:
        """Execute a complete note review job."""
        job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        with self.lock:
            self.current_job = JobExecution(job_id=job_id, status=JobStatus.PENDING)
            self.job_history.append(self.current_job)
        
        logger.info(f"Starting note review job: {job_id}")
        
        try:
            if self.structured_logger:
                context_manager = LoggedOperation(self.structured_logger, f"note_review_job_{job_id}")
            else:
                from contextlib import nullcontext
                context_manager = nullcontext()
                
            with context_manager:
                self._run_job_with_retries(self.current_job)
                
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            with self.lock:
                if self.current_job:
                    self.current_job.status = JobStatus.FAILED
                    self.current_job.error_message = str(e)
                    self.current_job.end_time = datetime.now()
        
        finally:
            with self.lock:
                self.current_job = None
    
    def _run_job_with_retries(self, job: JobExecution) -> None:
        """Run job with retry logic."""
        for attempt in range(self.config.max_retries + 1):
            try:
                with self.lock:
                    job.status = JobStatus.RUNNING
                    job.start_time = datetime.now()
                    job.retry_count = attempt
                
                self._execute_job_logic(job)
                
                with self.lock:
                    job.status = JobStatus.COMPLETED
                    job.end_time = datetime.now()
                
                logger.info(
                    f"Job {job.job_id} completed successfully",
                    extra={
                        'notes_processed': job.notes_processed,
                        'emails_sent': job.emails_sent,
                        'attempt': attempt + 1
                    }
                )
                return
                
            except Exception as e:
                logger.error(f"Job {job.job_id} attempt {attempt + 1} failed: {e}")
                
                if attempt < self.config.max_retries:
                    logger.info(f"Retrying job {job.job_id} in {self.config.retry_delay_seconds} seconds")
                    time.sleep(self.config.retry_delay_seconds)
                else:
                    raise
    
    def _execute_job_logic(self, job: JobExecution) -> None:
        """Execute the core job logic."""
        # Get candidate notes
        notes = get_notes_not_sent_recently(self.config.min_days_between_sends)
        
        logger.info(f"Database query returned {len(notes)} candidate notes")
        if not notes:
            logger.info("No notes available for sending")
            return
        
        job.notes_processed = len(notes)
        
        # Select best notes using algorithm with more permissive criteria
        criteria = SelectionCriteria(
            max_notes=self.config.max_notes_per_email,
            max_email_length_chars=20000,  # email length
            min_word_count=5,
            max_days_since_modification=365,
            avoid_duplicates=False
        )
        
        logger.info(f"Attempting to select up to {criteria.max_notes} notes from {len(notes)} candidates")
        selected_notes = self.selection_algorithm.select_notes(notes, criteria)
        
        logger.info(f"Selection algorithm returned {len(selected_notes)} notes")
        if not selected_notes:
            logger.warning("No notes selected by algorithm - this may indicate selection criteria are too restrictive")
            # Log details about candidate notes for debugging
            for i, note in enumerate(notes[:5]):  # Log first 5 notes for debugging
                logger.debug(f"Candidate note {i+1}: {note.file_path}, modified: {note.modified_at}")
            return
        
        # Format email with character-based preview (300 chars max)
        email_content = self.email_formatter.format_email(
            selected_notes,
            template_name="rich_review",
            include_toc=False,
            max_preview_words=300
        )
        
        # Send email
        if not self.email_service:
            raise RuntimeError("Email service not initialized")
        
        _, app_config = self.credential_manager.load_credentials()
        
        from ..database.models import Note
        notes_for_email = [
            Note(
                id=score.note_id,
                file_path=score.file_path,
                content_hash="",  # Will be calculated by email service if needed
                file_size=0,  # Will be calculated by email service if needed
                created_at=datetime.now(),
                modified_at=datetime.now()
            )
            for score in selected_notes
        ]
        
        self.email_service.send_notes_email(
            to_email=app_config.recipient_email,
            subject=email_content.subject,
            html_content=email_content.html_content,
            text_content=email_content.plain_text_content,
            notes=notes_for_email,
            attach_files=True  # Enable file attachments for full note content
        )
        
        # Record send history for each note
        for note_score in selected_notes:
            record_email_sent(
                note_id=note_score.note_id,
                sent_at=datetime.now(),
                email_subject=email_content.subject,
                notes_count_in_email=len(selected_notes)
            )
        
        job.emails_sent = 1
        
        logger.info(
            f"Successfully sent email with {len(selected_notes)} notes",
            extra={
                'selected_notes': len(selected_notes),
                'total_words': email_content.total_word_count,
                'categories': email_content.categories
            }
        )
    
    def get_job_status(self) -> Dict[str, Any]:
        """Get current job status and statistics."""
        with self.lock:
            current_status = None
            if self.current_job:
                current_status = { # type: ignore
                    'job_id': self.current_job.job_id,
                    'status': self.current_job.status.value,
                    'start_time': self.current_job.start_time.isoformat() if self.current_job.start_time else None,
                    'notes_processed': self.current_job.notes_processed,
                    'emails_sent': self.current_job.emails_sent,
                    'retry_count': self.current_job.retry_count
                }
            
            # Job history statistics
            total_jobs = len(self.job_history)
            completed_jobs = sum(1 for job in self.job_history if job.status == JobStatus.COMPLETED)
            failed_jobs = sum(1 for job in self.job_history if job.status == JobStatus.FAILED)
            
            # Get next run time safely
            next_run_time: Optional[str] = None
            if schedule.jobs:
                try:
                    next_run = schedule.next_run()
                    if next_run:
                        next_run_time = next_run.isoformat()
                except Exception:
                    pass
            
            return {
                'is_running': self.is_running,
                'shutdown_requested': self.shutdown_requested,
                'current_job': current_status,
                'statistics': {
                    'total_jobs': total_jobs,
                    'completed_jobs': completed_jobs,
                    'failed_jobs': failed_jobs,
                    'success_rate': completed_jobs / total_jobs if total_jobs > 0 else 0.0
                },
                'next_run': next_run_time
            }
    
    def run_job_now(self) -> str:
        """Manually trigger a job execution."""
        if self.current_job and self.current_job.status == JobStatus.RUNNING:
            raise RuntimeError("Another job is currently running")
        
        job_id = f"manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        logger.info(f"Manually triggering job: {job_id}")
        
        # Execute in separate thread to avoid blocking
        thread = threading.Thread(target=self._execute_note_review_job, daemon=True)
        thread.start()
        
        return job_id 