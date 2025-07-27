"""Email template management system."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass

from loguru import logger

from ..database.models import Note


class TemplateError(Exception):
    """Base exception for template operations."""
    pass


class TemplateNotFoundError(TemplateError):
    """Raised when a template file cannot be found."""
    pass


class TemplateRenderError(TemplateError):
    """Raised when template rendering fails."""
    pass


@dataclass(frozen=True)
class TemplateContext:
    """Context data for template rendering.
    
    Immutable dataclass containing all data needed for email template rendering.
    """
    notes: List[Note]
    recipient_email: str
    total_notes_count: int
    send_timestamp: datetime
    app_name: str = "Note Review Scheduler"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for template rendering.
        
        Returns:
            Dictionary representation of template context.
        """
        notes_data: List[Dict[str, Any]] = [self._note_to_dict(note) for note in self.notes]
        
        return {
            'notes': notes_data,
            'recipient_email': self.recipient_email,
            'total_notes_count': self.total_notes_count,
            'send_timestamp': self.send_timestamp,
            'send_date': self.send_timestamp.strftime('%Y-%m-%d'),
            'send_time': self.send_timestamp.strftime('%H:%M:%S'),
            'send_datetime_formatted': self.send_timestamp.strftime('%B %d, %Y at %I:%M %p'),
            'app_name': self.app_name,
            'notes_count': len(self.notes),
            'notes_html': self._generate_notes_html(notes_data),
            'notes_text': self._generate_notes_text(notes_data),
        }
    
    def _note_to_dict(self, note: Note) -> Dict[str, Any]:
        """Convert a Note to dictionary for template rendering.
        
        Args:
            note: Note object to convert.
            
        Returns:
            Dictionary representation of the note.
        """
        file_path: Path = Path(note.file_path)
        
        # Read file content safely
        content: str = ""
        try:
            content = file_path.read_text(encoding='utf-8', errors='replace')
        except Exception as e:
            logger.warning(f"Could not read note content from {file_path}: {e}")
            content = f"[Content could not be read: {e}]"
        
        return {
            'id': note.id,
            'file_path': str(note.file_path),
            'file_name': file_path.name,
            'file_stem': file_path.stem,
            'file_suffix': file_path.suffix,
            'content': content,
            'content_preview': self._create_content_preview(content),
            'content_hash': note.content_hash,
            'file_size': note.file_size,
            'file_size_formatted': self._format_file_size(note.file_size),
            'created_at': note.created_at,
            'modified_at': note.modified_at,
            'created_date': note.created_at.strftime('%Y-%m-%d'),
            'modified_date': note.modified_at.strftime('%Y-%m-%d'),
            'created_datetime_formatted': note.created_at.strftime('%B %d, %Y at %I:%M %p'),
            'modified_datetime_formatted': note.modified_at.strftime('%B %d, %Y at %I:%M %p'),
        }
    
    def _create_content_preview(self, content: str, max_length: int = 200) -> str:
        """Create a preview of note content.
        
        Args:
            content: Full note content.
            max_length: Maximum length of preview.
            
        Returns:
            Truncated content preview.
        """
        if not content.strip():
            return "[Empty note]"
        
        # Clean up whitespace
        clean_content: str = re.sub(r'\s+', ' ', content.strip())
        
        if len(clean_content) <= max_length:
            return clean_content
        
        # Truncate and add ellipsis
        truncated: str = clean_content[:max_length].strip()
        
        # Try to break at a word boundary
        last_space: int = truncated.rfind(' ')
        if last_space > max_length * 0.8:  # Only break if we don't lose too much
            truncated = truncated[:last_space]
        
        return truncated + "..."
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format.
        
        Args:
            size_bytes: File size in bytes.
            
        Returns:
            Formatted file size string.
        """
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
    
    def _generate_notes_html(self, notes_data: List[Dict[str, Any]]) -> str:
        """Generate HTML for all notes.
        
        Args:
            notes_data: List of note dictionaries.
            
        Returns:
            HTML string for all notes.
        """
        html_parts: List[str] = []
        
        for note_data in notes_data:
            # Escape HTML characters in content
            content: str = str(note_data.get('content', ''))
            content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            
            note_html: str = f"""
        <div class="note">
            <div class="note-header">
                <h2 class="note-title">{note_data.get('file_name', 'Unknown')}</h2>
                <div class="note-meta">
                    <span>Modified: {note_data.get('modified_date', 'Unknown')}</span>
                    <span>Size: {note_data.get('file_size_formatted', 'Unknown')}</span>
                </div>
            </div>
            <div class="note-content">{content}</div>
        </div>"""
            
            html_parts.append(note_html)
        
        return '\n'.join(html_parts)
    
    def _generate_notes_text(self, notes_data: List[Dict[str, Any]]) -> str:
        """Generate plain text for all notes.
        
        Args:
            notes_data: List of note dictionaries.
            
        Returns:
            Plain text string for all notes.
        """
        text_parts: List[str] = []
        
        for note_data in notes_data:
            content: str = str(note_data.get('content', ''))
            
            note_text: str = f"""
================================================================================
{note_data.get('file_name', 'Unknown')}
Modified: {note_data.get('modified_datetime_formatted', 'Unknown')} | {note_data.get('file_size_formatted', 'Unknown')}
================================================================================

{content}
"""
            
            text_parts.append(note_text)
        
        return '\n'.join(text_parts)


class SimpleTemplateEngine:
    """Simple template engine for basic variable substitution.
    
    Supports {{variable}} syntax with nested dictionary access using dot notation.
    """
    
    VARIABLE_PATTERN: re.Pattern[str] = re.compile(r'\{\{([^}]+)\}\}')
    
    def render(self, template: str, context: Dict[str, Any]) -> str:
        """Render template with context data.
        
        Args:
            template: Template string with {{variable}} placeholders.
            context: Dictionary of context data.
            
        Returns:
            Rendered template string.
            
        Raises:
            TemplateRenderError: If rendering fails.
        """
        try:
            def replace_variable(match: re.Match[str]) -> str:
                variable_path: str = match.group(1).strip()
                value: Any = self._get_nested_value(context, variable_path)
                return str(value) if value is not None else f"{{{{ {variable_path} }}}}"
            
            rendered: str = self.VARIABLE_PATTERN.sub(replace_variable, template)
            return rendered
            
        except Exception as e:
            logger.error(f"Template rendering failed: {e}")
            raise TemplateRenderError(f"Failed to render template: {e}") from e
    
    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get value from nested dictionary using dot notation.
        
        Args:
            data: Dictionary to search in.
            path: Dot-separated path to value (e.g., 'notes.0.file_name').
            
        Returns:
            Value at the specified path, or None if not found.
        """
        try:
            current: Union[Dict[str, Any], List[Any], str, int, float, bool, None] = data
            
            for key in path.split('.'):
                if isinstance(current, dict):
                    # Type narrowing: current is confirmed to be a dict here
                    current = current.get(key)
                elif isinstance(current, list) and key.isdigit():
                    index: int = int(key)
                    current = current[index] if 0 <= index < len(current) else None
                else:
                    return None
                
                if current is None:
                    return None
            
            return current
            
        except (KeyError, IndexError, ValueError, TypeError):
            return None


class EmailTemplateManager:
    """Manager for email templates with fallback support."""
    
    def __init__(self, templates_dir: Optional[Path] = None) -> None:
        """Initialize template manager.
        
        Args:
            templates_dir: Directory containing template files. If None, uses built-in templates.
        """
        self.templates_dir: Optional[Path] = templates_dir
        self.engine: SimpleTemplateEngine = SimpleTemplateEngine()
        
        if templates_dir:
            logger.info(f"Email template manager initialized with custom templates: {templates_dir}")
        else:
            logger.info("Email template manager initialized with built-in templates")
    
    def render_email(
        self,
        template_name: str,
        context: TemplateContext,
        format_type: str = 'html'
    ) -> str:
        """Render email template with context data.
        
        Args:
            template_name: Name of the template to render.
            context: Template context data.
            format_type: Template format ('html' or 'text').
            
        Returns:
            Rendered email content.
            
        Raises:
            TemplateError: If template rendering fails.
        """
        if format_type not in ('html', 'text'):
            raise ValueError("Format type must be 'html' or 'text'")
        
        logger.debug(f"Rendering {format_type} email template: {template_name}")
        
        try:
            # Get template content
            template_content: str = self._load_template(template_name, format_type)
            
            # Render with context
            context_dict: Dict[str, Any] = context.to_dict()
            rendered: str = self.engine.render(template_content, context_dict)
            
            logger.debug(f"Successfully rendered {format_type} template: {template_name}")
            return rendered
            
        except Exception as e:
            logger.error(f"Failed to render {format_type} template {template_name}: {e}")
            # Return fallback template
            return self._get_fallback_template(context, format_type)
    
    def _load_template(self, template_name: str, format_type: str) -> str:
        """Load template content from file or built-in templates.
        
        Args:
            template_name: Name of the template.
            format_type: Template format ('html' or 'text').
            
        Returns:
            Template content string.
            
        Raises:
            TemplateNotFoundError: If template cannot be found.
        """
        # Try to load from custom templates directory
        if self.templates_dir:
            template_file: Path = self.templates_dir / f"{template_name}.{format_type}"
            if template_file.exists():
                try:
                    content: str = template_file.read_text(encoding='utf-8')
                    logger.debug(f"Loaded custom template: {template_file}")
                    return content
                except Exception as e:
                    logger.warning(f"Failed to read custom template {template_file}: {e}")
        
        # Fall back to built-in templates
        return self._get_builtin_template(template_name, format_type)
    
    def _get_builtin_template(self, template_name: str, format_type: str) -> str:
        """Get built-in template content.
        
        Args:
            template_name: Name of the template.
            format_type: Template format ('html' or 'text').
            
        Returns:
            Built-in template content.
            
        Raises:
            TemplateNotFoundError: If template is not available.
        """
        builtin_templates: Dict[str, Dict[str, str]] = {
            'notes_review': {
                'html': self._get_builtin_html_template(),
                'text': self._get_builtin_text_template()
            }
        }
        
        if template_name not in builtin_templates:
            raise TemplateNotFoundError(f"Template '{template_name}' not found")
        
        if format_type not in builtin_templates[template_name]:
            raise TemplateNotFoundError(f"Template '{template_name}' does not have '{format_type}' format")
        
        return builtin_templates[template_name][format_type]
    
    def _get_builtin_html_template(self) -> str:
        """Get built-in HTML email template.
        
        Returns:
            HTML template string.
        """
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{app_name}} - Note Review</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f8f9fa;
        }
        .container {
            background-color: white;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            border-bottom: 2px solid #e9ecef;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        .header h1 {
            color: #495057;
            margin: 0;
            font-size: 28px;
        }
        .header p {
            color: #6c757d;
            margin: 10px 0 0 0;
            font-size: 16px;
        }
        .note {
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 6px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .note-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }
        .note-title {
            font-size: 18px;
            font-weight: 600;
            color: #495057;
            margin: 0;
        }
        .note-meta {
            color: #6c757d;
            font-size: 14px;
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
        }
        .note-content {
            background-color: white;
            border: 1px solid #e9ecef;
            border-radius: 4px;
            padding: 15px;
            font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
            font-size: 14px;
            line-height: 1.5;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        .footer {
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e9ecef;
            color: #6c757d;
            font-size: 14px;
        }
        .stats {
            background-color: #e7f3ff;
            border: 1px solid #b3d9ff;
            border-radius: 6px;
            padding: 15px;
            margin-bottom: 30px;
            text-align: center;
        }
        .stats strong {
            color: #0056b3;
        }
        @media (max-width: 600px) {
            body {
                padding: 10px;
            }
            .container {
                padding: 20px;
            }
            .note-header {
                flex-direction: column;
                align-items: flex-start;
            }
            .note-meta {
                margin-top: 10px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{{app_name}}</h1>
            <p>Your scheduled note review for {{send_datetime_formatted}}</p>
        </div>
        
        <div class="stats">
            <strong>{{notes_count}}</strong> notes selected for review
        </div>
        
        {{notes_html}}
        
        <div class="footer">
            <p>Generated by {{app_name}} on {{send_datetime_formatted}}</p>
            <p>This email contains {{notes_count}} of your {{total_notes_count}} total notes.</p>
        </div>
    </div>
</body>
</html>
        """.strip()
    
    def _get_builtin_text_template(self) -> str:
        """Get built-in plain text email template.
        
        Returns:
            Plain text template string.
        """
        return """
{{app_name}} - Note Review
{{send_datetime_formatted}}

Hello! Here are {{notes_count}} notes selected for your review:

{{notes_text}}

--------------------------------------------------------------------------------
Generated by {{app_name}} on {{send_datetime_formatted}}
This email contains {{notes_count}} of your {{total_notes_count}} total notes.
        """.strip()
    
    def _get_fallback_template(self, context: TemplateContext, format_type: str) -> str:
        """Get fallback template when main template fails.
        
        Args:
            context: Template context data.
            format_type: Template format ('html' or 'text').
            
        Returns:
            Fallback template content.
        """
        if format_type == 'html':
            return self._create_simple_html_fallback(context)
        else:
            return self._create_simple_text_fallback(context)
    
    def _create_simple_html_fallback(self, context: TemplateContext) -> str:
        """Create simple HTML fallback template.
        
        Args:
            context: Template context data.
            
        Returns:
            Simple HTML email content.
        """
        html_parts: List[str] = [
            "<!DOCTYPE html><html><head><title>Note Review</title></head><body>",
            f"<h1>{context.app_name} - Note Review</h1>",
            f"<p>Date: {context.send_timestamp.strftime('%B %d, %Y at %I:%M %p')}</p>",
            f"<p>Notes for review: {len(context.notes)}</p>",
            "<hr>"
        ]
        
        for i, note in enumerate(context.notes, 1):
            file_path: Path = Path(note.file_path)
            html_parts.extend([
                f"<h2>{i}. {file_path.name}</h2>",
                f"<p>Modified: {note.modified_at.strftime('%Y-%m-%d %H:%M')}</p>",
                "<div style='background:#f5f5f5;padding:10px;margin:10px 0;'>",
                "<pre style='white-space:pre-wrap;'>",
            ])
            
            # Add content safely
            try:
                content: str = file_path.read_text(encoding='utf-8', errors='replace')
                # Escape HTML characters
                content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                html_parts.append(content)
            except Exception:
                html_parts.append("[Content could not be read]")
            
            html_parts.extend(["</pre>", "</div>", "<hr>"])
        
        html_parts.extend([
            f"<p><small>Generated by {context.app_name}</small></p>",
            "</body></html>"
        ])
        
        return "".join(html_parts)
    
    def _create_simple_text_fallback(self, context: TemplateContext) -> str:
        """Create simple text fallback template.
        
        Args:
            context: Template context data.
            
        Returns:
            Simple text email content.
        """
        text_parts: List[str] = [
            f"{context.app_name} - Note Review",
            f"Date: {context.send_timestamp.strftime('%B %d, %Y at %I:%M %p')}",
            f"Notes for review: {len(context.notes)}",
            "",
            "=" * 70,
            ""
        ]
        
        for i, note in enumerate(context.notes, 1):
            file_path: Path = Path(note.file_path)
            text_parts.extend([
                f"{i}. {file_path.name}",
                f"   Modified: {note.modified_at.strftime('%Y-%m-%d %H:%M')}",
                "",
            ])
            
            # Add content safely
            try:
                content: str = file_path.read_text(encoding='utf-8', errors='replace')
                text_parts.append(content)
            except Exception:
                text_parts.append("[Content could not be read]")
            
            text_parts.extend(["", "-" * 70, ""])
        
        text_parts.append(f"Generated by {context.app_name}")
        
        return "\n".join(text_parts)
    
    def create_custom_template_files(self, template_dir: Path) -> None:
        """Create example custom template files.
        
        Args:
            template_dir: Directory to create template files in.
        """
        template_dir.mkdir(parents=True, exist_ok=True)
        
        # Create HTML template
        html_file: Path = template_dir / "notes_review.html"
        html_file.write_text(self._get_builtin_html_template(), encoding='utf-8')
        
        # Create text template
        text_file: Path = template_dir / "notes_review.text"
        text_file.write_text(self._get_builtin_text_template(), encoding='utf-8')
        
        logger.info(f"Created custom template files in {template_dir}") 