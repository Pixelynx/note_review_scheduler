"""Flexible text formatting system for email content with markdown cleaning and multiple styling options."""

from __future__ import annotations

import html
import re
from enum import Enum
from typing import Dict, List, Tuple, Pattern

from loguru import logger


class EmailFormatType(Enum):
    """Available email formatting styles."""
    PLAIN = "plain"
    BIONIC = "bionic"
    STYLED = "styled"
    
    @classmethod
    def from_string(cls, value: str) -> EmailFormatType:
        """Create EmailFormatType from string value."""
        try:
            return cls(value.lower())
        except ValueError:
            logger.warning(f"Unknown format type '{value}', defaulting to PLAIN")
            return cls.PLAIN


class MarkdownCleaner:
    """Cleans markdown formatting while preserving essential structure."""
    
    # Regex patterns for markdown elements to remove
    CLEANING_PATTERNS: Dict[str, Pattern[str]] = {
        # Headers (remove # symbols but keep text)
        'headers': re.compile(r'^#+\s+(.+)$', re.MULTILINE),
        
        # Bold formatting (remove ** or __ but keep text)
        'bold_asterisk': re.compile(r'\*\*(.*?)\*\*'),
        'bold_underscore': re.compile(r'__(.*?)__'),
        
        # Italic formatting (remove * or _ but keep text)
        'italic_asterisk': re.compile(r'(?<!\*)\*(?!\*)([^*]+)\*(?!\*)'),
        'italic_underscore': re.compile(r'(?<!_)_(?!_)([^_]+)_(?!_)'),
        
        # Code blocks (remove ``` but keep content)
        'code_block': re.compile(r'```[\w]*\n?(.*?)\n?```', re.DOTALL),
        
        # Inline code (remove ` but keep content)
        'code_inline': re.compile(r'`([^`]+)`'),
        
        # Links (extract text, remove URL)
        'links': re.compile(r'\[([^\]]+)\]\([^)]+\)'),
        
        # Images (remove completely)
        'images': re.compile(r'!\[([^\]]*)\]\([^)]+\)'),
        
        # Blockquotes (remove > but keep text)
        'blockquotes': re.compile(r'^>\s+(.+)$', re.MULTILINE),
        
        # Horizontal rules (remove completely)
        'horizontal_rules': re.compile(r'^[-*_]{3,}$', re.MULTILINE),
        
        # Strikethrough (remove ~~ but keep text)
        'strikethrough': re.compile(r'~~(.+?)~~'),
        
        # Tables (remove pipe formatting but keep content)
        'table_separators': re.compile(r'^\|?[-:\s|]+\|?$', re.MULTILINE),
        'table_pipes': re.compile(r'\|'),
    }
    
    # Patterns for lists to preserve
    LIST_PATTERNS: Dict[str, Pattern[str]] = {
        'bullet_list': re.compile(r'^(\s*)([-*+])\s+(.+)$', re.MULTILINE),
        'numbered_list': re.compile(r'^(\s*)(\d+\.)\s+(.+)$', re.MULTILINE),
    }
    
    @classmethod
    def clean_markdown(cls, text: str) -> str:
        """Clean markdown formatting from text while preserving lists and readability.
        
        Args:
            text: Raw markdown text to clean.
            
        Returns:
            Clean text with markdown formatting removed but lists preserved.
        """
        if not text or not text.strip():
            return text
        
        # Start with the original text
        cleaned_text: str = text
        
        # Apply cleaning patterns in order
        # Headers: Remove # symbols but keep text
        cleaned_text = cls.CLEANING_PATTERNS['headers'].sub(r'\1', cleaned_text)
        
        # Bold formatting: Remove ** and __ but keep text
        cleaned_text = cls.CLEANING_PATTERNS['bold_asterisk'].sub(r'\1', cleaned_text)
        cleaned_text = cls.CLEANING_PATTERNS['bold_underscore'].sub(r'\1', cleaned_text)
        
        # Italic formatting: Remove * and _ but keep text
        cleaned_text = cls.CLEANING_PATTERNS['italic_asterisk'].sub(r'\1', cleaned_text)
        cleaned_text = cls.CLEANING_PATTERNS['italic_underscore'].sub(r'\1', cleaned_text)
        
        # Code blocks: Remove ``` but keep content
        cleaned_text = cls.CLEANING_PATTERNS['code_block'].sub(r'\1', cleaned_text)
        
        # Inline code: Remove ` but keep content
        cleaned_text = cls.CLEANING_PATTERNS['code_inline'].sub(r'\1', cleaned_text)
        
        # Links: Extract text only, remove URL
        cleaned_text = cls.CLEANING_PATTERNS['links'].sub(r'\1', cleaned_text)
        
        # Images: Remove completely
        cleaned_text = cls.CLEANING_PATTERNS['images'].sub('', cleaned_text)
        
        # Blockquotes: Remove > but keep text
        cleaned_text = cls.CLEANING_PATTERNS['blockquotes'].sub(r'\1', cleaned_text)
        
        # Horizontal rules: Remove completely
        cleaned_text = cls.CLEANING_PATTERNS['horizontal_rules'].sub('', cleaned_text)
        
        # Strikethrough: Remove ~~ but keep text
        cleaned_text = cls.CLEANING_PATTERNS['strikethrough'].sub(r'\1', cleaned_text)
        
        # Tables: Clean pipe formatting but keep content
        cleaned_text = cls.CLEANING_PATTERNS['table_separators'].sub('', cleaned_text)
        cleaned_text = cls.CLEANING_PATTERNS['table_pipes'].sub(' ', cleaned_text)
        
        # Clean up extra whitespace and line breaks
        cleaned_text = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned_text)  # Multiple empty lines
        cleaned_text = re.sub(r'[ \t]+', ' ', cleaned_text)  # Multiple spaces/tabs
        cleaned_text = cleaned_text.strip()
        
        return cleaned_text
    
    @classmethod
    def extract_lists(cls, text: str) -> Tuple[List[str], str]:
        """Extract and preserve list items from text.
        
        Args:
            text: Text containing lists.
            
        Returns:
            Tuple of (list items, text with lists removed).
        """
        list_items: List[str] = []
        remaining_text: str = text
        
        # Extract bullet lists
        for match in cls.LIST_PATTERNS['bullet_list'].finditer(text):
            indent, marker, content = match.groups()
            list_items.append(f"{indent}{marker} {content}")
            remaining_text = remaining_text.replace(match.group(0), '', 1)
        
        # Extract numbered lists
        for match in cls.LIST_PATTERNS['numbered_list'].finditer(text):
            indent, marker, content = match.groups()
            list_items.append(f"{indent}{marker} {content}")
            remaining_text = remaining_text.replace(match.group(0), '', 1)
        
        return list_items, remaining_text


class TextFormatter:
    """Applies various formatting styles to cleaned text."""
    
    @staticmethod
    def format_plain(text: str) -> str:
        """Apply plain text formatting (no special styling - truly plain text).
        
        Args:
            text: Clean text to format.
            
        Returns:
            Plain text without HTML formatting.
        """
        if not text or not text.strip():
            return text
        
        # Return plain text without HTML escaping or conversion
        # This ensures truly plain text for attachments
        return text
    
    @staticmethod
    def format_bionic(text: str) -> str:
        """Apply bionic reading format (bold first half of words for ADHD focus).
        
        Args:
            text: Clean text to format.
            
        Returns:
            HTML with bionic reading formatting.
        """
        if not text or not text.strip():
            return text
        
        def bionic_word(word: str) -> str:
            """Apply bionic formatting to a single word."""
            # Handle punctuation and special characters
            word = word.strip()
            if not word:
                return word
            
            # Extract leading/trailing punctuation
            leading_punct = ''
            trailing_punct = ''
            
            # Leading punctuation
            while word and not word[0].isalnum():
                leading_punct += word[0]
                word = word[1:]
            
            # Trailing punctuation
            while word and not word[-1].isalnum():
                trailing_punct = word[-1] + trailing_punct
                word = word[:-1]
            
            # Apply bionic formatting if word has letters
            if word and any(c.isalpha() for c in word):
                if len(word) <= 2:
                    # Short words: bold first character
                    formatted = f"<strong>{word[0]}</strong>{word[1:]}"
                else:
                    # Longer words: bold first half
                    split_point = len(word) // 2
                    formatted = f"<strong>{word[:split_point]}</strong>{word[split_point:]}"
                
                return leading_punct + formatted + trailing_punct
            else:
                # Numbers or special characters - return as is
                return leading_punct + word + trailing_punct
        
        # Process text word by word
        words = text.split()
        formatted_words = [bionic_word(word) for word in words]
        formatted_text = ' '.join(formatted_words)
        
        # Convert line breaks to HTML
        formatted_text = formatted_text.replace('\n', '<br>')
        
        return formatted_text
    
    @staticmethod
    def format_styled(text: str) -> str:
        """Apply styled formatting with enhanced visual hierarchy.
        
        Args:
            text: Clean text to format.
            
        Returns:
            HTML with styled formatting.
        """
        if not text or not text.strip():
            return text
        
        # HTML escape the text first
        formatted_text: str = html.escape(text)
        
        # Split into paragraphs
        paragraphs = formatted_text.split('\n\n')
        styled_paragraphs: List[str] = []
        
        for paragraph in paragraphs:
            if not paragraph.strip():
                continue
            
            # Check if it's a single-line paragraph (might be a header)
            lines = paragraph.split('\n')
            if len(lines) == 1 and len(paragraph.strip()) < 80:
                # Short single line - style as header
                styled_paragraphs.append(
                    f'<p style="font-weight: 600; color: #2c3e50; margin-bottom: 10px; font-size: 18px;">{paragraph.strip()}</p>'
                )
            else:
                # Regular paragraph with enhanced styling
                styled_paragraphs.append(
                    f'<p style="line-height: 1.6; margin-bottom: 15px; color: #34495e;">{paragraph.replace(chr(10), "<br>")}</p>'
                )
        
        return '\n'.join(styled_paragraphs)
    
    @staticmethod
    def format_lists(list_items: List[str], format_type: EmailFormatType) -> str:
        """Format preserved list items according to the specified format type.
        
        Args:
            list_items: List of list items to format.
            format_type: Formatting style to apply.
            
        Returns:
            Formatted lists (HTML for bionic/styled, plain text for plain).
        """
        if not list_items:
            return ''
        
        # Group consecutive list items by type and indentation
        formatted_lists: List[str] = []
        current_list: List[str] = []
        current_list_type: str = ''
        current_indent: int = 0
        
        for item in list_items:
            # Parse list item
            match = re.match(r'^(\s*)([-*+]|\d+\.)\s+(.+)$', item)
            if not match:
                continue
            
            indent, marker, content = match.groups()
            indent_level = len(indent)
            list_type = 'ul' if marker in ['-', '*', '+'] else 'ol'
            
            # Check if we need to start a new list
            if list_type != current_list_type or indent_level != current_indent:
                # Close previous list if exists
                if current_list:
                    formatted_lists.append(TextFormatter._format_single_list(current_list, current_list_type, format_type))
                
                # Start new list
                current_list = [content]
                current_list_type = list_type
                current_indent = indent_level
            else:
                # Add to current list
                current_list.append(content)
        
        # Close final list
        if current_list:
            formatted_lists.append(TextFormatter._format_single_list(current_list, current_list_type, format_type))
        
        return '\n'.join(formatted_lists)
    
    @staticmethod
    def _format_single_list(items: List[str], list_type: str, format_type: EmailFormatType) -> str:
        """Format a single list with the specified format type.
        
        Args:
            items: List items to format.
            list_type: 'ul' or 'ol'.
            format_type: Formatting style to apply.
            
        Returns:
            Formatted list (HTML for bionic/styled, plain text for plain).
        """
        if not items:
            return ''
        
        if format_type == EmailFormatType.PLAIN:
            # Plain format: Return as plain text list
            formatted_items: List[str] = []
            for i, item in enumerate(items, 1):
                if list_type == 'ul':
                    formatted_items.append(f'• {item}')
                else:  # ol
                    formatted_items.append(f'{i}. {item}')
            return '\n'.join(formatted_items)
        else:
            # HTML format for bionic and styled
            formatted_items: List[str] = []
            for item in items:
                if format_type == EmailFormatType.BIONIC:
                    formatted_item = TextFormatter.format_bionic(item)
                else:  # STYLED
                    formatted_item = html.escape(item)
                
                formatted_items.append(f'<li style="margin-bottom: 5px;">{formatted_item}</li>')
            
            # Create the list HTML
            list_style = 'margin: 15px 0; padding-left: 20px; color: #34495e;' if format_type == EmailFormatType.STYLED else 'margin: 10px 0; padding-left: 20px;'
            
            return f'<{list_type} style="{list_style}">\n' + '\n'.join(formatted_items) + f'\n</{list_type}>'


class FlexibleTextFormatter:
    """Main interface for flexible text formatting with markdown cleaning."""
    
    def __init__(self, format_type: EmailFormatType = EmailFormatType.PLAIN) -> None:
        """Initialize formatter with specified format type.
        
        Args:
            format_type: Email formatting style to use.
        """
        self.format_type: EmailFormatType = format_type
        self.cleaner = MarkdownCleaner()
        self.formatter = TextFormatter()
        
        logger.debug(f"Initialized FlexibleTextFormatter with format: {format_type.value}")
    
    def format_text(self, text: str) -> str:
        """Format text using the complete processing pipeline.
        
        Args:
            text: Raw text (possibly with markdown) to format.
            
        Returns:
            Formatted text (HTML for bionic/styled, plain text for plain).
        """
        if not text or not text.strip():
            return text
        
        # Step 1: Clean markdown formatting
        cleaned_text = self.cleaner.clean_markdown(text)
        
        # Step 2: Extract and preserve lists
        list_items, text_without_lists = self.cleaner.extract_lists(cleaned_text)
        
        # Step 3: Apply formatting to main text
        if self.format_type == EmailFormatType.PLAIN:
            formatted_text = self.formatter.format_plain(text_without_lists)
        elif self.format_type == EmailFormatType.BIONIC:
            formatted_text = self.formatter.format_bionic(text_without_lists)
        else:  # STYLED
            formatted_text = self.formatter.format_styled(text_without_lists)
        
        # Step 4: Format lists
        formatted_lists = self.formatter.format_lists(list_items, self.format_type)
        
        # Step 5: Combine text and lists
        if formatted_lists:
            if formatted_text:
                # For plain format, use double newlines; for HTML formats, use HTML spacing
                separator = "\n\n" if self.format_type == EmailFormatType.PLAIN else "\n\n"
                return f"{formatted_text}{separator}{formatted_lists}"
            else:
                return formatted_lists
        else:
            return formatted_text
    
    def format_subject(self, subject: str) -> str:
        """Format email subject line (always plain formatting).
        
        Args:
            subject: Raw subject text.
            
        Returns:
            Clean subject text.
        """
        # Subjects are always plain text, just clean markdown
        cleaned_subject = self.cleaner.clean_markdown(subject)
        return cleaned_subject.replace('\n', ' ').strip()
    
    def set_format_type(self, format_type: EmailFormatType) -> None:
        """Change the formatting style.
        
        Args:
            format_type: New formatting style to use.
        """
        self.format_type = format_type
        logger.debug(f"Changed format type to: {format_type.value}") 