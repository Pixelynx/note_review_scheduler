"""Advanced email formatting with rich HTML, markdown conversion, and content organization."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Set, Any

from loguru import logger

from .selection_algorithm import NoteScore
from .content_analyzer import NoteImportance


@dataclass(frozen=True)
class NoteGroup:
    """Grouped notes by category for organized display."""
    category: str
    importance: NoteImportance
    notes: List[NoteScore]
    total_score: float
    
    def __post_init__(self) -> None:
        """Validate note group."""
        if not self.notes:
            raise ValueError("Note group cannot be empty")
        if len(self.category.strip()) == 0:
            raise ValueError("Category cannot be empty")


@dataclass(frozen=True)
class EmailContent:
    """Complete email content with metadata."""
    html_content: str
    plain_text_content: str
    subject: str
    note_count: int
    total_word_count: int
    categories: List[str]
    importance_summary: Dict[str, int]
    estimated_read_time_minutes: int
    
    def __post_init__(self) -> None:
        """Validate email content."""
        if not self.html_content.strip():
            raise ValueError("HTML content cannot be empty")
        if not self.plain_text_content.strip():
            raise ValueError("Plain text content cannot be empty")
        if not self.subject.strip():
            raise ValueError("Subject cannot be empty")


class EmailFormatter:
    """Advanced email formatter with rich HTML and intelligent content organization."""
    
    # Markdown patterns for conversion
    MARKDOWN_PATTERNS: Dict[str, Tuple[re.Pattern[str], str]] = {
        'bold': (re.compile(r'\*\*(.*?)\*\*'), r'<strong>\1</strong>'),
        'italic': (re.compile(r'\*(.*?)\*'), r'<em>\1</em>'),
        'code_inline': (re.compile(r'`([^`]+)`'), r'<code>\1</code>'),
        'code_block': (re.compile(r'```([\s\S]*?)```'), r'<pre><code>\1</code></pre>'),
        'header1': (re.compile(r'^# (.+)$', re.MULTILINE), r'<h1>\1</h1>'),
        'header2': (re.compile(r'^## (.+)$', re.MULTILINE), r'<h2>\1</h2>'),
        'header3': (re.compile(r'^### (.+)$', re.MULTILINE), r'<h3>\1</h3>'),
        'header4': (re.compile(r'^#### (.+)$', re.MULTILINE), r'<h4>\1</h4>'),
        'link': (re.compile(r'\[([^\]]+)\]\(([^)]+)\)'), r'<a href="\2">\1</a>'),
        'bullet': (re.compile(r'^[\s]*[-*+]\s+(.+)$', re.MULTILINE), r'<li>\1</li>'),
        'numbered': (re.compile(r'^[\s]*\d+\.\s+(.+)$', re.MULTILINE), r'<li>\1</li>'),
    }
    
    # Category classification patterns
    CATEGORY_PATTERNS: Dict[str, Set[str]] = {
        'Work': {'meeting', 'project', 'task', 'deadline', 'report', 'presentation', 'client'},
        'Personal': {'personal', 'life', 'family', 'health', 'hobby', 'travel', 'diary'},
        'Learning': {'learn', 'study', 'course', 'tutorial', 'research', 'book', 'article'},
        'Ideas': {'idea', 'concept', 'brainstorm', 'inspiration', 'creative', 'innovation'},
        'Technical': {'code', 'programming', 'software', 'tech', 'bug', 'feature', 'api'},
        'Planning': {'plan', 'goal', 'strategy', 'roadmap', 'timeline', 'schedule', 'future'}
    }
    
    def __init__(self) -> None:
        """Initialize email formatter."""
        logger.debug("Email formatter initialized")
    
    def format_email(
        self,
        selected_notes: List[NoteScore],
        template_name: str = "rich_review",
        include_toc: bool = False,  # Disable TOC by default for email compatibility
        max_preview_words: int = 50
    ) -> EmailContent:
        """Format selected notes into a rich email.
        
        Args:
            selected_notes: List of scored notes to include.
            template_name: Email template to use.
            include_toc: Whether to include table of contents.
            max_preview_words: Maximum words in note preview.
            
        Returns:
            Complete formatted email content.
        """
        if not selected_notes:
            raise ValueError("Cannot format email with no notes")
        
        logger.info(f"Formatting email with {len(selected_notes)} notes")
        
        # Categorize and group notes
        note_groups: List[NoteGroup] = self._categorize_notes(selected_notes)
        
        # Generate email subject
        subject: str = self._generate_subject(selected_notes, note_groups)
        
        # Create table of contents (only for text version if requested)
        toc_text: str = ""
        if include_toc:
            _, toc_text = self._generate_table_of_contents(note_groups)
        
        # Format note content
        notes_html: str = self._format_notes_html(note_groups, max_preview_words)
        notes_text: str = self._format_notes_text(note_groups, max_preview_words)
        
        # Generate email statistics
        stats: Dict[str, Any] = self._generate_email_stats(selected_notes)
        
        # Build complete email content (use simple template approach)
        html_content: str = self._build_simple_html_email(
            subject, notes_html, stats
        )
        
        plain_text_content: str = self._build_text_email(
            subject, toc_text, notes_text, stats
        )
        
        email_content: EmailContent = EmailContent(
            html_content=html_content,
            plain_text_content=plain_text_content,
            subject=subject,
            note_count=len(selected_notes),
            total_word_count=sum(note.content_metrics.word_count for note in selected_notes),
            categories=[group.category for group in note_groups],
            importance_summary=stats['importance_summary'],
            estimated_read_time_minutes=stats['estimated_read_time']
        )
        
        logger.info(f"Email formatted: {len(selected_notes)} notes, ~{stats['estimated_read_time']}min read")
        return email_content
    
    def _categorize_notes(self, notes: List[NoteScore]) -> List[NoteGroup]:
        """Categorize notes into logical groups.
        
        Args:
            notes: List of notes to categorize.
            
        Returns:
            List of categorized note groups.
        """
        # Group notes by detected categories
        category_groups: Dict[str, List[NoteScore]] = {}
        
        for note in notes:
            category: str = self._detect_note_category(note)
            if category not in category_groups:
                category_groups[category] = []
            category_groups[category].append(note)
        
        # Create note groups sorted by importance and score
        note_groups: List[NoteGroup] = []
        for category, category_notes in category_groups.items():
            # Sort notes within category by score
            sorted_notes: List[NoteScore] = sorted(
                category_notes, 
                key=lambda n: (n.content_metrics.importance_level.value, n.total_score), 
                reverse=True
            )
            
            # Determine group importance (highest in group)
            importance_order: Dict[NoteImportance, int] = {
                NoteImportance.CRITICAL: 0,
                NoteImportance.HIGH: 1,
                NoteImportance.MEDIUM: 2,
                NoteImportance.LOW: 3
            }
            group_importance: NoteImportance = min(
                (note.content_metrics.importance_level for note in sorted_notes),
                key=lambda x: importance_order[x]
            )
            
            total_score: float = sum(note.total_score for note in sorted_notes)
            
            note_groups.append(NoteGroup(
                category=category,
                importance=group_importance,
                notes=sorted_notes,
                total_score=total_score
            ))
        
        # Sort groups by importance and total score
        importance_order: Dict[NoteImportance, int] = {
            NoteImportance.CRITICAL: 0,
            NoteImportance.HIGH: 1,
            NoteImportance.MEDIUM: 2,
            NoteImportance.LOW: 3
        }
        
        return sorted(
            note_groups,
            key=lambda g: (importance_order[g.importance], -g.total_score)
        )
    
    def _detect_note_category(self, note: NoteScore) -> str:
        """Detect the category of a note based on content and path.
        
        Args:
            note: Note to categorize.
            
        Returns:
            Detected category name.
        """
        # Check file path for category hints
        file_path: str = note.file_path.lower()
        
        # Try to read content for analysis
        try:
            content: str = Path(note.file_path).read_text(encoding='utf-8', errors='ignore').lower()
        except Exception:
            content = ""
        
        combined_text: str = f"{file_path} {content}"
        
        # Score each category
        category_scores: Dict[str, int] = {}
        for category, keywords in self.CATEGORY_PATTERNS.items():
            score: int = sum(combined_text.count(keyword) for keyword in keywords)
            if score > 0:
                category_scores[category] = score
        
        # Return highest scoring category or default
        if category_scores:
            return max(category_scores.items(), key=lambda x: x[1])[0]
        
        return "General"
    
    def _generate_subject(
        self, 
        notes: List[NoteScore], 
        groups: List[NoteGroup]
    ) -> str:
        """Generate an intelligent email subject.
        
        Args:
            notes: List of selected notes.
            groups: Categorized note groups.
            
        Returns:
            Generated email subject.
        """
        date_str: str = datetime.now().strftime("%B %d")
        note_count: int = len(notes)
        
        # Analyze importance distribution
        critical_count: int = sum(
            1 for note in notes 
            if note.content_metrics.importance_level == NoteImportance.CRITICAL
        )
        high_count: int = sum(
            1 for note in notes 
            if note.content_metrics.importance_level == NoteImportance.HIGH
        )
        
        # Create subject based on content
        if critical_count > 0:
            subject: str = f"Critical Notes Review - {date_str} ({note_count} notes)"
        elif high_count > 0:
            subject: str = f"Important Notes Review - {date_str} ({note_count} notes)"
        else:
            subject: str = f"Note Review - {date_str} ({note_count} notes)"
        
        # Add category info if diverse
        if len(groups) > 1:
            top_categories: List[str] = [g.category for g in groups[:2]]
            subject += f" - {', '.join(top_categories)}"
            if len(groups) > 2:
                subject += f" & {len(groups) - 2} more"
        
        return subject
    
    def _generate_table_of_contents(
        self, 
        groups: List[NoteGroup]
    ) -> Tuple[str, str]:
        """Generate table of contents for email.
        
        Args:
            groups: Categorized note groups.
            
        Returns:
            Tuple of (HTML TOC, plain text TOC).
        """
        html_toc: str = '<div class="toc">\n<h2>Table of Contents</h2>\n<ul>\n'
        text_toc: str = "TABLE OF CONTENTS\n" + "=" * 25 + "\n\n"
        
        for i, group in enumerate(groups, 1):
            # Importance indicator
            importance_icon: str = {
                NoteImportance.CRITICAL: "[CRITICAL]",
                NoteImportance.HIGH: "[HIGH]", 
                NoteImportance.MEDIUM: "[MEDIUM]",
                NoteImportance.LOW: "[LOW]"
            }[group.importance]
            
            group_anchor: str = f"group-{i}"
            
            # HTML TOC entry
            html_toc += (
                f'  <li><a href="#{group_anchor}">'
                f'{importance_icon} {group.category} ({len(group.notes)} notes)</a></li>\n'
            )
            
            # Text TOC entry
            text_toc += f"{i}. {importance_icon} {group.category} ({len(group.notes)} notes)\n"
        
        html_toc += '</ul>\n</div>\n\n'
        text_toc += "\n"
        
        return html_toc, text_toc
    
    def _format_notes_html(
        self, 
        groups: List[NoteGroup], 
        max_preview_words: int
    ) -> str:
        """Format notes as rich HTML content.
        
        Args:
            groups: Categorized note groups.
            max_preview_words: Maximum words in preview.
            
        Returns:
            HTML formatted notes content.
        """
        html_content: str = ""
        
        for i, group in enumerate(groups, 1):
            # Group header
            importance_icon: str = {
                NoteImportance.CRITICAL: "[CRITICAL]",
                NoteImportance.HIGH: "[HIGH]",
                NoteImportance.MEDIUM: "[MEDIUM]", 
                NoteImportance.LOW: "[LOW]"
            }[group.importance]
            
            group_class: str = f"note-group importance-{group.importance.value.lower()}"
            
            html_content += (
                f'<div class="{group_class}" id="group-{i}">\n'
                f'<h2 class="group-header">{importance_icon} {group.category}</h2>\n'
            )
            
            # Notes in group
            for j, note in enumerate(group.notes, 1):
                note_content: str = self._format_single_note_html(note, max_preview_words)
                html_content += f'<div class="note" id="note-{i}-{j}">\n{note_content}\n</div>\n'
            
            html_content += '</div>\n\n'
        
        return html_content
    
    def _format_single_note_html(
        self, 
        note: NoteScore, 
        max_preview_words: int
    ) -> str:
        """Format a single note as HTML.
        
        Args:
            note: Note to format.
            max_preview_words: Maximum words in preview.
            
        Returns:
            HTML formatted note.
        """
        try:
            # Read note content
            content: str = Path(note.file_path).read_text(encoding='utf-8', errors='ignore')
            
            # Create preview
            preview: str = self._create_content_preview(content, max_preview_words)
            
            # Convert markdown to HTML
            html_preview: str = self._markdown_to_html(preview)
            
            # Note metadata
            file_name: str = Path(note.file_path).name
            word_count: int = note.content_metrics.word_count
            freshness: str = self._format_freshness(note.content_metrics.freshness_days)
            
            # Build note HTML
            note_html: str = f'''
            <div class="note-header">
                <h3 class="note-title">{html.escape(file_name)}</h3>
                <div class="note-metadata">
                    <span class="word-count">{word_count} words</span>
                    <span class="freshness">{freshness}</span>
                    <span class="score">Score: {note.total_score:.1f}</span>
                </div>
            </div>
            <div class="note-content">
                {html_preview}
            </div>
            '''
            
            return note_html
            
        except Exception as e:
            logger.error(f"Error formatting note {note.file_path}: {e}")
            return f'<div class="note-error">[ERROR] Error loading note: {html.escape(str(e))}</div>'
    
    def _format_notes_text(
        self, 
        groups: List[NoteGroup], 
        max_preview_words: int
    ) -> str:
        """Format notes as plain text content.
        
        Args:
            groups: Categorized note groups.
            max_preview_words: Maximum words in preview.
            
        Returns:
            Plain text formatted notes.
        """
        text_content: str = ""
        
        for i, group in enumerate(groups, 1):
            # Group header
            importance_icon: str = {
                NoteImportance.CRITICAL: "[CRITICAL]",
                NoteImportance.HIGH: "[HIGH]",
                NoteImportance.MEDIUM: "[MEDIUM]",
                NoteImportance.LOW: "[LOW]"
            }[group.importance]
            
            text_content += f"{i}. {importance_icon} {group.category.upper()}\n"
            text_content += "=" * (len(group.category) + 20) + "\n\n"
            
            # Notes in group
            for j, note in enumerate(group.notes, 1):
                note_content: str = self._format_single_note_text(note, max_preview_words)
                text_content += f"{i}.{j} {note_content}\n\n"
            
            text_content += "\n"
        
        return text_content
    
    def _format_single_note_text(
        self, 
        note: NoteScore, 
        max_preview_words: int
    ) -> str:
        """Format a single note as plain text.
        
        Args:
            note: Note to format.
            max_preview_words: Maximum words in preview.
            
        Returns:
            Plain text formatted note.
        """
        try:
            # Read note content
            content: str = Path(note.file_path).read_text(encoding='utf-8', errors='ignore')
            
            # Create preview
            preview: str = self._create_content_preview(content, max_preview_words)
            
            # Note metadata
            file_name: str = Path(note.file_path).name
            word_count: int = note.content_metrics.word_count
            freshness: str = self._format_freshness(note.content_metrics.freshness_days)
            
            # Build note text
            note_text: str = f"{file_name}\n"
            note_text += f"Words: {word_count} | {freshness} | Score: {note.total_score:.1f}\n"
            note_text += "-" * 50 + "\n"
            note_text += preview + "\n"
            
            return note_text
            
        except Exception as e:
            logger.error(f"Error formatting note {note.file_path}: {e}")
            return f"Error loading note: {str(e)}\n"
    
    def _create_content_preview(self, content: str, max_words: int) -> str:
        """Create a preview of note content.
        
        Args:
            content: Full note content.
            max_words: Maximum words in preview.
            
        Returns:
            Content preview.
        """
        words: List[str] = content.split()
        
        if len(words) <= max_words:
            return content
        
        preview_words: List[str] = words[:max_words]
        preview: str = " ".join(preview_words)
        
        return preview + "..."
    
    def _markdown_to_html(self, markdown_text: str) -> str:
        """Convert markdown text to HTML with email-safe styling.
        
        Args:
            markdown_text: Markdown formatted text.
            
        Returns:
            HTML formatted text safe for email.
        """
        html_text: str = html.escape(markdown_text)
        
        # Apply limited markdown patterns (avoid conflicting with email styles)
        # Only convert basic formatting, skip headers to prevent oversized text
        limited_patterns = {
            'bold': (re.compile(r'\*\*(.*?)\*\*'), r'<strong>\1</strong>'),
            'italic': (re.compile(r'\*(.*?)\*'), r'<em>\1</em>'),
            'code_inline': (re.compile(r'`([^`]+)`'), r'<code style="background-color: #f0f0f0; padding: 2px 4px; border-radius: 3px; font-family: monospace;">\1</code>'),
            'link': (re.compile(r'\[([^\]]+)\]\(([^)]+)\)'), r'<a href="\2">\1</a>'),
        }
        
        for _, (regex, replacement) in limited_patterns.items():
            html_text = regex.sub(replacement, html_text)
        
        # Handle lists more carefully
        lines = html_text.split('\n')
        processed_lines: List[str] = []
        in_list = False
        
        for line in lines:
            # Check for bullet points
            if re.match(r'^[\s]*[-*+]\s+', line):
                content = re.sub(r'^[\s]*[-*+]\s+', '', line)
                if not in_list:
                    processed_lines.append('<ul>')
                    in_list = True
                processed_lines.append(f'<li>{content}</li>')
            else:
                if in_list:
                    processed_lines.append('</ul>')
                    in_list = False
                # Convert line breaks to <br> for regular text
                if line.strip():
                    processed_lines.append(line + '<br>')
                else:
                    processed_lines.append('<br>')
        
        if in_list:
            processed_lines.append('</ul>')
        
        return '\n'.join(processed_lines)
    
    def _format_freshness(self, days: int) -> str:
        """Format freshness information.
        
        Args:
            days: Days since last modification.
            
        Returns:
            Formatted freshness string.
        """
        if days == 0:
            return "Today"
        elif days == 1:
            return "Yesterday"
        elif days <= 7:
            return f"{days} days ago"
        elif days <= 30:
            weeks: int = days // 7
            return f"{weeks} week{'s' if weeks > 1 else ''} ago"
        elif days <= 365:
            months: int = days // 30
            return f"{months} month{'s' if months > 1 else ''} ago"
        else:
            years: int = days // 365
            return f"{years} year{'s' if years > 1 else ''} ago"
    
    def _generate_email_stats(self, notes: List[NoteScore]) -> Dict[str, Any]:
        """Generate email statistics.
        
        Args:
            notes: List of notes to analyze.
            
        Returns:
            Dictionary of email statistics.
        """
        total_words: int = sum(note.content_metrics.word_count for note in notes)
        avg_score: float = sum(note.total_score for note in notes) / len(notes)
        
        # Importance distribution
        importance_counts: Dict[str, int] = {}
        for note in notes:
            importance: str = note.content_metrics.importance_level.value
            importance_counts[importance] = importance_counts.get(importance, 0) + 1
        
        # Estimated read time (average 200 words per minute)
        read_time: int = max(1, total_words // 200)
        
        return {
            'total_words': total_words,
            'avg_score': avg_score,
            'importance_summary': importance_counts,
            'estimated_read_time': read_time
        }
    
    def _build_html_email(
        self,
        subject: str,
        toc_html: str,
        notes_html: str,
        stats: Dict[str, Any],
        template_name: str
    ) -> str:
        """Build complete HTML email with styling.
        
        Args:
            subject: Email subject.
            toc_html: Table of contents HTML.
            notes_html: Notes content HTML.
            stats: Email statistics.
            template_name: Template name.
            
        Returns:
            Complete HTML email.
        """
        css_styles: str = self._get_email_css()
        current_date: str = datetime.now().strftime("%A, %B %d, %Y")
        
        html_email: str = f'''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{html.escape(subject)}</title>
            <style>{css_styles}</style>
        </head>
        <body>
            <div class="email-container">
                <header class="email-header">
                    <h1 class="email-title">{html.escape(subject)}</h1>
                    <div class="email-meta">
                        <p class="date">{current_date}</p>
                        <div class="stats">
                            <span class="stat">{stats['total_words']} words</span>
                            <span class="stat">~{stats['estimated_read_time']} min read</span>
                            <span class="stat">Avg score: {stats['avg_score']:.1f}</span>
                        </div>
                    </div>
                </header>
                
                {toc_html}
                
                <main class="email-content">
                    {notes_html}
                </main>
                
                <footer class="email-footer">
                    <p>Generated by Note Review Scheduler</p>
                    <div class="importance-summary">
                        <strong>Importance Distribution:</strong>
                        {self._format_importance_summary_html(stats['importance_summary'])}
                    </div>
                </footer>
            </div>
        </body>
        </html>
        '''
        
        return html_email
    
    def _build_text_email(
        self,
        subject: str,
        toc_text: str,
        notes_text: str,
        stats: Dict[str, Any]
    ) -> str:
        """Build complete plain text email.
        
        Args:
            subject: Email subject.
            toc_text: Table of contents text.
            notes_text: Notes content text.
            stats: Email statistics.
            
        Returns:
            Complete plain text email.
        """
        current_date: str = datetime.now().strftime("%A, %B %d, %Y")
        separator: str = "=" * 60
        
        text_email: str = f'''
{subject}
{separator}

{current_date}

SUMMARY:
- {stats['total_words']} total words
- ~{stats['estimated_read_time']} minute read
- Average score: {stats['avg_score']:.1f}

{toc_text}

{notes_text}

{separator}
Generated by Note Review Scheduler

IMPORTANCE DISTRIBUTION:
{self._format_importance_summary_text(stats['importance_summary'])}
        '''
        
        return text_email.strip()
    
    def _build_simple_html_email(
        self,
        subject: str,
        notes_html: str,
        stats: Dict[str, Any]
    ) -> str:
        """Build simple HTML email without complex styling.
        
        Args:
            subject: Email subject.
            notes_html: Notes content HTML.
            stats: Email statistics.
            
        Returns:
            Simple HTML email content.
        """
        current_date: str = datetime.now().strftime("%A, %B %d, %Y")
        
        # Simple, email-friendly HTML
        html_email: str = f'''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{html.escape(subject)}</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 700px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f8f9fa;
                }}
                .container {{
                    background-color: white;
                    padding: 30px;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .header {{
                    text-align: center;
                    border-bottom: 2px solid #e9ecef;
                    padding-bottom: 20px;
                    margin-bottom: 30px;
                }}
                .header h1 {{
                    color: #495057;
                    margin: 0;
                    font-size: 24px;
                }}
                .stats {{
                    background-color: #e7f3ff;
                    padding: 15px;
                    border-radius: 6px;
                    margin-bottom: 30px;
                    text-align: center;
                    font-size: 14px;
                }}
                .note-group {{
                    margin-bottom: 30px;
                }}
                .note {{
                    background-color: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 6px;
                    padding: 20px;
                    margin-bottom: 20px;
                }}
                .note-title {{
                    font-size: 16px;
                    font-weight: 600;
                    color: #495057;
                    margin: 0 0 10px 0;
                }}
                .note-meta {{
                    color: #6c757d;
                    font-size: 12px;
                    margin-bottom: 15px;
                }}
                .note-content {{
                    background-color: white;
                    padding: 15px;
                    border-radius: 4px;
                    font-size: 14px;
                    line-height: 1.6;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #e9ecef;
                    color: #6c757d;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{html.escape(subject)}</h1>
                    <p>{current_date}</p>
                </div>
                
                <div class="stats">
                    <strong>{stats['total_words']}</strong> words •
                    <strong>~{stats['estimated_read_time']}</strong> min read •
                    <strong>{stats['avg_score']:.1f}</strong> avg score
                </div>
                
                <div class="content">
                    {notes_html}
                </div>
                
                <div class="footer">
                    <p>Generated by Note Review Scheduler</p>
                </div>
            </div>
        </body>
        </html>
        '''
        
        return html_email.strip()
    
    def _get_email_css(self) -> str:
        """Get CSS styles for HTML email.
        
        Returns:
            CSS styles string.
        """
        return '''
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f8f9fa;
        }
        
        .email-container {
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }
        
        .email-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .email-title {
            margin: 0 0 15px 0;
            font-size: 28px;
            font-weight: 700;
        }
        
        .email-meta {
            opacity: 0.9;
        }
        
        .date {
            margin: 0 0 10px 0;
            font-size: 16px;
        }
        
        .stats {
            display: flex;
            justify-content: center;
            gap: 20px;
            flex-wrap: wrap;
        }
        
        .stat {
            background: rgba(255, 255, 255, 0.2);
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 14px;
        }
        
        .toc {
            background: #f8f9fa;
            margin: 0;
            padding: 25px;
            border-bottom: 2px solid #e9ecef;
        }
        
        .toc h2 {
            margin-top: 0;
            color: #495057;
            font-size: 20px;
        }
        
        .toc ul {
            list-style: none;
            padding: 0;
        }
        
        .toc li {
            padding: 8px 0;
            border-bottom: 1px solid #dee2e6;
        }
        
        .toc a {
            color: #007bff;
            text-decoration: none;
            font-weight: 500;
        }
        
        .toc a:hover {
            text-decoration: underline;
        }
        
        .email-content {
            padding: 30px;
        }
        
        .note-group {
            margin-bottom: 40px;
            border-radius: 8px;
            padding: 20px;
        }
        
        .importance-critical {
            background: #fff5f5;
            border-left: 4px solid #dc3545;
        }
        
        .importance-high {
            background: #fff8e1;
            border-left: 4px solid #ff9800;
        }
        
        .importance-medium {
            background: #f3e5f5;
            border-left: 4px solid #9c27b0;
        }
        
        .importance-low {
            background: #f5f5f5;
            border-left: 4px solid #6c757d;
        }
        
        .group-header {
            margin-top: 0;
            color: #495057;
            font-size: 24px;
            border-bottom: 2px solid #dee2e6;
            padding-bottom: 10px;
        }
        
        .note {
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin: 15px 0;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        
        .note-header {
            margin-bottom: 15px;
        }
        
        .note-title {
            margin: 0 0 8px 0;
            color: #343a40;
            font-size: 18px;
        }
        
        .note-metadata {
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            color: #6c757d;
            font-size: 14px;
        }
        
        .note-content {
            line-height: 1.7;
        }
        
        .note-content h1, .note-content h2, .note-content h3, .note-content h4 {
            color: #495057;
            margin-top: 20px;
            margin-bottom: 10px;
        }
        
        .note-content code {
            background: #f8f9fa;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 13px;
        }
        
        .note-content pre {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            overflow-x: auto;
            border-left: 3px solid #007bff;
        }
        
        .note-content ul, .note-content ol {
            padding-left: 25px;
        }
        
        .note-content a {
            color: #007bff;
            text-decoration: none;
        }
        
        .note-content a:hover {
            text-decoration: underline;
        }
        
        .email-footer {
            background: #f8f9fa;
            padding: 25px;
            text-align: center;
            color: #6c757d;
            border-top: 1px solid #dee2e6;
        }
        
        .importance-summary {
            margin-top: 15px;
            font-size: 14px;
        }
        
        .note-error {
            background: #f8d7da;
            color: #721c24;
            padding: 15px;
            border-radius: 6px;
            border: 1px solid #f5c6cb;
        }
        
        @media (max-width: 600px) {
            body {
                padding: 10px;
            }
            
            .email-header {
                padding: 20px;
            }
            
            .email-title {
                font-size: 22px;
            }
            
            .stats {
                flex-direction: column;
                align-items: center;
                gap: 10px;
            }
            
            .toc, .email-content {
                padding: 20px;
            }
            
            .note {
                padding: 15px;
            }
        }
        '''
    
    def _format_importance_summary_html(self, summary: Dict[str, int]) -> str:
        """Format importance summary as HTML.
        
        Args:
            summary: Importance count dictionary.
            
        Returns:
            HTML formatted importance summary.
        """
        if not summary:
            return "<span>No notes</span>"
        
        parts: List[str] = []
        icons: Dict[str, str] = {
            'CRITICAL': '[CRITICAL]',
            'HIGH': '[HIGH]', 
            'MEDIUM': '[MEDIUM]',
            'LOW': '[LOW]'
        }
        
        for importance, count in summary.items():
            icon: str = icons.get(importance, '[UNKNOWN]')
            parts.append(f'<span class="importance-item">{icon} {importance}: {count}</span>')
        
        return ' | '.join(parts)
    
    def _format_importance_summary_text(self, summary: Dict[str, int]) -> str:
        """Format importance summary as plain text.
        
        Args:
            summary: Importance count dictionary.
            
        Returns:
            Plain text importance summary.
        """
        if not summary:
            return "No notes"
        
        parts: List[str] = []
        for importance, count in summary.items():
            parts.append(f"- {importance}: {count}")
        
        return '\n'.join(parts) 