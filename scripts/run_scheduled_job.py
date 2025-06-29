#!/usr/bin/env python3
"""
Run scheduled note review job for GitHub Actions execution.

This script executes a single note review job with proper error handling,
logging, and integration with GitHub Actions workflow.
"""

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.note_reviewer.scheduler.scheduler import NoteScheduler, ScheduleConfig, ScheduleType
from src.note_reviewer.security.credentials import CredentialManager
from loguru import logger


def setup_logging(log_level: str) -> None:
    """Setup logging for GitHub Actions execution."""
    
    # Remove default handler
    logger.remove()
    
    # Add file handler
    log_file = Path("logs") / f"scheduled_job_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log_file.parent.mkdir(exist_ok=True)
    
    logger.add(
        log_file,
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="10 MB",
        retention="30 days"
    )
    
    # Add console handler for GitHub Actions
    logger.add(
        sys.stdout,
        level=log_level,
        format="::group::{level} - {time:HH:mm:ss}\n{message}\n::endgroup::",
        colorize=False
    )


def main() -> None:
    """Main execution function."""
    
    parser = argparse.ArgumentParser(description="Run scheduled note review job")
    parser.add_argument('--max-notes', type=int, default=5, help='Maximum notes per email')
    parser.add_argument('--force-send', action='store_true', help='Force send even if recently sent')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    parser.add_argument('--notes-dir', help='Override notes directory')
    
    args = parser.parse_args()
    
    setup_logging(args.log_level)
    
    logger.info("Starting scheduled note review job")
    logger.info(f"Max notes: {args.max_notes}")
    logger.info(f"Force send: {args.force_send}")
    
    try:
        # Initialize credential manager
        master_password = os.getenv('MASTER_PASSWORD')
        if not master_password:
            raise ValueError("MASTER_PASSWORD environment variable required")
        
        config_file = Path("config/encrypted_config.json")
        credential_manager = CredentialManager(config_file, master_password)
        
        # Load configuration
        _, app_config = credential_manager.load_credentials()
        notes_directory = Path(args.notes_dir or app_config.notes_directory)
        
        if not notes_directory.exists():
            logger.warning(f"Notes directory does not exist: {notes_directory}")
            logger.info("Creating empty notes directory for testing")
            notes_directory.mkdir(parents=True, exist_ok=True)
        
        # Create scheduler configuration
        schedule_config = ScheduleConfig(
            schedule_type=ScheduleType.DAILY,
            max_notes_per_email=args.max_notes,
            min_days_between_sends=0 if args.force_send else 7,
            max_retries=2,  # Reduce retries for GitHub Actions
            retry_delay_seconds=60  # Shorter delay for GitHub Actions
        )
        
        # Initialize scheduler
        scheduler = NoteScheduler(
            config=schedule_config,
            notes_directory=notes_directory,
            credential_manager=credential_manager
        )
        
        # Execute single job
        logger.info("Executing note review job...")
        job_id = scheduler.run_job_now()
        
        # Wait for job completion with timeout
        timeout = 600  # 10 minutes
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = scheduler.get_job_status()
            current_job = status.get('current_job')
            
            if not current_job:
                logger.info("Job completed")
                break
                
            if current_job['status'] in ['completed', 'failed', 'cancelled']:
                logger.info(f"Job finished with status: {current_job['status']}")
                if current_job['status'] == 'failed':
                    logger.error("Job failed - check logs for details")
                    sys.exit(1)
                break
                
            logger.info(f"Job status: {current_job['status']}")
            time.sleep(10)
        else:
            logger.error("Job timeout exceeded")
            sys.exit(1)
        
        # Log final statistics
        final_status = scheduler.get_job_status()
        stats = final_status.get('statistics', {})
        
        logger.info("Job execution completed successfully")
        logger.info(f"Total jobs: {stats.get('total_jobs', 0)}")
        logger.info(f"Success rate: {stats.get('success_rate', 0):.2%}")
        
        # Output GitHub Actions summary
        summary_file = os.getenv('GITHUB_STEP_SUMMARY')
        if summary_file:
            with open(summary_file, 'w') as f:
                f.write("# Note Review Job Summary\n\n")
                f.write(f"- **Status**: Completed\n")
                f.write(f"- **Job ID**: {job_id}\n")
                f.write(f"- **Max Notes**: {args.max_notes}\n")
                f.write(f"- **Force Send**: {args.force_send}\n")
                f.write(f"- **Success Rate**: {stats.get('success_rate', 0):.2%}\n")
        
    except Exception as e:
        logger.error(f"Job execution failed: {e}")
        
        # Output GitHub Actions error summary
        summary_file = os.getenv('GITHUB_STEP_SUMMARY')
        if summary_file:
            with open(summary_file, 'w') as f:
                f.write("# Note Review Job Summary\n\n")
                f.write(f"- **Status**: Failed\n")
                f.write(f"- **Error**: {str(e)}\n")
        
        sys.exit(1)


if __name__ == "__main__":
    main() 