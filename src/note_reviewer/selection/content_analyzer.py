"""Content analysis engine for intelligent note evaluation."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple

from loguru import logger

from ..database.models import Note


class NoteImportance(Enum):
    """Note importance levels for scoring."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass(frozen=True)
class ContentMetrics:
    """Immutable content analysis metrics for a note."""
    content_hash: str
    word_count: int
    line_count: int
    code_blocks: int
    headers: int
    links: int
    todo_items: int
    importance_keywords: int
    readability_score: float
    freshness_days: int
    importance_level: NoteImportance
    
    def get_content_score(self) -> float:
        """Calculate overall content quality score (0-100)."""
        # Base score from structure
        structure_score: float = min(
            (self.headers * 5) + (self.code_blocks * 3) + (self.links * 2), 50
        )
        
        # Content depth score
        depth_score: float = min(self.word_count / 10, 30)  # Up to 30 for 300+ words
        
        # Importance boost
        importance_multiplier: float = {
            NoteImportance.CRITICAL: 1.5,
            NoteImportance.HIGH: 1.2,
            NoteImportance.MEDIUM: 1.0,
            NoteImportance.LOW: 0.8
        }[self.importance_level]
        
        # TODO items add engagement
        todo_score: float = min(self.todo_items * 3, 20)
        
        base_score: float = structure_score + depth_score + todo_score
        return min(base_score * importance_multiplier, 100.0)
    
    def get_freshness_score(self) -> float:
        """Calculate freshness score based on recency (0-100)."""
        if self.freshness_days == 0:
            return 100.0
        elif self.freshness_days <= 7:
            return 90.0 - (self.freshness_days * 5)  # 90-55
        elif self.freshness_days <= 30:
            return 55.0 - ((self.freshness_days - 7) * 1.5)  # 55-20.5
        elif self.freshness_days <= 90:
            return 20.0 - ((self.freshness_days - 30) * 0.2)  # 20-8
        else:
            return max(5.0 - ((self.freshness_days - 90) * 0.05), 0.0)


class ContentAnalyzer:
    """Advanced content analysis engine for note evaluation."""
    
    # Critical keywords that boost importance
    CRITICAL_KEYWORDS: Set[str] = {
        "urgent", "critical", "important", "deadline", "asap", "emergency",
        "breaking", "alert", "warning", "error", "bug", "issue", "problem"
    }
    
    # High importance keywords
    HIGH_KEYWORDS: Set[str] = {
        "meeting", "presentation", "interview", "review", "decision", "action",
        "follow-up", "milestone", "release", "launch", "deploy", "fix"
    }
    
    # Medium importance keywords
    MEDIUM_KEYWORDS: Set[str] = {
        "idea", "note", "research", "analysis", "summary", "plan", "draft",
        "concept", "proposal", "suggestion", "feedback", "update"
    }
    
    # Patterns for content analysis
    HEADER_PATTERN: re.Pattern[str] = re.compile(r'^#{1,6}\s+.+$', re.MULTILINE)
    CODE_BLOCK_PATTERN: re.Pattern[str] = re.compile(r'```[\s\S]*?```|`[^`]+`')
    LINK_PATTERN: re.Pattern[str] = re.compile(r'\[([^\]]+)\]\([^)]+\)|https?://[^\s]+')
    TODO_PATTERN: re.Pattern[str] = re.compile(r'(?:^|\s)(?:TODO|FIXME|XXX|NOTE):', re.IGNORECASE | re.MULTILINE)
    BULLET_PATTERN: re.Pattern[str] = re.compile(r'^[\s]*[-*+]\s+', re.MULTILINE)
    
    def __init__(self) -> None:
        """Initialize the content analyzer."""
        self._content_hashes: Dict[str, str] = {}  # path -> hash
        self._duplicate_groups: Dict[str, List[str]] = {}  # hash -> list of paths
        logger.debug("Content analyzer initialized")
    
    def analyze_note_content(
        self, 
        note: Note, 
        content: Optional[str] = None
    ) -> ContentMetrics:
        """Perform comprehensive content analysis on a note.
        
        Args:
            note: Note database model.
            content: Optional content string. If None, reads from file.
            
        Returns:
            ContentMetrics with detailed analysis results.
        """
        try:
            # Get content
            if content is None:
                note_path: Path = Path(note.file_path)
                if not note_path.exists():
                    logger.warning(f"Note file not found: {note_path}")
                    return self._create_empty_metrics(note.content_hash)
                content = note_path.read_text(encoding='utf-8', errors='ignore')
            
            # Calculate content hash
            content_hash: str = self._calculate_content_hash(content)
            
            # Update duplicate tracking
            self._update_duplicate_tracking(note.file_path, content_hash)
            
            # Analyze content structure
            word_count: int = len(content.split())
            line_count: int = len(content.splitlines())
            
            # Count structural elements
            headers: int = len(self.HEADER_PATTERN.findall(content))
            code_blocks: int = len(self.CODE_BLOCK_PATTERN.findall(content))
            links: int = len(self.LINK_PATTERN.findall(content))
            todo_items: int = len(self.TODO_PATTERN.findall(content))
            
            # Analyze importance
            importance_keywords: int = self._count_importance_keywords(content)
            importance_level: NoteImportance = self._determine_importance_level(content)
            
            # Calculate readability (simplified Flesch Reading Ease)
            readability_score: float = self._calculate_readability(content, word_count)
            
            # Calculate freshness
            freshness_days: int = self._calculate_freshness_days(note.modified_at)
            
            metrics: ContentMetrics = ContentMetrics(
                content_hash=content_hash,
                word_count=word_count,
                line_count=line_count,
                code_blocks=code_blocks,
                headers=headers,
                links=links,
                todo_items=todo_items,
                importance_keywords=importance_keywords,
                readability_score=readability_score,
                freshness_days=freshness_days,
                importance_level=importance_level
            )
            
            logger.debug(
                f"Content analysis complete for {Path(note.file_path).name}: "
                f"words={word_count}, importance={importance_level.value}, "
                f"freshness={freshness_days}d"
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Content analysis failed for {note.file_path}: {e}")
            return self._create_empty_metrics(note.content_hash)
    
    def _calculate_content_hash(self, content: str) -> str:
        """Calculate SHA-256 hash of content for change detection.
        
        Args:
            content: Text content to hash.
            
        Returns:
            Hexadecimal SHA-256 hash.
        """
        # Normalize content for consistent hashing
        normalized_content: str = content.strip().replace('\r\n', '\n')
        return hashlib.sha256(normalized_content.encode('utf-8')).hexdigest()
    
    def _update_duplicate_tracking(self, file_path: str, content_hash: str) -> None:
        """Update duplicate content tracking.
        
        Args:
            file_path: Path to the note file.
            content_hash: Content hash of the note.
        """
        # Remove old hash if exists
        old_hash: Optional[str] = self._content_hashes.get(file_path)
        if old_hash and old_hash in self._duplicate_groups:
            self._duplicate_groups[old_hash].remove(file_path)
            if not self._duplicate_groups[old_hash]:
                del self._duplicate_groups[old_hash]
        
        # Add new hash
        self._content_hashes[file_path] = content_hash
        if content_hash not in self._duplicate_groups:
            self._duplicate_groups[content_hash] = []
        self._duplicate_groups[content_hash].append(file_path)
    
    def _count_importance_keywords(self, content: str) -> int:
        """Count importance-indicating keywords in content.
        
        Args:
            content: Text content to analyze.
            
        Returns:
            Total count of importance keywords.
        """
        content_lower: str = content.lower()
        total_count: int = 0
        
        for keyword in self.CRITICAL_KEYWORDS | self.HIGH_KEYWORDS | self.MEDIUM_KEYWORDS:
            total_count += content_lower.count(keyword)
        
        return total_count
    
    def _determine_importance_level(self, content: str) -> NoteImportance:
        """Determine importance level based on content analysis.
        
        Args:
            content: Text content to analyze.
            
        Returns:
            Determined importance level.
        """
        content_lower: str = content.lower()
        
        # Check for critical keywords
        critical_count: int = sum(
            content_lower.count(keyword) for keyword in self.CRITICAL_KEYWORDS
        )
        if critical_count > 0:
            return NoteImportance.CRITICAL
        
        # Check for high importance keywords
        high_count: int = sum(
            content_lower.count(keyword) for keyword in self.HIGH_KEYWORDS
        )
        if high_count >= 2:
            return NoteImportance.HIGH
        
        # Check for medium importance keywords
        medium_count: int = sum(
            content_lower.count(keyword) for keyword in self.MEDIUM_KEYWORDS
        )
        if medium_count >= 1 or high_count == 1:
            return NoteImportance.MEDIUM
        
        return NoteImportance.LOW
    
    def _calculate_readability(self, content: str, word_count: int) -> float:
        """Calculate simplified readability score.
        
        Args:
            content: Text content to analyze.
            word_count: Number of words in content.
            
        Returns:
            Readability score (0-100, higher is more readable).
        """
        if word_count == 0:
            return 0.0
        
        # Count sentences (simplified)
        sentence_count: int = len(re.findall(r'[.!?]+', content))
        if sentence_count == 0:
            sentence_count = 1
        
        # Count syllables (very simplified - count vowel groups)
        syllable_count: int = len(re.findall(r'[aeiouAEIOU]+', content))
        if syllable_count == 0:
            syllable_count = word_count  # Fallback
        
        # Simplified Flesch Reading Ease formula
        avg_sentence_length: float = word_count / sentence_count
        avg_syllables_per_word: float = syllable_count / word_count
        
        readability: float = (
            206.835 
            - (1.015 * avg_sentence_length) 
            - (84.6 * avg_syllables_per_word)
        )
        
        # Clamp to 0-100 range
        return max(0.0, min(100.0, readability))
    
    def _calculate_freshness_days(self, modified_at: datetime) -> int:
        """Calculate days since last modification.
        
        Args:
            modified_at: Last modification timestamp.
            
        Returns:
            Number of days since modification.
        """
        now: datetime = datetime.now()
        delta: timedelta = now - modified_at
        return max(0, delta.days)
    
    def _create_empty_metrics(self, content_hash: str) -> ContentMetrics:
        """Create empty metrics for failed analysis.
        
        Args:
            content_hash: Content hash from database.
            
        Returns:
            ContentMetrics with default values.
        """
        return ContentMetrics(
            content_hash=content_hash,
            word_count=0,
            line_count=0,
            code_blocks=0,
            headers=0,
            links=0,
            todo_items=0,
            importance_keywords=0,
            readability_score=0.0,
            freshness_days=999,
            importance_level=NoteImportance.LOW
        )
    
    def get_duplicate_notes(self) -> Dict[str, List[str]]:
        """Get groups of notes with identical content.
        
        Returns:
            Dictionary mapping content hash to list of file paths with that content.
        """
        return {
            hash_val: paths 
            for hash_val, paths in self._duplicate_groups.items() 
            if len(paths) > 1
        }
    
    def is_content_duplicate(self, file_path: str) -> bool:
        """Check if a note has duplicate content.
        
        Args:
            file_path: Path to the note file.
            
        Returns:
            True if content is duplicated elsewhere.
        """
        content_hash: Optional[str] = self._content_hashes.get(file_path)
        if not content_hash:
            return False
        
        duplicate_paths: List[str] = self._duplicate_groups.get(content_hash, [])
        return len(duplicate_paths) > 1
    
    def get_content_change_detection(
        self, 
        file_path: str, 
        new_content: str
    ) -> Tuple[bool, str]:
        """Detect if content has changed since last analysis.
        
        Args:
            file_path: Path to the note file.
            new_content: Current content to check.
            
        Returns:
            Tuple of (has_changed, new_hash).
        """
        new_hash: str = self._calculate_content_hash(new_content)
        old_hash: Optional[str] = self._content_hashes.get(file_path)
        
        has_changed: bool = old_hash != new_hash
        return has_changed, new_hash
    
    def clear_cache(self) -> None:
        """Clear all cached content analysis data."""
        self._content_hashes.clear()
        self._duplicate_groups.clear()
        logger.debug("Content analyzer cache cleared") 