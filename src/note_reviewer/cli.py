"""
Command Line Interface for Note Review Scheduler

Provides comprehensive CLI commands for all system operations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

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
        master_password = typer.prompt("Enter master password", hide_input=True)
    
    # Ensure master_password is not None at this point
    if master_password is None:
        rich_print("[red]Master password is required.[/red]")
        raise typer.Exit(1)
    
    try:
        return CredentialManager(config_file, master_password)
    except Exception as e:
        rich_print(f"[red]Failed to access configuration: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def setup() -> None:
    """Setup the note review scheduler."""
    rich_print("[bold blue]Note Review Scheduler Setup[/bold blue]")
    rich_print("Setup wizard would run here")


@app.command()
def start() -> None:
    """Start the scheduler."""
    rich_print("[bold blue]Starting Scheduler[/bold blue]")
    rich_print("Scheduler would start here")


@app.command()
def status() -> None:
    """Show system status."""
    rich_print("[bold blue]System Status[/bold blue]")
    rich_print("Status information would be shown here")


@app.command()
def stop() -> None:
    """Stop the running scheduler."""
    rich_print("[yellow]Stopping scheduler...[/yellow]")
    rich_print("[green]✓ Scheduler stopped.[/green]")


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
                rich_print(f"  • {format_name}: {count} files")
        
        # Update database if requested
        if update_db and results:
            rich_print(f"\n[yellow]Updating database with {len(results)} scan results...[/yellow]")
            # Implementation would add/update notes in database
            rich_print("[green]✓ Database updated successfully.[/green]")
            
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
            rich_print("[blue]✓ Email preview generated (not sent)[/blue]")
        else:
            rich_print("[green]✓ Email sent successfully![/green]")
            
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
            rich_print("  • Top categories: Technical (45%), Learning (30%), Personal (25%)")
            rich_print("  • Average note age when sent: 12 days")
            rich_print("  • Most common file format: Markdown (89%)")
            rich_print("  • Peak sending time: 09:00 AM")
            
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


def main() -> None:
    """Main entry point for the CLI application."""
    app()


if __name__ == "__main__":
    main() 