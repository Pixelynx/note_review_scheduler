"""File operation utilities."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional


def safe_file_read(file_path: Path, encoding: str = 'utf-8') -> Optional[str]:
    """Safely read file content with error handling."""
    try:
        return file_path.read_text(encoding=encoding)
    except (OSError, UnicodeDecodeError):
        # Try with different encodings
        for fallback_encoding in ['latin-1', 'cp1252', 'utf-8-sig']:
            if fallback_encoding != encoding:
                try:
                    return file_path.read_text(encoding=fallback_encoding)
                except (OSError, UnicodeDecodeError):
                    continue
        return None


def safe_file_write(file_path: Path, content: str, encoding: str = 'utf-8') -> bool:
    """Safely write content to file with error handling."""
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding=encoding)
        return True
    except OSError:
        return False


def get_file_hash(file_path: Path, algorithm: str = 'sha256') -> Optional[str]:
    """Calculate file hash."""
    try:
        hash_obj = hashlib.new(algorithm)
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    except (OSError, ValueError):
        return None


def ensure_directory(dir_path: Path) -> bool:
    """Ensure directory exists, create if necessary."""
    try:
        dir_path.mkdir(parents=True, exist_ok=True)
        return True
    except OSError:
        return False 