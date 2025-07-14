"""
Format-specific handlers for different note file types.

Provides specialized processing for Markdown, Org-mode, and other formats.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

from loguru import logger


@dataclass(frozen=True)
class ParsedContent:
    """Structured representation of parsed content."""
    title: Optional[str]
    headers: List[str]
    metadata: Dict[str, str]
    tags: Set[str]
    links: List[str]
    code_blocks: List[str]
    todo_items: List[str]
    raw_content: str


class FormatHandler(ABC):
    """Abstract base class for format handlers."""
    
    @abstractmethod
    def parse(self, content: str) -> ParsedContent:
        """Parse content and extract structured information."""
        pass
    
    @abstractmethod
    def get_format_name(self) -> str:
        """Get the format name this handler supports."""
        pass


class MarkdownHandler(FormatHandler):
    """Handler for Markdown files (.md, .markdown, etc.)"""
    
    def parse(self, content: str) -> ParsedContent:
        """Parse Markdown content and extract structured information."""
        logger.debug("Parsing Markdown content")
        
        title = self._extract_title(content)
        headers = self._extract_headers(content)
        metadata = self._extract_frontmatter(content)
        tags = self._extract_tags(content, metadata)
        links = self._extract_links(content)
        code_blocks = self._extract_code_blocks(content)
        todo_items = self._extract_todo_items(content)
        
        return ParsedContent(
            title=title, headers=headers, metadata=metadata,
            tags=tags, links=links, code_blocks=code_blocks,
            todo_items=todo_items, raw_content=content
        )
    
    def get_format_name(self) -> str:
        return "markdown"
    
    def _extract_title(self, content: str) -> Optional[str]:
        # Try YAML frontmatter title first
        frontmatter = re.search(r'^---\s*\n(.*?)\n---', content, re.DOTALL | re.MULTILINE)
        if frontmatter:
            title_match = re.search(r'^title:\s*["\']?(.*?)["\']?\s*$', frontmatter.group(1), re.MULTILINE)
            if title_match:
                return title_match.group(1).strip()
        
        # Fall back to first H1 header
        h1_match = re.search(r'^#\s+(.+)', content, re.MULTILINE)
        return h1_match.group(1).strip() if h1_match else None
    
    def _extract_headers(self, content: str) -> List[str]:
        headers: List[str] = []
        for match in re.finditer(r'^(#{1,6})\s+(.+)', content, re.MULTILINE):
            level = len(match.group(1))
            text = match.group(2).strip()
            headers.append(f"{'  ' * (level-1)}{text}")
        return headers
    
    def _extract_frontmatter(self, content: str) -> Dict[str, str]:
        metadata: Dict[str, str] = {}
        frontmatter = re.search(r'^---\s*\n(.*?)\n---', content, re.DOTALL | re.MULTILINE)
        if frontmatter:
            for line in frontmatter.group(1).split('\n'):
                if ':' in line and not line.strip().startswith('#'):
                    key, value = line.split(':', 1)
                    metadata[key.strip()] = value.strip().strip('"\'')
        return metadata
    
    def _extract_tags(self, content: str, metadata: Dict[str, str]) -> Set[str]:
        tags: Set[str] = set()
        
        # From YAML frontmatter
        if 'tags' in metadata:
            tag_value = metadata['tags']
            if tag_value.startswith('[') and tag_value.endswith(']'):
                tag_content = tag_value[1:-1]
                tag_list = [tag.strip().strip('"\'') for tag in tag_content.split(',')]
            else:
                tag_list = [tag.strip() for tag in tag_value.split(',')]
            tags.update(tag for tag in tag_list if tag)
        
        # From content
        hashtag_matches = re.findall(r'#(\w+)', content)
        tags.update(hashtag_matches)
        mention_matches = re.findall(r'@(\w+)', content)
        tags.update(mention_matches)
        return tags
    
    def _extract_links(self, content: str) -> List[str]:
        links: List[str] = []
        
        # [text](url)
        link_matches = re.findall(r'\[.*?\]\(([^)]+)\)', content)
        links.extend(link_matches)
        
        # ![alt](url)
        image_matches = re.findall(r'!\[.*?\]\(([^)]+)\)', content)
        links.extend(image_matches)
        
        # <url>
        angle_matches = re.findall(r'<(https?://[^>]+)>', content)
        links.extend(angle_matches)
        
        # bare URLs
        bare_matches = re.findall(r'(https?://[^\s\)>\]]+)', content)
        links.extend(bare_matches)
        
        return list(set(links))
    
    def _extract_code_blocks(self, content: str) -> List[str]:
        code_blocks: List[str] = []
        
        # Fenced code blocks
        fenced_matches = re.findall(r'```(?:[\w]*\n)?(.*?)```', content, re.DOTALL)
        code_blocks.extend(fenced_matches)
        
        # Indented code blocks
        indented_matches = re.findall(r'^(?: {4,}|\t+)(.+)$', content, re.MULTILINE)
        if indented_matches:
            code_blocks.append('\n'.join(indented_matches))
        
        return code_blocks
    
    def _extract_todo_items(self, content: str) -> List[str]:
        todo_items: List[str] = []
        
        # Checkbox items
        checkbox_matches = re.findall(r'^[\s]*[-*+]\s*\[[x\s]\]\s*(.+)', content, re.MULTILINE)
        todo_items.extend(checkbox_matches)
        
        # TODO/FIXME comments
        comment_matches = re.findall(r'(?:TODO|FIXME|HACK|NOTE):\s*(.+)', content, re.IGNORECASE)
        todo_items.extend(comment_matches)
        
        return todo_items


class OrgModeHandler(FormatHandler):
    """Handler for Org-mode files (.org)"""
    
    def parse(self, content: str) -> ParsedContent:
        logger.debug("Parsing Org-mode content")
        
        title = self._extract_title(content)
        headers = self._extract_headers(content)
        metadata = self._extract_metadata(content)
        tags = self._extract_tags(content, metadata)
        links = self._extract_links(content)
        code_blocks = self._extract_code_blocks(content)
        todo_items = self._extract_todo_items(content)
        
        return ParsedContent(
            title=title, headers=headers, metadata=metadata,
            tags=tags, links=links, code_blocks=code_blocks,
            todo_items=todo_items, raw_content=content
        )
    
    def get_format_name(self) -> str:
        return "org-mode"
    
    def _extract_title(self, content: str) -> Optional[str]:
        title_match = re.search(r'^\s*#\+TITLE:\s*(.+)', content, re.MULTILINE)
        if title_match:
            return title_match.group(1).strip()
        header_match = re.search(r'^\*+\s+(.+)', content, re.MULTILINE)
        return header_match.group(1).strip() if header_match else None
    
    def _extract_headers(self, content: str) -> List[str]:
        headers: List[str] = []
        for match in re.finditer(r'^(\*+)\s+(.+)', content, re.MULTILINE):
            level = len(match.group(1))
            text = match.group(2).strip()
            headers.append(f"{'  ' * (level-1)}{text}")
        return headers
    
    def _extract_metadata(self, content: str) -> Dict[str, str]:
        metadata: Dict[str, str] = {}
        for match in re.finditer(r'^\s*#\+(\w+):\s*(.+)', content, re.MULTILINE):
            metadata[match.group(1).lower()] = match.group(2).strip()
        return metadata
    
    def _extract_tags(self, content: str, metadata: Dict[str, str]) -> Set[str]:
        tags: Set[str] = set()
        if 'tags' in metadata:
            tags.update(metadata['tags'].split())
        
        inline_tag_matches = re.findall(r':(\w+):', content)
        tags.update(inline_tag_matches)
        
        return tags
    
    def _extract_links(self, content: str) -> List[str]:
        links: List[str] = []
        
        # [[url][text]]
        link_with_text_matches = re.findall(r'\[\[([^\]]+)\](?:\[[^\]]*\])?\]', content)
        links.extend(link_with_text_matches)
        
        # bare URLs
        bare_url_matches = re.findall(r'(https?://[^\s\]]+)', content)
        links.extend(bare_url_matches)
        
        return list(set(links))
    
    def _extract_code_blocks(self, content: str) -> List[str]:
        code_blocks: List[str] = []
        
        # #+BEGIN_SRC blocks
        src_matches = re.findall(r'#\+BEGIN_SRC.*?\n(.*?)#\+END_SRC', content, re.DOTALL | re.IGNORECASE)
        code_blocks.extend(src_matches)
        
        # #+BEGIN_EXAMPLE blocks
        example_matches = re.findall(r'#\+BEGIN_EXAMPLE.*?\n(.*?)#\+END_EXAMPLE', content, re.DOTALL | re.IGNORECASE)
        code_blocks.extend(example_matches)
        
        return code_blocks
    
    def _extract_todo_items(self, content: str) -> List[str]:
        todo_items: List[str] = []
        for match in re.finditer(r'^\*+\s+(TODO|DOING|WAITING|NEXT|SOMEDAY)\s+(.+)', content, re.MULTILINE):
            todo_items.append(f"{match.group(1)}: {match.group(2)}")
        return todo_items


class TextHandler(FormatHandler):
    """Handler for plain text files (.txt, .text)"""
    
    def parse(self, content: str) -> ParsedContent:
        logger.debug("Parsing plain text content")
        
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        title = lines[0] if lines else None
        headers = [line for line in lines if line.endswith(':')]
        metadata: Dict[str, str] = {}
        
        tags: Set[str] = set()
        hashtag_matches = re.findall(r'#(\w+)', content)
        tags.update(hashtag_matches)
        mention_matches = re.findall(r'@(\w+)', content)
        tags.update(mention_matches)
        
        bare_url_matches = re.findall(r'(https?://[^\s]+)', content)
        links = list(set(bare_url_matches))
        
        code_blocks: List[str] = []
        
        todo_items: List[str] = []
        
        # TODO/FIXME comments
        comment_matches = re.findall(r'^.*(?:TODO|FIXME|HACK|NOTE)[:]*\s*(.+)', content, re.MULTILINE | re.IGNORECASE)
        todo_items.extend(comment_matches)
        
        # Checkbox items
        checkbox_matches = re.findall(r'^\s*\[[x\s]\]\s*(.+)', content, re.MULTILINE)
        todo_items.extend(checkbox_matches)
        
        return ParsedContent(
            title=title, headers=headers, metadata=metadata,
            tags=tags, links=links, code_blocks=code_blocks,
            todo_items=todo_items, raw_content=content
        )
    
    def get_format_name(self) -> str:
        return "plain-text" 