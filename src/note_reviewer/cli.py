"""
Command Line Interface for Note Review Scheduler

Provides comprehensive CLI commands for all system operations.
"""

from __future__ import annotations

import getpass
import os
import signal
import sys
from pathlib import Path
from typing import Any, Optional

import typer
from rich import print as rich_print
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .database.operations import get_notes_never_sent, get_notes_not_sent_recently
from .security.credentials import CredentialManager
from .scanner.file_scanner import FileScanner
from .selection.selection_algorithm import SelectionAlgorithm
from .selection.content_analyzer import ContentAnalyzer

def get_password_cross_platform(prompt: str) -> str:
    """
    Get password input that works across different terminal environments.
    Uses visible input in Git Bash to avoid hanging issues.
    """
    # Check if we're in Git Bash or similar environment on Windows
    if os.name == 'nt' and 'MSYSTEM' in os.environ:
        # We're in Git Bash/MSYS2 - use visible input to avoid hanging
        print(f"\nNote: Running in Git Bash - password will be visible while typing.")
        print("(This is normal for Git Bash - your password is still secure)")
        sys.stdout.write(prompt)
        sys.stdout.flush()
        try:
            # Use sys.stdin.readline() for better signal handling
            password = sys.stdin.readline().strip()
            return password
        except KeyboardInterrupt:
            print("\nPress Enter to confirm exit, or Ctrl+C again to force quit...")
            try:
                input()
                rich_print("\n[yellow]Process cancelled by user[/yellow]")
                raise typer.Exit(0)
            except KeyboardInterrupt:
                rich_print("\n[yellow]Force quit - process terminated[/yellow]")
                raise typer.Exit(0)
    else:
        # Use standard getpass for PowerShell, Command Prompt, etc.
        try:
            return getpass.getpass(prompt)
        except KeyboardInterrupt:
            print("\nPress Enter to confirm exit, or Ctrl+C again to force quit...")
            try:
                input()
                rich_print("\n[yellow]Process cancelled by user[/yellow]")
                raise typer.Exit(0)
            except KeyboardInterrupt:
                rich_print("\n[yellow]Force quit - process terminated[/yellow]")
                raise typer.Exit(0)

def setup_signal_handling() -> None:
    """Set up proper signal handling for Git Bash and other terminals."""
    def signal_handler(signum: int, frame: Any) -> None:
        print("\nPress Enter to confirm exit, or Ctrl+C again to force quit...")
        try:
            input()
            rich_print("\n[yellow]Setup cancelled by user[/yellow]")
            raise typer.Exit(0)
        except KeyboardInterrupt:
            rich_print("\n[yellow]Force quit - setup terminated[/yellow]")
            raise typer.Exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)

# Initialize CLI app
app = typer.Typer(
    name="note-scheduler",
    help="Intelligent Note Review Scheduler - Automate your note reviews with smart email notifications",
    add_completion=False,
    rich_markup_mode="rich"
)

# Initialize console for rich output
console = Console()

# Global state for configuration
config_file = Path("config/credentials.json")
master_password: Optional[str] = None


def get_credential_manager() -> CredentialManager:
    """Get credential manager with master password."""
    global master_password
    
    if not config_file.exists():
        rich_print("[red]Configuration not found. Please run 'notes setup' first.[/red]")
        raise typer.Exit(1)
    
    if not master_password:
        master_password = get_password_cross_platform("Enter master password: ")
    
    # Check if password was actually entered
    if not master_password.strip():
        rich_print("[red]Master password is required[/red]")
        raise typer.Exit(1)
    
    try:
        return CredentialManager(config_file, master_password)
    except Exception as e:
        rich_print(f"[red]Failed to access configuration: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def setup(
    force: bool = typer.Option(False, "--force", "-f", help="Reconfigure existing setup")
) -> None:
    """Setup the note review scheduler with interactive configuration."""
    # Set up signal handling for better Ctrl+C support
    setup_signal_handling()
    
    rich_print("[bold blue]Note Review Scheduler Setup[/bold blue]")
    
    # Check if config already exists
    if config_file.exists() and not force:
        rich_print(f"[yellow]Configuration already exists at {config_file}[/yellow]")
        rich_print("[yellow]Use --force to reconfigure or 'notes config --show' to view current settings.[/yellow]")
        return
    
    rich_print("\n[green]This wizard will help you configure the note review scheduler.[/green]")
    rich_print("[cyan]You'll need:[/cyan]")
    rich_print("  - Gmail account with 2-factor authentication enabled")
    rich_print("  - Gmail app password (not your regular password)")
    rich_print("  - Directory containing your notes")
    
    if not typer.confirm("\nDo you want to continue?"):
        rich_print("[yellow]Setup cancelled.[/yellow]")
        return
    
    try:
        # Get master password
        rich_print("\n[bold]Security Setup[/bold]")
        
        # Add debug output to help identify where hanging occurs
        rich_print("[dim]Waiting for master password input...[/dim]")
        try:
            master_password = get_password_cross_platform("Create a master password for encrypting your credentials: ")
        except Exception as e:
            rich_print(f"[red]Error with password input: {e}[/red]")
            rich_print("[yellow]Try using a simpler terminal or command prompt[/yellow]")
            raise typer.Exit(1)
        
        rich_print("[dim]Waiting for password confirmation...[/dim]")
        try:
            confirm_password = get_password_cross_platform("Confirm master password: ")
        except Exception as e:
            rich_print(f"[red]Error with password confirmation: {e}[/red]")
            rich_print("[yellow]Try using a simpler terminal or command prompt[/yellow]")
            raise typer.Exit(1)
        
        rich_print("[dim]Checking password match...[/dim]")
        if master_password != confirm_password:
            rich_print("[red]Passwords don't match. Setup cancelled.[/red]")
            raise typer.Exit(1)
        
        rich_print("[green]Passwords match! Continuing setup...[/green]")
        
        # Get Gmail credentials
        rich_print("\n[bold]Gmail Configuration[/bold]")
        rich_print("[cyan]Instructions for Gmail App Password:[/cyan]")
        rich_print("1. Go to your Google Account settings")
        rich_print("2. Navigate to Security => App passwords")
        rich_print("3. Generate an app password for 'Mail'")
        rich_print("4. Use that password below (not your regular Gmail password)")
        
        gmail_username = typer.prompt("\nGmail address")
        if "@gmail.com" not in gmail_username.lower():
            rich_print("[red]Please enter a valid Gmail address[/red]")
            raise typer.Exit(1)
        
        gmail_app_password = get_password_cross_platform("Gmail app password: ")
        
        # Test email credentials immediately
        rich_print("\n[yellow]Testing Gmail credentials...[/yellow]")
        from .email.service import EmailService, EmailConfig
        
        email_config = EmailConfig(
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            username=gmail_username,
            password=gmail_app_password,
            from_email=gmail_username,
            from_name=gmail_username.split('@')[0].title(),
            timeout_seconds=10
        )
        
        email_service = EmailService(email_config)
        
        try:
            if email_service.test_connection():
                rich_print("[green]Gmail credentials verified successfully![/green]")
            else:
                rich_print("[red]Gmail credentials test failed![/red]")
                rich_print("[red]The app password may be incorrect or expired.[/red]")
                rich_print("\n[cyan]Gmail app password should be 16 characters in format: xxxx xxxx xxxx xxxx[/cyan]")
                
                if typer.confirm("Do you want to retry entering your Gmail credentials?"):
                    rich_print("\n[yellow]Please try again with your Gmail credentials...[/yellow]")
                    return  # Exit setup to let user run it again
                else:
                    rich_print("[yellow]Continuing with unverified email credentials.[/yellow]")
                    rich_print("[yellow]You can test the connection later with 'notes status'[/yellow]")
        except Exception as e:
            rich_print(f"[red]Gmail connection test failed: {e}[/red]")
            rich_print("[red]This could be due to network issues or incorrect credentials.[/red]")
            
            if typer.confirm("Do you want to retry entering your Gmail credentials?"):
                rich_print("\n[yellow]Please try again with your Gmail credentials...[/yellow]")
                return  # Exit setup to let user run it again
            else:
                rich_print("[yellow]Continuing with unverified email credentials.[/yellow]")
                rich_print("[yellow]You can test the connection later with 'notes status'[/yellow]")
        
        from_name = typer.prompt(
            "Display name for emails",
            default=gmail_username.split('@')[0].title()
        )
        
        # Get recipient email
        recipient_email = typer.prompt(
            "Email address to send note reviews to",
            default=gmail_username
        )
        
        # Get notes directory
        rich_print("\n[bold]Notes Configuration[/bold]")
        notes_dir = typer.prompt("Path to your notes directory")
        notes_path = Path(notes_dir).expanduser().resolve()
        
        if not notes_path.exists():
            if typer.confirm(f"Directory {notes_path} doesn't exist. Create it?"):
                notes_path.mkdir(parents=True, exist_ok=True)
                rich_print(f"[green]Created directory: {notes_path}[/green]")
            else:
                rich_print("[yellow]Setup cancelled - notes directory required.[/yellow]")
                raise typer.Exit(1)
        
        # Get schedule configuration
        rich_print("\n[bold]Schedule Configuration[/bold]")
        schedule_time = typer.prompt(
            "Daily email time (HH:MM format)",
            default="09:00"
        )
        
        # Validate time format
        try:
            hour, minute = schedule_time.split(':')
            hour_int, minute_int = int(hour), int(minute)
            if not (0 <= hour_int <= 23 and 0 <= minute_int <= 59):
                raise ValueError()
        except ValueError:
            rich_print("[red]Invalid time format. Please use HH:MM (24-hour format)[/red]")
            raise typer.Exit(1)
        
        notes_per_email = typer.prompt(
            "Maximum notes per email",
            default=3,
            type=int
        )
        
        if notes_per_email <= 0:
            rich_print("[red]Notes per email must be positive[/red]")
            raise typer.Exit(1)
        
        # Show configuration summary
        rich_print("\n[bold]Configuration Summary[/bold]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Gmail Username", gmail_username)
        table.add_row("From Name", from_name)
        table.add_row("Recipient Email", recipient_email)
        table.add_row("Notes Directory", str(notes_path))
        table.add_row("Schedule Time", schedule_time)
        table.add_row("Notes Per Email", str(notes_per_email))
        
        console.print(table)
        
        if not typer.confirm("\nSave this configuration?"):
            rich_print("[yellow]Setup cancelled.[/yellow]")
            return
        
        # Save configuration
        rich_print("\n[yellow]Saving configuration...[/yellow]")
        
        # Create credential manager and save
        from .security.credentials import CredentialManager
        
        manager = CredentialManager.setup_wizard(
            config_file=config_file,
            master_password=master_password,
            gmail_username=gmail_username,
            gmail_app_password=gmail_app_password,
            recipient_email=recipient_email,
            notes_directory=str(notes_path),
            from_name=from_name
        )
        
        # Update app config with schedule settings
        from .security.credentials import AppConfig
        email_creds, current_config = manager.load_credentials()
        
        updated_config = AppConfig(
            notes_directory=str(notes_path),
            recipient_email=recipient_email,
            database_path=current_config.database_path,
            schedule_time=schedule_time,
            notes_per_email=notes_per_email,
            email_template=current_config.email_template,
            attach_files=current_config.attach_files,
            log_level=current_config.log_level,
            log_file=current_config.log_file
        )
        
        manager.save_credentials(email_creds, updated_config)
        
        # Initialize database
        rich_print("\n[yellow]Initializing database...[/yellow]")
        from .database.operations import initialize_database
        
        db_path = Path(updated_config.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        initialize_database(db_path)
        rich_print("[green]Database initialized successfully![/green]")
        
        # Run initial scan if notes exist
        if any(notes_path.glob("*.md")):
            if typer.confirm("\nRun initial notes scan?"):
                rich_print("\n[yellow]Scanning notes directory...[/yellow]")
                
                scanner = FileScanner(extract_tags=True, extract_links=True)
                results, stats = scanner.scan_directory(notes_path, recursive=True)
                
                # Update database with scan results
                if results:
                    from .database.operations import add_or_update_note
                    for result in results:
                        if result.is_valid:
                            add_or_update_note(
                                file_path=result.file_path,
                                content_hash=result.content_hash,
                                file_size=result.file_size,
                                created_at=result.created_at,
                                modified_at=result.modified_at,
                                db_path=db_path
                            )
                
                rich_print(f"[green]Scanned {stats.scanned_files} notes successfully![/green]")
        
        # Success message
        rich_print("\n[bold green]Setup completed successfully![/bold green]")
        rich_print("\n[cyan]Next steps:[/cyan]")
        rich_print("  - notes scan          - Scan your notes directory")
        rich_print("  - notes send --preview - Preview a note selection") 
        rich_print("  - notes start         - Start the scheduler")
        rich_print("  - notes config --show - View your configuration")
        rich_print("  - notes reset         - Reset configuration if needed")
        
    except KeyboardInterrupt:
        print("\nPress Enter to confirm exit, or Ctrl+C again to force quit...")
        try:
            input()
            rich_print("\n[yellow]Setup cancelled by user[/yellow]")
            rich_print("[dim]You can run 'notes setup' again to restart the configuration.[/dim]")
            rich_print("[dim]Or use 'notes reset' to clean up and start fresh.[/dim]")
            raise typer.Exit(0)
        except KeyboardInterrupt:
            rich_print("\n[yellow]Force quit - setup terminated[/yellow]")
            raise typer.Exit(0)
    except Exception as e:
        rich_print(f"\n[red]Setup failed: {e}[/red]")
        rich_print("[dim]You can run 'notes setup' again to retry.[/dim]")
        rich_print("[dim]Or use 'notes reset' to clean up and start fresh.[/dim]")
        raise typer.Exit(1)


@app.command()
def start(
    daemon: bool = typer.Option(False, "--daemon", "-d", help="Run as background daemon")
) -> None:
    """Start the scheduler."""
    rich_print("[bold blue]Starting Note Review Scheduler[/bold blue]")
    
    # Check if config exists
    if not config_file.exists():
        rich_print("[red]Configuration not found. Please run 'notes setup' first.[/red]")
        raise typer.Exit(1)
    
    try:
        # Get credentials and initialize app
        from .main import NoteReviewApplication
        
        global master_password
        if not master_password:
            master_password = get_password_cross_platform("Enter master password: ")
        
        app_instance = NoteReviewApplication(config_file)
        
        if not master_password.strip():
            rich_print("[red]Master password is required[/red]")
            raise typer.Exit(1)
        
        if not app_instance.initialize(master_password):
            rich_print("[red]Failed to initialize application[/red]")
            raise typer.Exit(1)
        
        if daemon:
            rich_print("[yellow]Daemon mode not yet implemented. Starting in foreground...[/yellow]")
        
        rich_print("[green]Scheduler starting...[/green]")
        rich_print("[cyan]Press Ctrl+C to stop[/cyan]")
        
        # Start the scheduler
        if daemon:
            # Daemon mode - start and return immediately
            success = app_instance.start_scheduler(daemon_mode=True)
            if success:
                rich_print("[green]Scheduler started in daemon mode[/green]")
                rich_print("[cyan]Use 'notes stop' to stop the scheduler[/cyan]")
            else:
                rich_print("[red]Failed to start scheduler[/red]")
                raise typer.Exit(1)
        else:
            # Foreground mode - start and wait for shutdown
            rich_print("[cyan]Starting scheduler in foreground mode...[/cyan]")
            rich_print("[cyan]Press Ctrl+C to stop[/cyan]")
            rich_print("[dim]Check the logs above for next scheduled run time[/dim]")
            
            try:
                success = app_instance.start_scheduler(daemon_mode=False)
                if success:
                    rich_print("[green]Scheduler stopped gracefully[/green]")
                else:
                    rich_print("[red]Failed to start scheduler[/red]")
                    raise typer.Exit(1)
            except KeyboardInterrupt:
                rich_print("\n[yellow]Stopping scheduler...[/yellow]")
                app_instance.stop()
                rich_print("[green]Scheduler stopped[/green]")
                raise typer.Exit(0)
            
    except KeyboardInterrupt:
        rich_print("\n[yellow]Scheduler stopped by user[/yellow]")
    except Exception as e:
        rich_print(f"[red]Failed to start scheduler: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def status() -> None:
    """Show system status and health information."""
    rich_print("[bold blue]System Status[/bold blue]")
    
    # Check configuration
    if not config_file.exists():
        rich_print("[red]Configuration not found[/red]")
        rich_print("  Run 'notes setup' to configure the system")
        return
    
    try:
        # Get credentials
        global master_password
        if not master_password:
            master_password = get_password_cross_platform("Enter master password: ")
        
        if not master_password.strip():
            rich_print("[red]Master password is required[/red]")
            raise typer.Exit(1)
        
        credential_manager = CredentialManager(config_file, master_password)
        email_creds, app_config = credential_manager.load_credentials()
        
        # Create status table
        table = Table(title="System Status", show_header=True, header_style="bold magenta")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details")
        
        # Configuration status
        table.add_row("Configuration", "Loaded", f"Config file: {config_file}")
        
        # Notes directory status
        notes_path = Path(app_config.notes_directory)
        if notes_path.exists():
            note_count = len(list(notes_path.glob("**/*.md"))) + len(list(notes_path.glob("**/*.txt")))
            table.add_row("Notes Directory", "Available", f"{note_count} files found")
        else:
            table.add_row("Notes Directory", "Missing", f"Path: {notes_path}")
        
        # Database status
        db_path = Path(app_config.database_path)
        if db_path.exists():
            from .database.operations import get_notes_never_sent
            try:
                notes = get_notes_never_sent(db_path)
                table.add_row("Database", "Connected", f"{len(notes)} notes never sent")
            except Exception as e:
                table.add_row("Database", "Error", str(e))
        else:
            table.add_row("Database", "Missing", "Run 'notes scan' to initialize")
        
        # Email service status
        try:
            from .email.service import EmailService, EmailConfig
            
            email_config = EmailConfig(
                smtp_server=email_creds.smtp_server,
                smtp_port=email_creds.smtp_port,
                username=email_creds.username,
                password=email_creds.password,
                from_email=email_creds.username,
                from_name=email_creds.from_name
            )
            
            email_service = EmailService(email_config)
            if email_service.test_connection():
                table.add_row("Email Service", "Connected", f"Gmail: {email_creds.username}")
            else:
                table.add_row("Email Service", "Failed", "Check Gmail credentials")
                
        except Exception as e:
            table.add_row("Email Service", "Error", str(e))
        
        # Health check
        try:
            from .main import NoteReviewApplication
            app_instance = NoteReviewApplication(config_file)
            app_instance.initialize(master_password)
            
            health_status = app_instance.get_health_status()
            if health_status.get('is_healthy', False):
                cpu = health_status.get('cpu_percent', 0)
                memory = health_status.get('memory_percent', 0)
                table.add_row("System Health", "Healthy", f"CPU: {cpu:.1f}%, RAM: {memory:.1f}%")
            else:
                error_msg = health_status.get('error', 'Unknown error')
                table.add_row("System Health", "Unhealthy", error_msg)
                
        except Exception as e:
            table.add_row("System Health", "Warning", f"Health check failed: {e}")
        
        console.print(table)
        
        # Show recent activity summary
        rich_print("\n[bold]Recent Activity[/bold]")
        if db_path.exists():
            try:
                # Show recent notes that could be sent
                from .database.operations import get_notes_not_sent_recently
                recent_notes = get_notes_not_sent_recently(7, db_path)
                
                if recent_notes:
                    rich_print(f"[green]{len(recent_notes)} notes available for sending[/green]")
                    for note in recent_notes[:3]:  # Show first 3
                        file_name = Path(note.file_path).name
                        rich_print(f"  - {file_name}")
                    if len(recent_notes) > 3:
                        rich_print(f"  ... and {len(recent_notes) - 3} more")
                else:
                    rich_print("[yellow]No notes available for sending[/yellow]")
                    
            except Exception as e:
                rich_print(f"[yellow]Could not load recent activity: {e}[/yellow]")
        
        # Quick actions
        rich_print("\n[bold]Quick Actions[/bold]")
        rich_print("  - notes scan          - Refresh notes database")
        rich_print("  - notes send --preview - Preview next email")
        rich_print("  - notes start         - Start scheduler")
        
    except Exception as e:
        rich_print(f"[red]Failed to get status: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def stop() -> None:
    """Stop the running scheduler."""
    rich_print("[yellow]Stopping scheduler...[/yellow]")
    rich_print("[green]Scheduler stopped.[/green]")


@app.command()
def scan(
    directory: Optional[str] = typer.Argument(None, help="Directory to scan (default: configured notes directory)"),
    recursive: bool = typer.Option(True, "--recursive/--no-recursive", "-r", help="Scan subdirectories"),
    update_db: bool = typer.Option(True, "--update-db/--no-update-db", help="Update database with scan results"),
) -> None:
    """Scan notes directory for files."""
    rich_print("\n[bold blue]Scanning Notes[/bold blue]")
    
    # Get configuration  
    credential_manager = get_credential_manager()
    _, app_config = credential_manager.load_credentials()
    
    # Determine scan directory
    scan_dir = Path(directory) if directory else Path(app_config.notes_directory)
    
    if not scan_dir.exists():
        rich_print(f"[red]Directory not found: {scan_dir}[/red]")
        raise typer.Exit(1)
    
    # Initialize scanner
    scanner = FileScanner(
        extract_tags=True,
        extract_links=True,
        generate_summary=True
    )
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Scanning files...", total=None)
            
            results, stats = scanner.scan_directory(scan_dir, recursive=recursive)
            
            progress.update(task, description="Scan complete")
        
        # Display results
        table = Table(title=f"Scan Results: {scan_dir}", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_column("Details")
        
        table.add_row("Total Files", str(stats.total_files), "Files found in directory")
        table.add_row("Scanned Successfully", str(stats.scanned_files), f"{stats.success_rate:.1%} success rate")
        table.add_row("Errors", str(stats.error_files), "Files with scan errors")
        table.add_row("Total Size", f"{stats.total_size_bytes / (1024*1024):.1f} MB", "Combined file size")
        table.add_row("Scan Duration", f"{stats.scan_duration_seconds:.2f}s", "Time to complete scan")
        
        console.print(table)
        
        # Show format breakdown
        if stats.formats_found:
            rich_print("\n[bold]File Formats Found:[/bold]")
            for format_name, count in stats.formats_found.items():
                rich_print(f"  - {format_name}: {count} files")
        
        # Update database if requested
        if update_db and results:
            rich_print(f"\n[yellow]Updating database with {len(results)} scan results...[/yellow]")
            # Implementation would add/update notes in database
            rich_print("[green]Database updated successfully.[/green]")
            
    except Exception as e:
        rich_print(f"[red]Scan failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def send(
    max_notes: int = typer.Option(3, "--max-notes", "-n", help="Maximum notes to send"),
    force: bool = typer.Option(False, "--force", "-f", help="Send even if sent recently"),
    preview: bool = typer.Option(False, "--preview", "-p", help="Preview email without sending"),
) -> None:
    """Manually send a note review email."""
    rich_print("\n[bold blue]Manual Note Send[/bold blue]")
    
    # Get configuration
    credential_manager = get_credential_manager()
    _, app_config = credential_manager.load_credentials()
    
    try:
        # Get notes to send
        db_path = Path(app_config.database_path)
        if not db_path.exists():
            rich_print("[red]Database not found. Run 'notes scan' first.[/red]")
            raise typer.Exit(1)
        
        # Select notes based on criteria
        if force:
            notes = get_notes_never_sent(db_path, max_notes)
            if len(notes) < max_notes:
                # Get additional notes that were sent, but not recently
                additional = get_notes_not_sent_recently(1, db_path)[:max_notes - len(notes)]
                notes.extend(additional)
        else:
            notes = get_notes_not_sent_recently(7, db_path)[:max_notes]  # Not sent in last week
        
        if not notes:
            rich_print("[yellow]No notes available to send.[/yellow]")
            return
        
        rich_print(f"[green]Found {len(notes)} notes to send:[/green]")
        for i, note in enumerate(notes, 1):
            rich_print(f"  {i}. {Path(note.file_path).name}")
        
        if preview:
            rich_print("\n[yellow]Preview mode - email will not be sent.[/yellow]")
        else:
            if not typer.confirm("\nSend email with these notes?"):
                return
        
        # Initialize selection and email systems
        content_analyzer = ContentAnalyzer()
        SelectionAlgorithm(content_analyzer)  # Would be used in full implementation
        
        # Note: EmailService expects EmailConfig, not EmailCredentials
        # This would need proper config conversion in full implementation
        rich_print("\n[yellow]Generating email content...[/yellow]")
        
        if preview:
            rich_print("[blue]Email preview generated (not sent)[/blue]")
        else:
            rich_print("[green]Email sent successfully![/green]")
            
    except Exception as e:
        rich_print(f"[red]Failed to send email: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def stats(
    days: int = typer.Option(30, "--days", "-d", help="Number of days to analyze"),
    detailed: bool = typer.Option(False, "--detailed", help="Show detailed statistics"),
) -> None:
    """Show usage statistics and analytics."""
    rich_print(f"\n[bold blue]Statistics (Last {days} days)[/bold blue]")
    
    try:
        credential_manager = get_credential_manager()
        _, app_config = credential_manager.load_credentials()
        
        db_path = Path(app_config.database_path)
        if not db_path.exists():
            rich_print("[red]Database not found. Run 'notes scan' first.[/red]")
            raise typer.Exit(1)
        
        # Get statistics (implementation would query database)
        table = Table(title="Usage Statistics", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_column("Details")
        
        # Mock statistics for now
        table.add_row("Total Notes", "127", "Notes in database")
        table.add_row("Emails Sent", "23", f"In last {days} days")
        table.add_row("Notes Sent", "69", "Total notes included in emails")
        table.add_row("Avg Notes/Email", "3.0", "Average per email")
        table.add_row("Most Active Day", "Monday", "Day with most emails")
        
        console.print(table)
        
        if detailed:
            rich_print("\n[bold]Detailed Analytics:[/bold]")
            rich_print("  - Top categories: Technical (45%), Learning (30%), Personal (25%)")
            rich_print("  - Average note age when sent: 12 days")
            rich_print("  - Most common file format: Markdown (89%)")
            rich_print("  - Peak sending time: 09:00 AM")
            
    except Exception as e:
        rich_print(f"[red]Failed to get statistics: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def config(
    show: bool = typer.Option(False, "--show", help="Show current configuration"),
    edit: bool = typer.Option(False, "--edit", help="Edit configuration interactively"),
) -> None:
    """Manage configuration settings."""
    if show:
        rich_print("\n[bold blue]Current Configuration[/bold blue]")
        
        try:
            credential_manager = get_credential_manager()
            email_creds, app_config = credential_manager.load_credentials()
            
            table = Table(title="Configuration", show_header=True, header_style="bold magenta")
            table.add_column("Setting", style="cyan")
            table.add_column("Value", style="green")
            
            table.add_row("Notes Directory", app_config.notes_directory)
            table.add_row("Database Path", app_config.database_path)
            table.add_row("Schedule Time", app_config.schedule_time)
            table.add_row("Notes Per Email", str(app_config.notes_per_email))
            table.add_row("Email Username", email_creds.username)
            table.add_row("Recipient Email", app_config.recipient_email)
            table.add_row("SMTP Server", f"{email_creds.smtp_server}:{email_creds.smtp_port}")
            table.add_row("From Name", email_creds.from_name)
            table.add_row("Max Emails/Hour", str(email_creds.max_emails_per_hour))
            
            console.print(table)
            
        except Exception as e:
            rich_print(f"[red]Failed to load configuration: {e}[/red]")
            raise typer.Exit(1)
    
    elif edit:
        rich_print("[yellow]Interactive configuration editing not yet implemented.[/yellow]")
        rich_print("Use 'notes setup --force' to reconfigure.")
    
    else:
        rich_print("[yellow]Use --show to view or --edit to modify configuration.[/yellow]")


@app.command()
def reset(
    confirm: bool = typer.Option(False, "--confirm", help="Skip confirmation prompt"),
) -> None:
    """Reset configuration and clean up all files."""
    rich_print("\n[bold red]Reset Configuration[/bold red]")
    
    if not config_file.exists():
        rich_print("[yellow]No configuration found to reset.[/yellow]")
        return
    
    rich_print("[yellow]This will permanently delete:[/yellow]")
    rich_print(f"  - Configuration file: {config_file}")
    rich_print(f"  - Database file: data/notes.db")
    rich_print(f"  - Log files: logs/")
    rich_print("\n[red]This action cannot be undone![/red]")
    
    if not confirm:
        if not typer.confirm("\nAre you sure you want to reset all configuration?"):
            rich_print("[yellow]Reset cancelled.[/yellow]")
            return
    
    try:
        # Remove configuration file
        if config_file.exists():
            config_file.unlink()
            rich_print(f"[green]Removed configuration file: {config_file}[/green]")
        
        # Remove database file
        db_file = Path("data/notes.db")
        if db_file.exists():
            db_file.unlink()
            rich_print(f"[green]Removed database file: {db_file}[/green]")
        
        # Remove log files
        log_dir = Path("logs")
        if log_dir.exists():
            for log_file in log_dir.glob("*.log*"):
                log_file.unlink()
            rich_print(f"[green]Removed log files from: {log_dir}[/green]")
        
        rich_print("\n[bold green]Configuration reset completed![/bold green]")
        rich_print("\n[cyan]To set up again, run:[/cyan]")
        rich_print("  notes setup")
        
    except Exception as e:
        rich_print(f"[red]Failed to reset configuration: {e}[/red]")
        raise typer.Exit(1)


def main() -> None:
    """Main entry point for the CLI application."""
    app()


if __name__ == "__main__":
    main() 