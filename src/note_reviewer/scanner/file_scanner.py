"""
Advanced File Scanner for Note Review Scheduler

Provides comprehensive file scanning with support for multiple formats,
content analysis, and metadata extraction.
"""

from __future__ import annotations

import hashlib
import mimetypes
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Union

# Try to import loguru, fall back to standard logging if it fails
try:
    from loguru import logger
    LOGURU_AVAILABLE = True
    print("Loguru imported successfully")
except ImportError as e:
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    LOGURU_AVAILABLE = False
    print(f"Loguru import failed: {e}")
    print("Falling back to standard logging")

# Print environment info for debugging
print(f"Python version: {sys.version}")
print(f"Default encoding: {sys.getdefaultencoding()}")
print(f"File system encoding: {sys.getfilesystemencoding()}")


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


def safe_log(level: str, message: str) -> None:
    """Safe logging function that handles Unicode properly."""
    try:
        # Ensure message is clean and can be encoded for Windows console
        clean_message = message.encode('cp1252', errors='replace').decode('cp1252')
        
        if LOGURU_AVAILABLE:
            getattr(logger, level.lower())(clean_message)
        else:
            getattr(logger, level.lower())(clean_message)
    except Exception as e:
        # Last resort: print to stdout using ASCII only
        ascii_message = message.encode('ascii', errors='replace').decode('ascii')
        print(f"[{level}] {ascii_message} (logging error: {e})")


class FileScanner:
    """Advanced file scanner with multi-format support and enhanced debugging."""
    
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
        generate_summary: bool = False,
        debug: bool = False
    ) -> None:
        """Initialize file scanner with configuration."""
        self.max_file_size = max_file_size
        self.min_file_size = min_file_size
        self.allowed_formats = allowed_formats if allowed_formats is not None else set(self.SUPPORTED_FORMATS.values())
        self.follow_symlinks = follow_symlinks
        self.extract_tags = extract_tags
        self.extract_links = extract_links
        self.generate_summary = generate_summary
        self.debug = debug
        
        safe_log("INFO", f"FileScanner initialized with {len(self.allowed_formats)} allowed formats")
    
    def scan_directory(
        self,
        directory: Union[str, Path],
        recursive: bool = True,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None
    ) -> tuple[List[ScanResult], ScanStats]:
        """Scan directory for supported note files."""
        start_time = datetime.now()
        directory = Path(directory)
        
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        if not directory.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {directory}")
        
        safe_log("INFO", f"Starting directory scan: {directory}")
        
        # Collect files to scan
        files_to_scan = self._collect_files(
            directory, recursive, include_patterns, exclude_patterns
        )
        
        safe_log("INFO", f"Found {len(files_to_scan)} files to scan")
        
        # Initialize statistics
        stats = ScanStats(total_files=len(files_to_scan))
        results: List[ScanResult] = []
        
        # Scan each file
        for i, file_path in enumerate(files_to_scan, 1):
            try:
                if self.debug:
                    print(f"[DEBUG] Scanning file {i}/{len(files_to_scan)}: {file_path}")
                
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
                    if self.debug:
                        print(f"[DEBUG] File scan failed: {result.error_message}")
                    
            except Exception as e:
                error_msg = f"Error scanning {file_path}: {e}"
                safe_log("ERROR", error_msg)
                if self.debug:
                    print(f"[DEBUG] Exception details: {type(e).__name__}: {e}")
                    import traceback
                    traceback.print_exc()
                
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
        
        # Use safe logging for final message
        final_msg = f"Directory scan completed - {stats.scanned_files}/{stats.total_files} files scanned successfully"
        safe_log("INFO", final_msg)
            
        return results, stats
    
    def scan_file(self, file_path: Union[str, Path]) -> ScanResult:
        """Scan a single file and extract metadata."""
        file_path = Path(file_path)
        
        if self.debug:
            print(f"[DEBUG] Processing file: {file_path}")
        
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
            if self.debug:
                print(f"[DEBUG] Reading file content...")
            content, encoding = self._read_file_content(file_path)
            
            if self.debug:
                print(f"[DEBUG] File read with encoding: {encoding}, content length: {len(content)}")
                # Show first few characters with their Unicode code points
                preview = content[:50] if len(content) > 50 else content
                char_info = [f"{c}(U+{ord(c):04X})" for c in preview[:10]]
                print(f"[DEBUG] First chars: {', '.join(char_info)}")
            
            # Clean content early to remove problematic characters
            if self.debug:
                print(f"[DEBUG] Cleaning content...")
            content = self._clean_text(content)
            
            if self.debug:
                print(f"[DEBUG] Content cleaned, new length: {len(content)}")
            
            # Calculate content hash from cleaned and normalized content
            content_hash = self._calculate_content_hash(content)
            
            # Basic content analysis
            lines = content.split('\n')
            words = content.split()
            
            # Get file timestamps
            stat = file_path.stat()
            try:
                created_at = datetime.fromtimestamp(stat.st_birthtime)
            except AttributeError:
                created_at = datetime.fromtimestamp(stat.st_ctime) # type: ignore
            modified_at = datetime.fromtimestamp(stat.st_mtime)
            
            # Get MIME type
            mime_type, _ = mimetypes.guess_type(str(file_path))
            
            # Advanced content processing
            tags: Set[str] = set()
            links: List[str] = []
            summary: Optional[str] = None
            
            if self.extract_tags:
                if self.debug:
                    print(f"[DEBUG] Extracting tags...")
                tags = self._extract_tags(content, file_format)
            
            if self.extract_links:
                if self.debug:
                    print(f"[DEBUG] Extracting links...")
                links = self._extract_links(content, file_format)
            
            if self.generate_summary:
                if self.debug:
                    print(f"[DEBUG] Generating summary...")
                summary = self._generate_summary(content, file_format)
            
            if self.debug:
                print(f"[DEBUG] File processing completed successfully")
            
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
            if self.debug:
                print(f"[DEBUG] Error in scan_file: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
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
        
        return sorted(files)
    
    def _get_file_format(self, file_path: Path) -> str:
        """Determine file format from extension."""
        suffix = file_path.suffix.lower()
        return self.SUPPORTED_FORMATS.get(suffix, 'unknown')
    
    def _read_file_content(self, file_path: Path) -> tuple[str, str]:
        """Read file content with robust encoding detection."""
        encodings = ['utf-8', 'utf-8-sig', 'utf-16', 'utf-16-le', 'utf-16-be', 'latin-1', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                    content = f.read()
                    return content, encoding
            except Exception as e:
                if self.debug:
                    print(f"[DEBUG] Failed to read with {encoding}: {e}")
                continue
        
        # Binary fallback
        try:
            with open(file_path, 'rb') as f:
                raw_bytes = f.read()
            content = raw_bytes.decode('utf-8', errors='replace')
            return content, 'binary-fallback'
        except Exception as e:
            if self.debug:
                print(f"[DEBUG] Binary fallback failed: {e}")
            return f"[Error reading file: {e}]", 'error'
    
    def _calculate_content_hash(self, content: str) -> str:
        """Calculate SHA256 hash with safe encoding."""
        try:
            # Use ASCII-only content for hashing to avoid encoding issues
            ascii_content = ''.join(c if ord(c) < 128 else '?' for c in content)
            return hashlib.sha256(ascii_content.encode('ascii')).hexdigest()
        except Exception as e:
            if self.debug:
                print(f"[DEBUG] Hash calculation failed: {e}")
            return f"error_hash_{len(content)}"
    
    def _clean_text(self, text: str) -> str:
        """Aggressively clean text to remove problematic characters."""
        if not text:
            return ""
        
        try:
            # Only keep basic ASCII characters and common punctuation
            cleaned_chars = []
            for char in text:
                code_point = ord(char)
                
                # Only keep safe ASCII range
                if code_point < 128:
                    cleaned_chars.append(char)
                elif char.isspace():  # Keep whitespace
                    cleaned_chars.append(' ')
                else:
                    # Replace everything else with space
                    cleaned_chars.append(' ')
            
            text = ''.join(cleaned_chars)
            
            # Normalize whitespace
            text = ' '.join(text.split())
            
            return text.strip()
            
        except Exception as e:
            if self.debug:
                print(f"[DEBUG] Text cleaning failed: {e}")
            # Ultimate fallback: only ASCII letters, numbers, and spaces
            try:
                return ''.join(c if c.isalnum() or c.isspace() else ' ' for c in text if ord(c) < 128).strip()
            except Exception:
                return "[Text cleaning failed]"
    
    def _extract_tags(self, content: str, file_format: str) -> Set[str]:
        """Extract tags with error handling."""
        try:
            tags: Set[str] = set()
            
            if file_format == 'markdown':
                # Simple hashtag extraction
                hashtag_matches = re.findall(r'#(\w+)', content)
                tags.update(hashtag_matches)
            
            return {self._clean_text(str(tag)) for tag in tags if tag}
        except Exception as e:
            if self.debug:
                print(f"[DEBUG] Tag extraction failed: {e}")
            return set()
    
    def _extract_links(self, content: str, file_format: str) -> List[str]:
        """Extract links with error handling."""
        try:
            links: List[str] = []
            # Simple URL extraction
            url_matches = re.findall(r'https?://[^\s]+', content)
            links.extend(url_matches)
            return [self._clean_text(str(link)) for link in links if link]
        except Exception as e:
            if self.debug:
                print(f"[DEBUG] Link extraction failed: {e}")
            return []
    
    def _generate_summary(self, content: str, file_format: str) -> Optional[str]:
        """Generate summary with error handling."""
        try:
            sentences = content.split('.')[:2]  # First 2 sentences
            summary = '. '.join(s.strip() for s in sentences if s.strip())
            if summary:
                return self._clean_text(summary)
            return None
        except Exception as e:
            if self.debug:
                print(f"[DEBUG] Summary generation failed: {e}")
            return None


# Test function to help debug
def test_scanner_creation():
    """Test if we can create a scanner instance."""
    try:
        scanner = FileScanner(debug=True)
        print("FileScanner created successfully")
        return scanner
    except Exception as e:
        print(f"Failed to create FileScanner: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    print("=== FileScanner Debug Version ===")
    test_scanner_creation()