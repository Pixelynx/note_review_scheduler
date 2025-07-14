"""Logging configuration module with comprehensive structured logging support."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional, Union
from types import TracebackType
from datetime import datetime

from loguru import logger


@dataclass(frozen=True)
class LoggingConfig:
    """Configuration for logging system."""
    
    # File logging
    log_file: Path = Path("note_scheduler.log")
    log_level: str = "INFO"
    rotation_size: str = "10 MB"
    retention_count: int = 10
    compression: str = "zip"
    
    # Console logging
    console_enabled: bool = True
    console_level: str = "INFO"
    console_format: str = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    
    # File format
    file_format: str = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {process.id} | {thread.id} | {message} | {extra}"
    
    # Performance monitoring
    enable_performance_logging: bool = True
    slow_operation_threshold_seconds: float = 1.0
    
    # Error handling
    enable_error_context: bool = True
    max_traceback_depth: int = 10
    
    def __post_init__(self) -> None:
        """Validate logging configuration."""
        valid_levels: set[str] = {"TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"}
        
        if self.log_level.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {self.log_level}")
        if self.console_level.upper() not in valid_levels:
            raise ValueError(f"Invalid console log level: {self.console_level}")
        if self.retention_count < 1:
            raise ValueError("Retention count must be at least 1")
        if self.slow_operation_threshold_seconds <= 0:
            raise ValueError("Slow operation threshold must be positive")


class StructuredLogger:
    """Enhanced logger with structured logging and performance monitoring."""
    
    def __init__(self, config: LoggingConfig) -> None:
        """Initialize structured logger with configuration."""
        self.config: LoggingConfig = config
        self._setup_logger()
    
    def _setup_logger(self) -> None:
        """Setup loguru logger with configuration."""
        # Remove default handler
        logger.remove()
        
        # Add console handler if enabled
        if self.config.console_enabled:
            logger.add(
                sys.stderr,
                level=self.config.console_level,
                format=self.config.console_format,
                colorize=True,
                enqueue=True  # Thread-safe logging
            )
        
        # Add file handler
        logger.add(
            str(self.config.log_file),
            level=self.config.log_level,
            format=self.config.file_format,
            rotation=self.config.rotation_size,
            retention=self.config.retention_count,
            compression=self.config.compression,
            enqueue=True,
            serialize=False  # Keep human-readable format
        )
        
        # Add separate error handler if enabled
        if self.config.enable_error_context:
            logger.add(
                str(self.config.log_file.with_suffix('.error.log')),
                level="ERROR",
                format=self._get_error_format(),
                rotation=self.config.rotation_size,
                retention=self.config.retention_count,
                compression=self.config.compression,
                enqueue=True,
                backtrace=True,
                diagnose=True
            )
    
    def _get_error_format(self) -> str:
        """Get detailed error logging format."""
        return (
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | "
            "{process.id} | {thread.id} | {message}\n"
            "Exception: {exception}\n"
            "Extra: {extra}\n"
            "---"
        )
    
    def log_operation_start(self, operation: str, **context: Any) -> str:
        """Log the start of an operation and return operation ID.
        
        Args:
            operation: Name of the operation.
            **context: Additional context data.
            
        Returns:
            Operation ID for tracking.
        """
        operation_id: str = f"{operation}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        logger.info(
            f"Operation started: {operation}",
            operation_id=operation_id,
            operation=operation,
            start_time=datetime.now().isoformat(),
            **context
        )
        
        return operation_id
    
    def log_operation_end(
        self,
        operation_id: str,
        operation: str,
        success: bool = True,
        error: Optional[BaseException] = None,
        **context: Any
    ) -> None:
        """Log the end of an operation.
        
        Args:
            operation_id: Operation ID from log_operation_start.
            operation: Name of the operation.
            success: Whether operation was successful.
            error: BaseException if operation failed.
            **context: Additional context data.
        """
        end_time: datetime = datetime.now()
        
        log_data: Dict[str, Any] = {
            "operation_id": operation_id,
            "operation": operation,
            "success": success,
            "end_time": end_time.isoformat(),
            **context
        }
        
        if success:
            logger.success(f"Operation completed: {operation}", **log_data)
        else:
            logger.error(
                f"Operation failed: {operation}",
                error_type=type(error).__name__ if error else "Unknown",
                error_message=str(error) if error else "Unknown error",
                **log_data
            )
    
    def log_performance_metric(
        self,
        metric_name: str,
        value: Union[int, float],
        unit: str = "",
        **context: Any
    ) -> None:
        """Log a performance metric.
        
        Args:
            metric_name: Name of the metric.
            value: Metric value.
            unit: Unit of measurement.
            **context: Additional context data.
        """
        logger.info(
            f"Performance metric: {metric_name}",
            metric_name=metric_name,
            metric_value=value,
            metric_unit=unit,
            timestamp=datetime.now().isoformat(),
            **context
        )
        
        # Log warning for slow operations
        if (self.config.enable_performance_logging and 
            metric_name.endswith('_duration_seconds') and 
            value > self.config.slow_operation_threshold_seconds):
            
            logger.warning(
                f"Slow operation detected: {metric_name}",
                metric_name=metric_name,
                duration_seconds=value,
                threshold_seconds=self.config.slow_operation_threshold_seconds,
                **context
            )
    
    def log_database_operation(
        self,
        operation: str,
        table: str,
        affected_rows: int = 0,
        execution_time_ms: Optional[float] = None,
        **context: Any
    ) -> None:
        """Log database operations with structured data.
        
        Args:
            operation: Database operation (SELECT, INSERT, UPDATE, DELETE).
            table: Database table name.
            affected_rows: Number of affected rows.
            execution_time_ms: Execution time in milliseconds.
            **context: Additional context data.
        """
        logger.info(
            f"Database operation: {operation} on {table}",
            db_operation=operation,
            db_table=table,
            db_affected_rows=affected_rows,
            db_execution_time_ms=execution_time_ms,
            **context
        )
    
    def log_email_operation(
        self,
        operation: str,
        recipient: str,
        success: bool,
        notes_count: int = 0,
        error: Optional[str] = None,
        **context: Any
    ) -> None:
        """Log email operations with structured data.
        
        Args:
            operation: Email operation (send, test_connection, etc.).
            recipient: Email recipient.
            success: Whether operation was successful.
            notes_count: Number of notes in email.
            error: Error message if failed.
            **context: Additional context data.
        """
        log_level = logger.info if success else logger.error
        
        log_level(
            f"Email operation: {operation}",
            email_operation=operation,
            email_recipient=recipient,
            email_success=success,
            email_notes_count=notes_count,
            email_error=error,
            **context
        )
    
    def log_security_event(
        self,
        event_type: str,
        success: bool,
        details: Optional[str] = None,
        **context: Any
    ) -> None:
        """Log security-related events.
        
        Args:
            event_type: Type of security event.
            success: Whether event was successful.
            details: Additional details.
            **context: Additional context data.
        """
        log_level = logger.info if success else logger.warning
        
        log_level(
            f"Security event: {event_type}",
            security_event=event_type,
            security_success=success,
            security_details=details,
            timestamp=datetime.now().isoformat(),
            **context
        )


def setup_logging(config: Optional[LoggingConfig] = None) -> StructuredLogger:
    """Setup logging system with configuration.
    
    Args:
        config: Logging configuration. If None, uses default configuration.
        
    Returns:
        Configured StructuredLogger instance.
    """
    if config is None:
        config = LoggingConfig()
    
    # Ensure log directory exists
    config.log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Create and configure structured logger
    structured_logger: StructuredLogger = StructuredLogger(config)
    
    logger.info(
        "Logging system initialized",
        log_file=str(config.log_file),
        log_level=config.log_level,
        console_enabled=config.console_enabled,
        performance_monitoring=config.enable_performance_logging
    )
    
    return structured_logger


# Context managers for operation logging
class LoggedOperation:
    """Context manager for logging operations with automatic timing."""
    
    def __init__(
        self,
        structured_logger: StructuredLogger,
        operation_name: str,
        **context: Any
    ) -> None:
        """Initialize logged operation.
        
        Args:
            structured_logger: StructuredLogger instance.
            operation_name: Name of the operation.
            **context: Additional context data.
        """
        self.structured_logger: StructuredLogger = structured_logger
        self.operation_name: str = operation_name
        self.context: Dict[str, Any] = context
        self.operation_id: Optional[str] = None
        self.start_time: Optional[datetime] = None
    
    def __enter__(self) -> LoggedOperation:
        """Enter context and start logging operation."""
        self.start_time = datetime.now()
        self.operation_id = self.structured_logger.log_operation_start(
            self.operation_name,
            **self.context
        )
        return self
    
    def __exit__(
        self, 
        exc_type: Optional[type], 
        exc_val: Optional[BaseException], 
        _: Optional[TracebackType]
    ) -> None:
        """Exit context and log operation completion."""
        if self.start_time and self.operation_id:
            duration_seconds: float = (datetime.now() - self.start_time).total_seconds()
            
            # Log performance metric
            self.structured_logger.log_performance_metric(
                f"{self.operation_name}_duration_seconds",
                duration_seconds,
                "seconds",
                operation_id=self.operation_id
            )
            
            # Log operation end
            success: bool = exc_type is None
            self.structured_logger.log_operation_end(
                self.operation_id,
                self.operation_name,
                success=success,
                error=exc_val if exc_val else None,
                duration_seconds=duration_seconds,
                **self.context
            )


# Export the default logger instance for convenience
_default_structured_logger: Optional[StructuredLogger] = None

def get_logger() -> StructuredLogger:
    """Get the default structured logger instance.
    
    Returns:
        Default StructuredLogger instance.
    """
    global _default_structured_logger
    if _default_structured_logger is None:
        _default_structured_logger = setup_logging()
    return _default_structured_logger 