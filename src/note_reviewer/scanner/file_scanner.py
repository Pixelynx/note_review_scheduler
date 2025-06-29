"""
Advanced File Scanner for Note Review Scheduler

Provides comprehensive file scanning with support for multiple formats,
content analysis, and metadata extraction.
"""

from __future__ import annotations

import hashlib
import mimetypes
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Union

from loguru import logger


@dataclass(frozen=True)
class ScanResult:
    """Result of scanning a single file."""
    file_path: Path
    content_hash: str
    file_size: int
    created_at: datetime
    modified_at: datetime
    file_format: str
    mime_type: Optional[str]
    encoding: str
    line_count: int
    word_count: int
    is_valid: bool
    error_message: Optional[str] = None
    tags: Set[str] = field(default_factory=lambda: set())
    links: List[str] = field(default_factory=lambda: [])
    summary: Optional[str] = None


@dataclass
class ScanStats:
    """Statistics from a scanning operation."""
    total_files: int = 0
    scanned_files: int = 0
    skipped_files: int = 0
    error_files: int = 0
    formats_found: Dict[str, int] = field(default_factory=lambda: {})
    total_size_bytes: int = 0
    scan_duration_seconds: float = 0.0
    
    @property
    def success_rate(self) -> float:
        """Calculate scan success rate."""
        if self.total_files == 0:
            return 0.0
        return self.scanned_files / self.total_files


class FileScanner:
    """Advanced file scanner with multi-format support."""
    
    # Supported file extensions and their formats
    SUPPORTED_FORMATS: Dict[str, str] = {
        '.md': 'markdown',
        '.markdown': 'markdown', 
        '.mdown': 'markdown',
        '.mkd': 'markdown',
        '.org': 'org-mode',
        '.txt': 'plain-text',
        '.text': 'plain-text',
        '.rst': 'restructured-text',
        '.asciidoc': 'asciidoc',
        '.adoc': 'asciidoc'
    }
    
    # File size limits (configurable)
    DEFAULT_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    DEFAULT_MIN_FILE_SIZE = 1  # 1 byte
    
    def __init__(
        self,
        max_file_size: int = DEFAULT_MAX_FILE_SIZE,
        min_file_size: int = DEFAULT_MIN_FILE_SIZE,
        allowed_formats: Optional[Set[str]] = None,
        follow_symlinks: bool = False,
        extract_tags: bool = True,
        extract_links: bool = True,
        generate_summary: bool = False
    ) -> None:
        """Initialize file scanner with configuration.
        
        Args:
            max_file_size: Maximum file size to scan in bytes
            min_file_size: Minimum file size to scan in bytes  
            allowed_formats: Set of allowed formats (None = all supported)
            follow_symlinks: Whether to follow symbolic links
            extract_tags: Whether to extract tags from content
            extract_links: Whether to extract links from content
            generate_summary: Whether to generate content summaries
        """
        self.max_file_size = max_file_size
        self.min_file_size = min_file_size
        self.allowed_formats = allowed_formats if allowed_formats is not None else set(self.SUPPORTED_FORMATS.values())
        self.follow_symlinks = follow_symlinks
        self.extract_tags = extract_tags
        self.extract_links = extract_links
        self.generate_summary = generate_summary
        
        logger.info(f"FileScanner initialized with {len(self.allowed_formats)} allowed formats")
    
    def scan_directory(
        self,
        directory: Union[str, Path],
        recursive: bool = True,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None
    ) -> tuple[List[ScanResult], ScanStats]:
        """Scan directory for supported note files.
        
        Args:
            directory: Directory path to scan
            recursive: Whether to scan subdirectories
            include_patterns: Glob patterns for files to include
            exclude_patterns: Glob patterns for files to exclude
            
        Returns:
            Tuple of (scan results, scan statistics)
        """
        start_time = datetime.now()
        directory = Path(directory)
        
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        if not directory.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {directory}")
        
        logger.info(f"Starting directory scan: {directory}")
        
        # Collect files to scan
        files_to_scan = self._collect_files(
            directory, recursive, include_patterns, exclude_patterns
        )
        
        # Initialize statistics
        stats = ScanStats(total_files=len(files_to_scan))
        results: List[ScanResult] = []
        
        # Scan each file
        for file_path in files_to_scan:
            try:
                result = self.scan_file(file_path)
                results.append(result)
                
                if result.is_valid:
                    stats.scanned_files += 1
                    stats.total_size_bytes += result.file_size
                    
                    # Update format statistics
                    if result.file_format in stats.formats_found:
                        stats.formats_found[result.file_format] += 1
                    else:
                        stats.formats_found[result.file_format] = 1
                else:
                    stats.error_files += 1
                    
            except Exception as e:
                logger.error(f"Error scanning {file_path}: {e}")
                stats.error_files += 1
                
                # Create error result
                error_result = ScanResult(
                    file_path=file_path,
                    content_hash="",
                    file_size=0,
                    created_at=datetime.now(),
                    modified_at=datetime.now(),
                    file_format="unknown",
                    mime_type=None,
                    encoding="unknown",
                    line_count=0,
                    word_count=0,
                    is_valid=False,
                    error_message=str(e)
                )
                results.append(error_result)
        
        # Finalize statistics
        stats.scan_duration_seconds = (datetime.now() - start_time).total_seconds()
        stats.skipped_files = stats.total_files - stats.scanned_files - stats.error_files
        
        logger.info(f"Directory scan completed - {stats.scanned_files}/{stats.total_files} files scanned successfully")
        return results, stats
    
    def scan_file(self, file_path: Union[str, Path]) -> ScanResult:
        """Scan a single file and extract metadata.
        
        Args:
            file_path: Path to file to scan
            
        Returns:
            ScanResult with file metadata and content analysis
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")
        
        # Check file size
        file_size = file_path.stat().st_size
        if file_size < self.min_file_size or file_size > self.max_file_size:
            raise ValueError(f"File size {file_size} bytes outside allowed range")
        
        # Determine file format
        file_format = self._get_file_format(file_path)
        if file_format not in self.allowed_formats:
            raise ValueError(f"File format '{file_format}' not allowed")
        
        try:
            # Read file content with encoding detection
            content, encoding = self._read_file_content(file_path)
            
            # Calculate content hash
            content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            
            # Basic content analysis
            lines = content.split('\n')
            words = content.split()
            
            # Get file timestamps
            stat = file_path.stat()
            # Use st_birthtime if available (recommended), fall back to st_ctime
            try:
                created_at = datetime.fromtimestamp(stat.st_birthtime)
            except AttributeError:
                # st_birthtime not available on this platform, use st_ctime
                created_at = datetime.fromtimestamp(stat.st_ctime) # type: ignore
            modified_at = datetime.fromtimestamp(stat.st_mtime)
            
            # Get MIME type
            mime_type, _ = mimetypes.guess_type(str(file_path))
            
            # Advanced content processing
            tags: Set[str] = set()
            links: List[str] = []
            summary: Optional[str] = None
            
            if self.extract_tags:
                tags = self._extract_tags(content, file_format)
            
            if self.extract_links:
                links = self._extract_links(content, file_format)
            
            if self.generate_summary:
                summary = self._generate_summary(content, file_format)
            
            return ScanResult(
                file_path=file_path,
                content_hash=content_hash,
                file_size=file_size,
                created_at=created_at,
                modified_at=modified_at,
                file_format=file_format,
                mime_type=mime_type,
                encoding=encoding,
                line_count=len(lines),
                word_count=len(words),
                is_valid=True,
                tags=tags,
                links=links,
                summary=summary
            )
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            raise
    
    def _collect_files(
        self,
        directory: Path,
        recursive: bool,
        include_patterns: Optional[List[str]],
        exclude_patterns: Optional[List[str]]
    ) -> List[Path]:
        """Collect files to scan based on criteria."""
        files: List[Path] = []
        
        # Determine search pattern
        pattern = "**/*" if recursive else "*"
        
        for path in directory.glob(pattern):
            # Skip if not a file
            if not path.is_file():
                continue
            
            # Skip symlinks if not following them
            if path.is_symlink() and not self.follow_symlinks:
                continue
            
            # Check if file extension is supported
            if path.suffix.lower() not in self.SUPPORTED_FORMATS:
                continue
            
            # Apply include patterns
            if include_patterns:
                included = any(path.match(pattern) for pattern in include_patterns)
                if not included:
                    continue
            
            # Apply exclude patterns
            if exclude_patterns:
                excluded = any(path.match(pattern) for pattern in exclude_patterns)
                if excluded:
                    continue
            
            files.append(path)
        
        return sorted(files)  # Sort for consistent ordering
    
    def _get_file_format(self, file_path: Path) -> str:
        """Determine file format from extension."""
        suffix = file_path.suffix.lower()
        return self.SUPPORTED_FORMATS.get(suffix, 'unknown')
    
    def _read_file_content(self, file_path: Path) -> tuple[str, str]:
        """Read file content with encoding detection."""
        # Try UTF-8 first (most common)
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
        
        for encoding in encodings:
            try:
                content = file_path.read_text(encoding=encoding)
                return content, encoding
            except UnicodeDecodeError:
                continue
        
        # If all fail, read as binary and decode with errors='replace'
        raw_bytes = file_path.read_bytes()
        content = raw_bytes.decode('utf-8', errors='replace')
        return content, 'utf-8-fallback'
    
    def _extract_tags(self, content: str, file_format: str) -> Set[str]:
        """Extract tags from content based on format."""
        tags: Set[str] = set()
        
        if file_format == 'markdown':
            # Handle each pattern separately for cleaner type handling
            
            # #hashtag and @mention patterns (single capture group)
            hashtag_matches = re.findall(r'#(\w+)', content, re.IGNORECASE)
            tags.update(hashtag_matches)
            
            mention_matches = re.findall(r'@(\w+)', content, re.IGNORECASE)
            tags.update(mention_matches)
            
            # YAML tags patterns
            yaml_array_matches = re.findall(r'tags:\s*\[(.*?)\]', content, re.IGNORECASE)
            for tag_content in yaml_array_matches:
                tag_list = [tag.strip().strip('"\'') for tag in tag_content.split(',') if tag.strip()]
                tags.update(tag_list)
            
            yaml_line_matches = re.findall(r'tags:\s*(.*?)(?=\n|\r|$)', content, re.IGNORECASE)
            for tag_content in yaml_line_matches:
                # Skip if it looks like an array (already handled above)
                if not tag_content.strip().startswith('['):
                    tag_list = [tag.strip() for tag in tag_content.split(',') if tag.strip()]
                    tags.update(tag_list)
        
        elif file_format == 'org-mode':
            # #+TAGS: directive
            tags_directive_matches = re.findall(r'#\+TAGS:\s*(.*?)(?=\n|\r|$)', content, re.IGNORECASE)
            for tag_content in tags_directive_matches:
                tag_list = [tag.strip() for tag in tag_content.split() if tag.strip()]
                tags.update(tag_list)
            
            # :tag: format
            inline_tag_matches = re.findall(r':(\w+):', content)
            tags.update(inline_tag_matches)
        
        return tags
    
    def _extract_links(self, content: str, file_format: str) -> List[str]:
        """Extract links from content based on format."""
        links: List[str] = []
        
        if file_format == 'markdown':
            # Markdown links: [text](url) and ![alt](url)
            link_patterns = [
                r'\[.*?\]\((https?://[^\s\)]+)\)',  # [text](http://url)
                r'!\[.*?\]\((https?://[^\s\)]+)\)',  # ![alt](http://url)
                r'<(https?://[^\s>]+)>',  # <http://url>
                r'(https?://[^\s]+)',  # bare URLs
            ]
            
            for pattern in link_patterns:
                matches = re.findall(pattern, content)
                links.extend(str(match) for match in matches)
        
        elif file_format == 'org-mode':
            # Org-mode links: [[url][text]] and [[url]]
            link_patterns = [
                r'\[\[(https?://[^\]]+)\]\[.*?\]\]',  # [[url][text]]
                r'\[\[(https?://[^\]]+)\]\]',  # [[url]]
                r'(https?://[^\s]+)',  # bare URLs
            ]
            
            for pattern in link_patterns:
                matches = re.findall(pattern, content)
                links.extend(str(match) for match in matches)
        
        else:
            # Generic: just find bare URLs
            url_pattern = r'(https?://[^\s]+)'
            matches = re.findall(url_pattern, content)
            links.extend(str(match) for match in matches)
        
        return list(set(links))  # Remove duplicates
    
    def _generate_summary(self, content: str, file_format: str) -> Optional[str]:
        """Generate a brief summary of the content."""
        # Simple extractive summary - first few sentences
        sentences = re.split(r'[.!?]+', content)
        clean_sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        
        if not clean_sentences:
            return None
        
        # Take first 2-3 sentences, max 200 chars
        summary_parts: List[str] = []
        total_length = 0
        
        for sentence in clean_sentences[:3]:
            if total_length + len(sentence) > 200:
                break
            summary_parts.append(sentence)
            total_length += len(sentence)
        
        if summary_parts:
            return '. '.join(summary_parts) + '.'
        
        return None 