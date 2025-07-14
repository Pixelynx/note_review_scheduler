"""
Monitoring and Health Check System for Note Review Scheduler

Provides comprehensive monitoring, health checks, and execution metrics.
"""

from __future__ import annotations

import os
import json
import time
from contextlib import nullcontext
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import psutil
from loguru import logger

# Runtime import
try:
    from ..config.logging_config import StructuredLogger, LoggingConfig
    has_structured_logger = True
except ImportError:
    logger.warning("StructuredLogger not available")
    has_structured_logger = False
    StructuredLogger = None
    LoggingConfig = None


@dataclass(frozen=True)
class SystemMetrics:
    """System resource metrics."""
    cpu_percent: float
    memory_percent: float  
    disk_usage_percent: float
    available_memory_gb: float
    disk_free_gb: float


@dataclass(frozen=True)
class HealthStatus:
    """Overall system health status."""
    is_healthy: bool
    timestamp: datetime
    system_metrics: SystemMetrics
    warnings: List[str]
    errors: List[str]


@dataclass
class ExecutionMetrics:
    """Execution and performance metrics."""
    total_jobs_run: int = 0
    successful_jobs: int = 0
    failed_jobs: int = 0
    
    @property
    def success_rate(self) -> float:
        """Calculate job success rate."""
        if self.total_jobs_run == 0:
            return 0.0
        return self.successful_jobs / self.total_jobs_run


class HealthMonitor:
    def __init__(self, credential_manager: Optional[Any] = None) -> None:
        """Initialize health monitor."""
        self.credential_manager = credential_manager
        self._execution_history: List[Dict[str, Any]] = []
        self.structured_logger: Optional[Any] = None
        
        if has_structured_logger and StructuredLogger is not None and LoggingConfig is not None:
            try:
                config = LoggingConfig()
                self.structured_logger = StructuredLogger(config)
                logger.info("StructuredLogger initialized successfully")
            except Exception as e:
                logger.warning(f"StructuredLogger initialization failed: {e}")
        else:
            logger.info("Using fallback logging")
            
        logger.info("HealthMonitor initialized")

    
    def get_system_metrics(self) -> SystemMetrics:
        """Get current system resource metrics."""
        try:
            # CPU and memory usage (use no interval to avoid hanging)
            cpu_percent = psutil.cpu_percent(interval=None)  # type: ignore
            memory = psutil.virtual_memory()  # type: ignore
            memory_percent = memory.percent  # type: ignore
            available_memory_gb = memory.available / (1024**3)  # type: ignore
            
            # Disk usage
            disk = psutil.disk_usage(os.getcwd() if os.name == 'nt' else '/')  # type: ignore
            disk_usage_percent = (disk.used / disk.total) * 100  # type: ignore
            disk_free_gb = disk.free / (1024**3)  # type: ignore
            
            return SystemMetrics(  # type: ignore
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                disk_usage_percent=disk_usage_percent,
                available_memory_gb=available_memory_gb,
                disk_free_gb=disk_free_gb
            )
            
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            raise
    
    def perform_health_check(self) -> HealthStatus:
        """Perform comprehensive health check."""
        logger.info("Performing health check")
        
        # Use structured logger if available, otherwise continue without it
        if self.structured_logger is not None:
            try:
                from ..config.logging_config import LoggedOperation
                context_manager = LoggedOperation(self.structured_logger, "health_check")
            except Exception as e:
                logger.warning(f"Failed to create log operation context: {e}")
                context_manager = nullcontext()
        else:
            context_manager = nullcontext()
        
        with context_manager:
            # Collect system metrics
            system_metrics = self.get_system_metrics()
            
            # Analyze health status
            warnings: List[str] = []
            errors: List[str] = []
            is_healthy: bool = True
            
            # System health checks
            if system_metrics.cpu_percent > 80:
                warnings.append(f"High CPU usage: {system_metrics.cpu_percent:.1f}%")
            
            if system_metrics.memory_percent > 85:
                warnings.append(f"High memory usage: {system_metrics.memory_percent:.1f}%")
            
            if system_metrics.disk_usage_percent > 90:
                errors.append(f"Critical disk usage: {system_metrics.disk_usage_percent:.1f}%")
                is_healthy = False
            elif system_metrics.disk_usage_percent > 80:
                warnings.append(f"High disk usage: {system_metrics.disk_usage_percent:.1f}%")
            
            if system_metrics.available_memory_gb < 1.0:
                warnings.append(f"Low available memory: {system_metrics.available_memory_gb:.1f} GB")
            
            # Database health check
            db_path = Path("data/notes_tracker.db")
            if not db_path.exists():
                warnings.append("Database file not found")
            
            # Final health determination
            if errors:
                is_healthy = False
            
            health_status = HealthStatus(
                is_healthy=is_healthy,
                timestamp=datetime.now(),
                system_metrics=system_metrics,
                warnings=warnings,
                errors=errors
            )
            
            logger.info(
                f"Health check completed - Status: {'HEALTHY' if is_healthy else 'UNHEALTHY'}",
                extra={
                    'is_healthy': is_healthy,
                    'warning_count': len(warnings),
                    'error_count': len(errors)
                }
            )
            
            return health_status
    
    def record_job_execution(
        self, 
        job_id: str, 
        success: bool, 
        duration_seconds: float
    ) -> None:
        """Record job execution for metrics."""
        execution_record: Dict[str, Any] = {
            'job_id': job_id,
            'timestamp': time.time(),
            'success': success,
            'duration': duration_seconds
        }
        
        self._execution_history.append(execution_record)
        
        # Keep only last 100 records
        if len(self._execution_history) > 100:
            self._execution_history = self._execution_history[-100:]
        
        logger.info(f"Recorded job execution: {job_id}", extra=execution_record)
    
    def export_health_report(self, format: str = "json") -> Union[str, Dict[str, Any]]:
        """Export comprehensive health report."""
        health_status = self.perform_health_check()
        
        if format.lower() == "json":
            # Convert to dict for JSON serialization
            report_dict: Dict[str, Any] = {
                'is_healthy': health_status.is_healthy,
                'timestamp': health_status.timestamp.isoformat(),
                'system_metrics': {
                    'cpu_percent': health_status.system_metrics.cpu_percent,
                    'memory_percent': health_status.system_metrics.memory_percent,
                    'disk_usage_percent': health_status.system_metrics.disk_usage_percent,
                    'available_memory_gb': health_status.system_metrics.available_memory_gb,
                    'disk_free_gb': health_status.system_metrics.disk_free_gb
                },
                'warnings': health_status.warnings,
                'errors': health_status.errors
            }
            return json.dumps(report_dict, indent=2)
        
        elif format.lower() == "dict":
            report_dict: Dict[str, Any] = {
                'is_healthy': health_status.is_healthy,
                'timestamp': health_status.timestamp.isoformat(),
                'system_metrics': health_status.system_metrics,
                'warnings': health_status.warnings,
                'errors': health_status.errors
            }
            return report_dict
        
        else:
            raise ValueError(f"Unsupported format: {format}") 