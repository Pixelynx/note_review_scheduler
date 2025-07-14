#!/usr/bin/env python3
"""Pytest-based tests for the scanner system."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture
def temp_notes_dir() -> Generator[Path, None, None]:
    """Create temporary directory with test notes."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test files
        (temp_path / "test.md").write_text("# Test Note\nThis is a test.")
        (temp_path / "test.txt").write_text("Plain text note")
        
        yield temp_path


def test_file_scanner_basic(temp_notes_dir: Path) -> None:
    """Test basic file scanner functionality."""
    from src.note_reviewer.scanner.file_scanner import FileScanner
    
    scanner = FileScanner()
    results, stats = scanner.scan_directory(temp_notes_dir)
    
    assert len(results) >= 2
    assert stats.total_files >= 2
    assert stats.success_rate > 0.5


def test_markdown_handler() -> None:
    """Test Markdown format handler."""
    from src.note_reviewer.scanner.format_handlers import MarkdownHandler
    
    handler = MarkdownHandler()
    content = "# Title\n\nSome content with #tag"
    result = handler.parse(content)
    
    assert result.title == "Title"
    assert "tag" in result.tags


def test_content_processor() -> None:
    """Test content processing utilities."""
    from src.note_reviewer.scanner.content_processor import ContentProcessor
    
    processor = ContentProcessor()
    content = "This is a test note with some content."
    summary = processor.generate_content_summary(content)
    
    assert summary is not None
    assert len(summary) <= 200 