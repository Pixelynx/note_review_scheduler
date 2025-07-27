#!/usr/bin/env python3
"""
Health Check Script for Note Review Scheduler

Performs comprehensive health checks and outputs results in various formats
for monitoring, alerting, and GitHub Actions integration.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.note_reviewer.scheduler.monitor import HealthMonitor
from src.note_reviewer.security.credentials import CredentialManager
from loguru import logger


def setup_logging(log_level: str) -> None:
    """Setup logging for health check script."""
    logger.remove()
    
    # Add console handler
    logger.add(
        sys.stdout,
        level=log_level,
        format="{time:HH:mm:ss} | {level: <8} | {message}",
        colorize=True
    )


def output_github_format(health_status: Dict[str, Any]) -> None:
    """Output health status in GitHub Actions format."""
    is_healthy: bool = health_status['is_healthy']
    warnings: list[str] = health_status.get('warnings', [])
    errors: list[str] = health_status.get('errors', [])
    
    # Set job summary
    summary_file = os.getenv('GITHUB_STEP_SUMMARY')
    if summary_file:
        with open(summary_file, 'w') as f:
            f.write("# System Health Check\n\n")
            
            if is_healthy:
                f.write("## System Status: HEALTHY\n\n")
            else:
                f.write("## System Status: UNHEALTHY\n\n")
            
            # System metrics
            sys_metrics: Dict[str, Any] = health_status.get('system_metrics', {})
            f.write("### System Resources\n")
            f.write(f"- **CPU Usage**: {sys_metrics.get('cpu_percent', 0):.1f}%\n")
            f.write(f"- **Memory Usage**: {sys_metrics.get('memory_percent', 0):.1f}%\n")
            f.write(f"- **Disk Usage**: {sys_metrics.get('disk_usage_percent', 0):.1f}%\n")
            f.write(f"- **Available Memory**: {sys_metrics.get('available_memory_gb', 0):.1f} GB\n")
            f.write(f"- **Free Disk Space**: {sys_metrics.get('disk_free_gb', 0):.1f} GB\n\n")
            
            # Database metrics
            db_metrics: Dict[str, Any] = health_status.get('database_metrics', {})
            f.write("### Database Health\n")
            f.write(f"- **Accessible**: {'' if db_metrics.get('is_accessible') else ''}\n")
            f.write(f"- **File Size**: {db_metrics.get('file_size_mb', 0):.1f} MB\n")
            f.write(f"- **Tables**: {db_metrics.get('table_count', 0)}\n")
            f.write(f"- **Notes**: {db_metrics.get('note_count', 0)}\n")
            f.write(f"- **Send History**: {db_metrics.get('send_history_count', 0)}\n")
            
            backup_age = db_metrics.get('last_backup_age_hours')
            if backup_age is not None:
                f.write(f"- **Last Backup**: {backup_age:.1f} hours ago\n")
            else:
                f.write("- **Last Backup**: No backup found\n")
            f.write("\n")
            
            # Email metrics
            email_metrics: Dict[str, Any] = health_status.get('email_metrics', {})
            f.write("### Email Service\n")
            f.write(f"- **Configured**: {'' if email_metrics.get('is_configured') else ''}\n")
            f.write(f"- **Rate Limit Remaining**: {email_metrics.get('rate_limit_remaining', 0)}\n")
            
            connection_time: float = email_metrics.get('connection_test_ms', 0)
            if connection_time > 0:
                f.write(f"- **Connection Test**: {connection_time:.0f}ms\n")
            
            if email_metrics.get('last_send_error'):
                f.write(f"- **Last Error**: {email_metrics['last_send_error']}\n")
            f.write("\n")
            
            # Execution metrics
            exec_metrics: Dict[str, Any] = health_status.get('execution_metrics', {})
            f.write("### Job Execution\n")
            f.write(f"- **Total Jobs**: {exec_metrics.get('total_jobs_run', 0)}\n")
            f.write(f"- **Successful**: {exec_metrics.get('successful_jobs', 0)}\n")
            f.write(f"- **Failed**: {exec_metrics.get('failed_jobs', 0)}\n")
            f.write(f"- **Success Rate**: {exec_metrics.get('success_rate', 0):.1%}\n")
            f.write(f"- **Avg Duration**: {exec_metrics.get('average_execution_time_seconds', 0):.1f}s\n\n")
            
            # Warnings and errors
            if warnings:
                f.write("### Warnings\n")
                for warning in warnings:
                    f.write(f"- {warning}\n")
                f.write("\n")
            
            if errors:
                f.write("### Errors\n")
                for error in errors:
                    f.write(f"- {error}\n")
                f.write("\n")
    
    # Set GitHub Actions outputs
    print(f"::set-output name=is_healthy::{str(is_healthy).lower()}")
    print(f"::set-output name=warning_count::{len(warnings)}")
    print(f"::set-output name=error_count::{len(errors)}")
    
    # Set exit code based on health
    if not is_healthy:
        sys.exit(1)


def main() -> None:
    """Main health check execution."""
    parser = argparse.ArgumentParser(description="Perform comprehensive health check")
    parser.add_argument('--output-format', 
                       choices=['json', 'text', 'github'], 
                       default='text',
                       help='Output format')
    parser.add_argument('--log-level', 
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO',
                       help='Logging level')
    parser.add_argument('--include-credentials',
                       action='store_true',
                       help='Include credential checks (requires master password)')
    parser.add_argument('--output-file',
                       help='Write output to file instead of stdout')
    
    args = parser.parse_args()
    
    setup_logging(args.log_level)
    
    logger.info("Starting comprehensive health check")
    
    try:
        # Initialize health monitor
        credential_manager = None
        if args.include_credentials:
            master_password = os.getenv('MASTER_PASSWORD')
            if master_password:
                config_file = Path("config/encrypted_config.json")
                credential_manager = CredentialManager(config_file, master_password)
            else:
                logger.warning("MASTER_PASSWORD not provided, skipping credential checks")
        
        health_monitor = HealthMonitor(credential_manager)
        
        # Perform health check
        health_status = health_monitor.perform_health_check()
        
        # Convert to dict for output
        health_dict_result = health_monitor.export_health_report(format="dict")
        
        # Ensure we have a dict
        if isinstance(health_dict_result, dict):
            health_dict = health_dict_result
        else:
            logger.error("Unexpected health report format")
            sys.exit(1)
        
        # Output results
        if args.output_format == 'json':
            output = json.dumps(health_dict, indent=2)
            
        elif args.output_format == 'github':
            output_github_format(health_dict)
            return  # GitHub format handles its own output
            
        else:  # text format
            output = format_text_output(health_dict)
        
        # Write to file or stdout
        if args.output_file:
            with open(args.output_file, 'w') as f:
                f.write(output)
            logger.info(f"Health check results written to: {args.output_file}")
        else:
            print(output)
        
        # Exit with error code if unhealthy
        if not health_status.is_healthy:
            logger.error("Health check failed - system is unhealthy")
            sys.exit(1)
        else:
            logger.info("Health check passed - system is healthy")
        
    except Exception as e:
        logger.error(f"Health check execution failed: {e}")
        sys.exit(1)


def format_text_output(health_dict: Dict[str, Any]) -> str:
    """Format health status as human-readable text."""
    lines: list[str] = []
    
    # Header
    is_healthy: bool = health_dict['is_healthy']
    status = "HEALTHY" if is_healthy else "UNHEALTHY"
    lines.append(f"System Health Status: {status}")
    lines.append(f"Timestamp: {health_dict['timestamp']}")
    lines.append("=" * 60)
    
    # System metrics
    sys_metrics = health_dict.get('system_metrics')
    lines.append("\nSYSTEM RESOURCES:")
    
    # Handle both dict and dataclass formats
    if sys_metrics is not None:
        cpu_percent = getattr(sys_metrics, 'cpu_percent', sys_metrics.get('cpu_percent', 0))
        memory_percent = getattr(sys_metrics, 'memory_percent', sys_metrics.get('memory_percent', 0))
        disk_usage_percent = getattr(sys_metrics, 'disk_usage_percent', sys_metrics.get('disk_usage_percent', 0))
        available_memory_gb = getattr(sys_metrics, 'available_memory_gb', sys_metrics.get('available_memory_gb', 0))
        disk_free_gb = getattr(sys_metrics, 'disk_free_gb', sys_metrics.get('disk_free_gb', 0))
        
        lines.append(f"  CPU Usage:         {cpu_percent:.1f}%")
        lines.append(f"  Memory Usage:      {memory_percent:.1f}%")
        lines.append(f"  Disk Usage:        {disk_usage_percent:.1f}%")
        lines.append(f"  Available Memory:  {available_memory_gb:.1f} GB")
        lines.append(f"  Free Disk Space:   {disk_free_gb:.1f} GB")
    else:
        lines.append("  System metrics unavailable")
    
    # Database metrics
    db_metrics: Dict[str, Any] = health_dict.get('database_metrics', {})
    lines.append("\nDATABASE HEALTH:")
    lines.append(f"  Accessible:        {'Yes' if db_metrics.get('is_accessible') else 'No'}")
    lines.append(f"  File Size:         {db_metrics.get('file_size_mb', 0):.1f} MB")
    lines.append(f"  Tables:            {db_metrics.get('table_count', 0)}")
    lines.append(f"  Notes:             {db_metrics.get('note_count', 0)}")
    lines.append(f"  Send History:      {db_metrics.get('send_history_count', 0)}")
    lines.append(f"  Query Performance: {db_metrics.get('query_performance_ms', 0):.0f}ms")
    
    backup_age = db_metrics.get('last_backup_age_hours')
    if backup_age is not None:
        lines.append(f"  Last Backup:       {backup_age:.1f} hours ago")
    else:
        lines.append(f"  Last Backup:       No backup found")
    
    # Email metrics
    email_metrics: Dict[str, Any] = health_dict.get('email_metrics', {})
    lines.append("\nEMAIL SERVICE:")
    lines.append(f"  Configured:        {'Yes' if email_metrics.get('is_configured') else 'No'}")
    lines.append(f"  Rate Limit:        {email_metrics.get('rate_limit_remaining', 0)} remaining")
    
    connection_time: float = email_metrics.get('connection_test_ms', 0)
    if connection_time > 0:
        lines.append(f"  Connection Test:   {connection_time:.0f}ms")
    
    if email_metrics.get('last_send_error'):
        lines.append(f"  Last Error:        {email_metrics['last_send_error']}")
    
    # Execution metrics
    exec_metrics: Dict[str, Any] = health_dict.get('execution_metrics', {})
    lines.append("\nJOB EXECUTION:")
    lines.append(f"  Total Jobs:        {exec_metrics.get('total_jobs_run', 0)}")
    lines.append(f"  Successful:        {exec_metrics.get('successful_jobs', 0)}")
    lines.append(f"  Failed:            {exec_metrics.get('failed_jobs', 0)}")
    lines.append(f"  Success Rate:      {exec_metrics.get('success_rate', 0):.1%}")
    lines.append(f"  Avg Duration:      {exec_metrics.get('average_execution_time_seconds', 0):.1f}s")
    
    # Warnings and errors
    warnings: list[str] = health_dict.get('warnings', [])
    errors: list[str] = health_dict.get('errors', [])
    
    if warnings:
        lines.append("\nWARNINGS:")
        for warning in warnings:
            lines.append(f"  - {warning}")
    
    if errors:
        lines.append("\nERRORS:")
        for error in errors:
            lines.append(f"  - {error}")
    
    return "\n".join(lines)


if __name__ == "__main__":
    main() 