"""Email service module with Gmail SMTP support and security features."""

from __future__ import annotations

import smtplib
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Final, List
import ssl

from loguru import logger

from ..database.models import Note

# Type checking import to avoid circular imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..selection.text_formatter import FlexibleTextFormatter


class EmailError(Exception):
    """Base exception for email operations."""
    pass


class RateLimitError(EmailError):
    """Raised when email rate limit is exceeded."""
    pass


class AuthenticationError(EmailError):
    """Raised when email authentication fails."""
    pass


@dataclass(frozen=True)
class EmailConfig:
    """Configuration for email service.
    
    Immutable dataclass to prevent accidental mutation of sensitive data.
    """
    smtp_server: str
    smtp_port: int
    username: str
    password: str  # App password for Gmail
    from_email: str
    from_name: str
    max_emails_per_hour: int = 50  # Gmail limit
    retry_attempts: int = 3
    retry_delay_seconds: int = 5
    timeout_seconds: int = 30
    
    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if not self.smtp_server.strip():
            raise ValueError("SMTP server cannot be empty")
        if not (1 <= self.smtp_port <= 65535):
            raise ValueError("SMTP port must be between 1 and 65535")
        if not self.username.strip():
            raise ValueError("Username cannot be empty")
        if not self.password.strip():
            raise ValueError("Password cannot be empty")
        if not self.from_email.strip():
            raise ValueError("From email cannot be empty")
        if "@" not in self.from_email:
            raise ValueError("From email must be a valid email address")
        if self.max_emails_per_hour <= 0:
            raise ValueError("Max emails per hour must be positive")
        if self.retry_attempts < 0:
            raise ValueError("Retry attempts cannot be negative")
        if self.retry_delay_seconds <= 0:
            raise ValueError("Retry delay must be positive")
        if self.timeout_seconds <= 0:
            raise ValueError("Timeout must be positive")


@dataclass
class EmailRateTracker:
    """Tracks email sending rate to enforce limits."""
    sent_times: List[datetime]
    max_per_hour: int
    
    def __post_init__(self) -> None:
        """Initialize with empty sent times list."""
        if not hasattr(self, 'sent_times'):
            self.sent_times = []
    
    def can_send_email(self) -> bool:
        """Check if we can send another email without exceeding rate limit."""
        now: datetime = datetime.now()
        cutoff: datetime = now - timedelta(hours=1)
        
        # Remove old entries
        self.sent_times = [t for t in self.sent_times if t > cutoff]
        
        return len(self.sent_times) < self.max_per_hour
    
    def record_email_sent(self) -> None:
        """Record that an email was just sent."""
        self.sent_times.append(datetime.now())
        logger.debug(f"Email rate tracker: {len(self.sent_times)}/{self.max_per_hour} emails sent in last hour")


class EmailService:
    """Gmail SMTP email service with rate limiting and retry logic."""
    
    # Gmail SMTP settings
    GMAIL_SMTP_SERVER: Final[str] = "smtp.gmail.com"
    GMAIL_SMTP_PORT: Final[int] = 587
    
    def __init__(self, config: EmailConfig) -> None:
        """Initialize email service with configuration.
        
        Args:
            config: Email service configuration.
        """
        self.config: EmailConfig = config
        self.rate_tracker: EmailRateTracker = EmailRateTracker([], config.max_emails_per_hour)
        logger.info(f"Email service initialized for {config.from_email}")
    
    @classmethod
    def create_gmail_config(
        cls,
        username: str,
        app_password: str,
        from_name: str = "",
        max_emails_per_hour: int = 50
    ) -> EmailConfig:
        """Create a Gmail-specific email configuration.
        
        Args:
            username: Gmail username (email address).
            app_password: Gmail app password (not regular password).
            from_name: Display name for sender.
            max_emails_per_hour: Maximum emails to send per hour.
            
        Returns:
            Configured EmailConfig for Gmail.
            
        Raises:
            ValueError: If parameters are invalid.
        """
        if "@gmail.com" not in username.lower():
            raise ValueError("Username must be a Gmail address")
        
        from_name = from_name or username
        
        return EmailConfig(
            smtp_server=cls.GMAIL_SMTP_SERVER,
            smtp_port=cls.GMAIL_SMTP_PORT,
            username=username,
            password=app_password,
            from_email=username,
            from_name=from_name,
            max_emails_per_hour=max_emails_per_hour
        )
    
    def _create_connection(self) -> smtplib.SMTP:
        """Create and authenticate SMTP connection.
        
        Returns:
            Authenticated SMTP connection.
            
        Raises:
            AuthenticationError: If authentication fails.
            EmailError: If connection fails.
        """
        try:
            logger.debug(f"Connecting to SMTP server {self.config.smtp_server}:{self.config.smtp_port}")
            
            # Create connection with timeout
            server: smtplib.SMTP = smtplib.SMTP(
                self.config.smtp_server,
                self.config.smtp_port,
                timeout=self.config.timeout_seconds
            )
            
            # Enable security
            server.starttls(context=ssl.create_default_context())
            
            # Authenticate
            server.login(self.config.username, self.config.password)
            
            logger.debug("SMTP connection established and authenticated")
            return server
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            raise AuthenticationError(f"Email authentication failed: {e}") from e
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            raise EmailError(f"Email server error: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error connecting to email server: {e}")
            raise EmailError(f"Failed to connect to email server: {e}") from e
    
    def send_notes_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str,
        notes: List[Note],
        attach_files: bool = True,
        formatter: "FlexibleTextFormatter | None" = None,
        embed_in_body: bool = True
    ) -> bool:
        """Send email with note content and optional file attachments.
        
        Args:
            to_email: Recipient email address.
            subject: Email subject line.
            html_content: HTML version of email content.
            text_content: Plain text version of email content.
            notes: List of notes being sent.
            attach_files: Whether to attach actual note files.
            formatter: Optional text formatter for attachments.
            embed_in_body: If True, embed formatted content in email body.
            
        Returns:
            True if email sent successfully, False otherwise.
            
        Raises:
            RateLimitError: If rate limit would be exceeded.
            EmailError: If email sending fails.
        """
        # Check rate limit
        if not self.rate_tracker.can_send_email():
            raise RateLimitError(
                f"Rate limit exceeded: {self.rate_tracker.max_per_hour} emails per hour"
            )
        
        # Validate inputs
        if not to_email.strip() or "@" not in to_email:
            raise ValueError("Invalid recipient email address")
        if not subject.strip():
            raise ValueError("Email subject cannot be empty")
        if not html_content.strip() and not text_content.strip():
            raise ValueError("Email must have either HTML or text content")
        
        logger.info(f"Sending email to {to_email} with {len(notes)} notes")
        
        # If embedding in body, enhance email content with formatted notes
        if embed_in_body and formatter and notes:
            enhanced_html, enhanced_text = self._embed_formatted_notes_in_body(
                html_content, text_content, notes, formatter
            )
            html_content = enhanced_html
            text_content = enhanced_text
        
        # Attempt to send with retry logic
        last_exception: Exception | None = None
        
        for attempt in range(1, self.config.retry_attempts + 1):
            try:
                success: bool = self._attempt_send_email(
                    to_email, subject, html_content, text_content, notes, attach_files, formatter
                )
                
                if success:
                    self.rate_tracker.record_email_sent()
                    logger.info(f"Email sent successfully to {to_email} on attempt {attempt}")
                    return True
                    
            except Exception as e:
                last_exception = e
                logger.warning(f"Email send attempt {attempt} failed: {e}")
                
                if attempt < self.config.retry_attempts:
                    logger.info(f"Retrying in {self.config.retry_delay_seconds} seconds...")
                    time.sleep(self.config.retry_delay_seconds)
                else:
                    logger.error(f"All {self.config.retry_attempts} email send attempts failed")
        
        # All attempts failed
        if last_exception:
            raise EmailError(f"Failed to send email after {self.config.retry_attempts} attempts") from last_exception
        
        return False
    
    def _embed_formatted_notes_in_body(
        self, 
        html_content: str, 
        text_content: str, 
        notes: List[Note], 
        formatter: "FlexibleTextFormatter"
    ) -> tuple[str, str]:
        """Embed formatted note content directly in email body for better Gmail compatibility.
        
        Args:
            html_content: Original HTML email content.
            text_content: Original text email content.
            notes: Notes to embed.
            formatter: Text formatter to apply.
            
        Returns:
            Tuple of (enhanced_html_content, enhanced_text_content).
        """
        format_type = formatter.format_type.value
        
        # Generate embedded HTML content
        embedded_html_parts = [
            f'<div style="margin-top: 30px; border-top: 2px solid #e9ecef; padding-top: 20px;">',
            f'<h2 style="color: #495057; margin-bottom: 20px;">Formatted Notes ({format_type.title()})</h2>'
        ]
        
        # Generate embedded text content
        embedded_text_parts = [
            "\n" + "="*60,
            f"FORMATTED NOTES ({format_type.upper()})",
            "="*60 + "\n"
        ]
        
        for i, note in enumerate(notes, 1):
            try:
                file_path = Path(note.file_path)
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                
                # Format content
                formatted_content = formatter.format_text(content)
                
                # HTML version
                content_style = self._get_inline_content_styles(format_type)
                embedded_html_parts.extend([
                    f'<div style="margin-bottom: 30px; border: 1px solid #dee2e6; border-radius: 6px; padding: 20px;">',
                    f'<h3 style="margin: 0 0 15px 0; color: #343a40; font-size: 16px;">{i}. {file_path.name}</h3>',
                    f'<div style="{content_style}">{formatted_content}</div>',
                    '</div>'
                ])
                
                # Text version  
                embedded_text_parts.extend([
                    f"{i}. {file_path.name}",
                    "-" * 40,
                    formatted_content if format_type == 'plain' else content,  # Use plain content for text version
                    "-" * 40 + "\n"
                ])
                
            except Exception as e:
                logger.error(f"Error embedding note {note.file_path}: {e}")
                continue
        
        embedded_html_parts.append('</div>')
        
        # Combine original content with embedded notes
        enhanced_html = html_content + '\n'.join(embedded_html_parts)
        enhanced_text = text_content + '\n'.join(embedded_text_parts)
        
        return enhanced_html, enhanced_text
    
    def _attempt_send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str,
        notes: List[Note],
        attach_files: bool,
        formatter: "FlexibleTextFormatter | None"
    ) -> bool:
        """Single attempt to send email.
        
        Args:
            to_email: Recipient email address.
            subject: Email subject line.
            html_content: HTML version of email content.
            text_content: Plain text version of email content.
            notes: List of notes being sent.
            attach_files: Whether to attach actual note files.
            
        Returns:
            True if email sent successfully.
            
        Raises:
            EmailError: If email sending fails.
        """
        server: smtplib.SMTP | None = None
        
        try:
            # Create email message
            msg: MIMEMultipart = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.config.from_name} <{self.config.from_email}>"
            msg['To'] = to_email
            msg['Date'] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")
            
            # Add content
            if text_content.strip():
                text_part: MIMEText = MIMEText(text_content, 'plain', 'utf-8')
                msg.attach(text_part)
            
            if html_content.strip():
                html_part: MIMEText = MIMEText(html_content, 'html', 'utf-8')
                msg.attach(html_part)
            
            # Add file attachments if requested
            if attach_files:
                self._add_file_attachments(msg, notes, formatter)
            
            # Send email
            server = self._create_connection()
            text: str = msg.as_string()
            server.sendmail(self.config.from_email, [to_email], text)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            raise EmailError(f"Email sending failed: {e}") from e
        
        finally:
            if server:
                try:
                    server.quit()
                except Exception as e:
                    logger.warning(f"Error closing SMTP connection: {e}")
    
    def _add_file_attachments(self, msg: MIMEMultipart, notes: List[Note], formatter: "FlexibleTextFormatter | None") -> None:
        """Add note files as email attachments with format-appropriate content and extensions.
        
        Args:
            msg: Email message to add attachments to.
            notes: List of notes to attach.
            formatter: Optional text formatter to apply to attachment content. 
                      - Plain format: Creates plain text attachments (.txt)
                      - Bionic/Styled formats: Creates HTML attachments (.html) with complete document structure
            
        Raises:
            EmailError: If attachment fails.
        """
        for note in notes:
            try:
                file_path: Path = Path(note.file_path)
                
                if not file_path.exists():
                    logger.warning(f"Note file not found for attachment: {file_path}")
                    continue
                
                # Read file content
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Determine attachment filename and content based on format
                if formatter:
                    # Apply formatting to content
                    formatted_content = formatter.format_text(content)
                    format_type = formatter.format_type.value
                    
                    if format_type == 'plain':
                        # Plain format: Create plain text attachment
                        attachment: MIMEText = MIMEText(formatted_content, 'plain', 'utf-8')
                        # Keep original extension for plain text
                        attachment_filename = file_path.name
                    else:
                        # Bionic/Styled formats: Create HTML attachment with complete document
                        html_document = self._create_html_attachment_document(
                            formatted_content, file_path.name, format_type
                        )
                        attachment: MIMEText = MIMEText(html_document, 'html', 'utf-8')
                        # Change extension to .html for formatted content
                        attachment_filename = file_path.stem + '.html'
                    
                else:
                    # No formatter: Use original content as plain text
                    attachment: MIMEText = MIMEText(content, 'plain', 'utf-8')
                    attachment_filename = file_path.name
                
                # Add header with appropriate filename
                attachment.add_header(
                    'Content-Disposition',
                    f'attachment; filename="{attachment_filename}"'
                )
                
                msg.attach(attachment)
                logger.debug(f"Added attachment: {attachment_filename}")
                
            except Exception as e:
                logger.error(f"Failed to attach file {note.file_path}: {e}")
                # Continue with other attachments rather than failing completely
                continue
    
    def test_connection(self) -> bool:
        """Test email service connectivity and authentication.
        
        Returns:
            True if connection successful, False otherwise.
        """
        try:
            logger.info("Testing email service connection...")
            server: smtplib.SMTP = self._create_connection()
            server.quit()
            logger.info("Email service connection test successful")
            return True
            
        except Exception as e:
            logger.error(f"Email service connection test failed: {e}")
            return False
    
    def get_rate_limit_status(self) -> dict[str, int]:
        """Get current rate limiting status.
        
        Returns:
            Dictionary with rate limit information.
        """
        now: datetime = datetime.now()
        cutoff: datetime = now - timedelta(hours=1)
        recent_sends: List[datetime] = [t for t in self.rate_tracker.sent_times if t > cutoff]
        
        return {
            "emails_sent_last_hour": len(recent_sends),
            "max_emails_per_hour": self.rate_tracker.max_per_hour,
            "emails_remaining": max(0, self.rate_tracker.max_per_hour - len(recent_sends))
        } 

    def _create_html_attachment_document(self, formatted_content: str, original_filename: str, format_type: str) -> str:
        """Create a complete HTML document for email attachments with Gmail-friendly inline CSS.
        
        Args:
            formatted_content: The formatted text content (with HTML tags).
            original_filename: Original filename for title.
            format_type: Format type used (for CSS selection).
            
        Returns:
            Complete HTML document string with inline CSS for better Gmail compatibility.
        """
        # Extract base filename for title
        base_filename = Path(original_filename).stem.replace('-', ' ').replace('_', ' ').title()
        
        # Get format-specific inline styles
        content_style = self._get_inline_content_styles(format_type)
        
        html_document = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{base_filename}</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; line-height: 1.6; color: #333; background-color: #ffffff; padding: 20px; margin: 0;">
    <div style="max-width: 800px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1); padding: 40px;">
        <header style="border-bottom: 2px solid #e9ecef; padding-bottom: 20px; margin-bottom: 30px; text-align: center;">
            <h1 style="color: #2c3e50; font-size: 28px; font-weight: 700; margin: 0 0 10px 0;">{base_filename}</h1>
            <p style="color: #6c757d; font-size: 14px; font-style: italic; margin: 0;">Formatted with {format_type.upper()} styling</p>
        </header>
        
        <main style="{content_style}">
            {formatted_content}
        </main>
        
        <footer style="border-top: 1px solid #e9ecef; padding-top: 20px; text-align: center; color: #6c757d; font-size: 12px; margin-top: 40px;">
            <p style="margin: 0;">Generated by Note Review Scheduler</p>
        </footer>
    </div>
</body>
</html>'''
        
        return html_document
    
    def _get_inline_content_styles(self, format_type: str) -> str:
        """Get inline CSS styles for note content based on format type.
        
        Args:
            format_type: Format type (plain, bionic, styled).
            
        Returns:
            Inline CSS styles string for the content container.
        """
        base_style = "min-height: 200px; margin-bottom: 40px;"
        
        if format_type.lower() == 'bionic':
            return (base_style + " font-size: 18px; line-height: 1.8; letter-spacing: 0.02em; "
                   "background-color: #fafbfc; padding: 25px; border-radius: 6px; "
                   "border-left: 4px solid #007bff;")
        
        elif format_type.lower() == 'styled':
            return (base_style + " font-size: 16px; line-height: 1.7; color: #2d3748; "
                   "background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%); "
                   "border: 1px solid #e9ecef; border-radius: 8px; padding: 25px; "
                   "box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);")
        
        else:  # plain format
            return (base_style + " font-size: 16px; line-height: 1.6; color: #2d3748;")
    
    def _get_attachment_css_styles(self, format_type: str) -> str:
        """Get CSS styles for attachment HTML documents (fallback for older method).
        
        Note: This method is now deprecated in favor of inline styles for better Gmail compatibility.
        Keeping for backward compatibility.
        
        Args:
            format_type: Format type (plain, bionic, styled).
            
        Returns:
            CSS styles string.
        """
        # Simple fallback CSS for cases where the new inline method isn't used
        return '''
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; }
        .note-content { padding: 20px; }
        strong { font-weight: 700; color: #2c3e50; }
        '''