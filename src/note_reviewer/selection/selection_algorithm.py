"""Intelligent note selection algorithm with priority-based scoring."""

from __future__ import annotations

import heapq
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Set, Any

from loguru import logger

from ..database.models import Note
from .content_analyzer import ContentAnalyzer, ContentMetrics, NoteImportance


@dataclass(frozen=True)
class SelectionCriteria:
    """Configuration for note selection algorithm."""
    max_notes: int = 5
    min_notes: int = 1
    max_email_length_chars: int = 10000
    
    # Scoring weights (should sum to ~1.0)
    content_weight: float = 0.3
    freshness_weight: float = 0.25
    importance_weight: float = 0.2
    send_history_weight: float = 0.15
    diversity_weight: float = 0.1
    
    # Selection preferences
    prefer_unread: bool = True
    avoid_duplicates: bool = True
    min_word_count: int = 10
    max_days_since_modification: int = 365
    
    # Importance level thresholds
    critical_boost_multiplier: float = 2.0
    high_boost_multiplier: float = 1.5
    medium_boost_multiplier: float = 1.0
    low_penalty_multiplier: float = 0.7
    
    def __post_init__(self) -> None:
        """Validate selection criteria."""
        if self.max_notes < self.min_notes:
            raise ValueError("max_notes must be >= min_notes")
        if self.max_notes <= 0 or self.min_notes <= 0:
            raise ValueError("Note counts must be positive")
        if self.max_email_length_chars <= 0:
            raise ValueError("Max email length must be positive")
        
        # Validate weights
        total_weight: float = (
            self.content_weight + self.freshness_weight + self.importance_weight +
            self.send_history_weight + self.diversity_weight
        )
        if not (0.8 <= total_weight <= 1.2):
            logger.warning(f"Selection weights sum to {total_weight:.2f}, should be close to 1.0")


@dataclass(frozen=True)
class NoteScore:
    """Scoring information for a note selection."""
    note_id: int
    file_path: str
    total_score: float
    content_score: float
    freshness_score: float
    importance_score: float
    send_history_score: float
    diversity_score: float
    content_metrics: ContentMetrics
    
    def __lt__(self, other: NoteScore) -> bool:
        """Enable heap operations by comparing total scores."""
        return -self.total_score < -other.total_score  # Negative for max-heap behavior


class SelectionAlgorithm:
    """Advanced note selection algorithm with intelligent scoring."""
    
    def __init__(self, content_analyzer: ContentAnalyzer) -> None:
        """Initialize selection algorithm.
        
        Args:
            content_analyzer: Content analyzer instance for metrics.
        """
        self.content_analyzer: ContentAnalyzer = content_analyzer
        self._selection_history: Dict[int, datetime] = {}  # note_id -> last_selected
        logger.debug("Selection algorithm initialized")
    
    def select_notes(
        self,
        candidate_notes: List[Note],
        criteria: SelectionCriteria
    ) -> List[NoteScore]:
        """Select best notes using intelligent scoring algorithm.
        
        Args:
            candidate_notes: List of candidate notes to select from.
            criteria: Selection criteria and weights.
            
        Returns:
            List of selected notes with scores, ordered by score descending.
        """
        logger.info(f"Starting note selection from {len(candidate_notes)} candidates")
        
        # Filter candidates based on basic criteria
        filtered_notes: List[Note] = self._filter_candidates(candidate_notes, criteria)
        logger.info(f"Filtered to {len(filtered_notes)} viable candidates")
        
        if not filtered_notes:
            logger.warning("No viable notes found after filtering")
            return []
        
        # Score all filtered notes
        scored_notes: List[NoteScore] = self._score_notes(filtered_notes, criteria)
        
        # Select best notes using priority queue
        selected_notes: List[NoteScore] = self._select_top_notes(scored_notes, criteria)
        
        # Apply diversity and email length optimization
        optimized_selection: List[NoteScore] = self._optimize_selection(
            selected_notes, criteria
        )
        
        # Update selection history
        for note_score in optimized_selection:
            self._selection_history[note_score.note_id] = datetime.now()
        
        logger.info(
            f"Selected {len(optimized_selection)} notes with average score "
            f"{sum(n.total_score for n in optimized_selection) / len(optimized_selection):.2f}"
        )
        
        return optimized_selection
    
    def _filter_candidates(
        self, 
        notes: List[Note], 
        criteria: SelectionCriteria
    ) -> List[Note]:
        """Filter candidate notes based on basic criteria.
        
        Args:
            notes: Candidate notes to filter.
            criteria: Selection criteria.
            
        Returns:
            Filtered list of viable notes.
        """
        filtered: List[Note] = []
        now: datetime = datetime.now()
        
        for note in notes:
            # Check modification time
            days_since_mod: int = (now - note.modified_at).days
            if days_since_mod > criteria.max_days_since_modification:
                continue
            
            # Basic file existence check
            try:
                note_path: Path = Path(note.file_path)
                if not note_path.exists():
                    logger.debug(f"Skipping missing file: {note.file_path}")
                    continue
                
                # Quick word count check
                content: str = note_path.read_text(encoding='utf-8', errors='ignore')
                word_count: int = len(content.split())
                if word_count < criteria.min_word_count:
                    continue
                
                filtered.append(note)
                
            except Exception as e:
                logger.debug(f"Error filtering note {note.file_path}: {e}")
                continue
        
        return filtered
    
    def _score_notes(
        self, 
        notes: List[Note], 
        criteria: SelectionCriteria
    ) -> List[NoteScore]:
        """Score all notes using weighted criteria.
        
        Args:
            notes: Notes to score.
            criteria: Scoring criteria and weights.
            
        Returns:
            List of scored notes.
        """
        scored_notes: List[NoteScore] = []
        
        for note in notes:
            try:
                # Get content metrics
                metrics: ContentMetrics = self.content_analyzer.analyze_note_content(note)
                
                # Calculate individual score components
                content_score: float = metrics.get_content_score()
                freshness_score: float = metrics.get_freshness_score()
                importance_score: float = self._calculate_importance_score(metrics, criteria)
                send_history_score: float = self._calculate_send_history_score(note)
                diversity_score: float = self._calculate_diversity_score(note, criteria)
                
                # Calculate weighted total score
                total_score: float = (
                    (content_score * criteria.content_weight) +
                    (freshness_score * criteria.freshness_weight) +
                    (importance_score * criteria.importance_weight) +
                    (send_history_score * criteria.send_history_weight) +
                    (diversity_score * criteria.diversity_weight)
                )
                
                note_score: NoteScore = NoteScore(
                    note_id=note.id or 0,  # Handle None case with fallback
                    file_path=note.file_path,
                    total_score=total_score,
                    content_score=content_score,
                    freshness_score=freshness_score,
                    importance_score=importance_score,
                    send_history_score=send_history_score,
                    diversity_score=diversity_score,
                    content_metrics=metrics
                )
                
                scored_notes.append(note_score)
                
            except Exception as e:
                logger.error(f"Error scoring note {note.file_path}: {e}")
                continue
        
        return scored_notes
    
    def _calculate_importance_score(
        self, 
        metrics: ContentMetrics, 
        criteria: SelectionCriteria
    ) -> float:
        """Calculate importance-based score with configurable multipliers.
        
        Args:
            metrics: Content metrics for the note.
            criteria: Selection criteria with multipliers.
            
        Returns:
            Importance score (0-100).
        """
        base_importance_score: float = 50.0  # Baseline score
        
        # Apply importance level multipliers
        multiplier: float = {
            NoteImportance.CRITICAL: criteria.critical_boost_multiplier,
            NoteImportance.HIGH: criteria.high_boost_multiplier,
            NoteImportance.MEDIUM: criteria.medium_boost_multiplier,
            NoteImportance.LOW: criteria.low_penalty_multiplier
        }[metrics.importance_level]
        
        # Add keyword density bonus
        keyword_bonus: float = min(metrics.importance_keywords * 5, 25)
        
        total_score: float = (base_importance_score + keyword_bonus) * multiplier
        return min(total_score, 100.0)
    
    def _calculate_send_history_score(self, note: Note) -> float:
        """Calculate score based on send history.
        
        Args:
            note: Note to score.
            
        Returns:
            Send history score (0-100).
        """
        # Check internal selection history cache
        if note.id and note.id in self._selection_history:
            last_selected: datetime = self._selection_history[note.id]
            days_since_sent: int = (datetime.now() - last_selected).days
            
            if days_since_sent >= 90:
                return 90.0
            elif days_since_sent >= 30:
                return 70.0
            elif days_since_sent >= 14:
                return 50.0
            elif days_since_sent >= 7:
                return 30.0
            else:
                return 10.0  # Recently sent
        
        # Default score for notes never sent (or not in our cache)
        return 100.0
    
    def _calculate_diversity_score(
        self, 
        note: Note, 
        criteria: SelectionCriteria
    ) -> float:
        """Calculate diversity score to promote content variety.
        
        Args:
            note: Note to score.
            criteria: Selection criteria.
            
        Returns:
            Diversity score (0-100).
        """
        # Check for duplicate content
        if criteria.avoid_duplicates and self.content_analyzer.is_content_duplicate(note.file_path):
            return 20.0  # Lower score for duplicates
        
        # Simple directory-based diversity scoring
        # This could be enhanced with more sophisticated analysis
        base_score: float = 80.0
        
        return base_score
    
    def _select_top_notes(
        self, 
        scored_notes: List[NoteScore], 
        criteria: SelectionCriteria
    ) -> List[NoteScore]:
        """Select top-scoring notes using priority queue.
        
        Args:
            scored_notes: All scored notes.
            criteria: Selection criteria.
            
        Returns:
            Top selected notes.
        """
        if not scored_notes:
            return []
        
        # Use heap for efficient top-k selection
        # Python's heapq is min-heap, so we negate scores for max-heap behavior
        heap: List[NoteScore] = []
        
        for note_score in scored_notes:
            if len(heap) < criteria.max_notes:
                heapq.heappush(heap, note_score)
            elif note_score.total_score > heap[0].total_score:
                heapq.heapreplace(heap, note_score)
        
        # Convert heap to sorted list (highest score first)
        selected: List[NoteScore] = sorted(heap, key=lambda x: x.total_score, reverse=True)
        
        # Ensure minimum notes requirement
        if len(selected) < criteria.min_notes:
            logger.warning(
                f"Only {len(selected)} notes available, less than minimum {criteria.min_notes}"
            )
        
        return selected
    
    def _optimize_selection(
        self, 
        selected_notes: List[NoteScore], 
        criteria: SelectionCriteria
    ) -> List[NoteScore]:
        """Optimize final selection for email length and diversity.
        
        Args:
            selected_notes: Initially selected notes.
            criteria: Selection criteria.
            
        Returns:
            Optimized selection.
        """
        if not selected_notes:
            return selected_notes
        
        # Estimate total email length
        total_chars: int = 0
        optimized: List[NoteScore] = []
        used_directories: Set[str] = set()
        
        for note_score in selected_notes:
            # Estimate character count (word_count * 6 average chars per word)
            estimated_chars: int = note_score.content_metrics.word_count * 6
            
            # Check email length constraint
            if total_chars + estimated_chars > criteria.max_email_length_chars:
                if len(optimized) >= criteria.min_notes:
                    logger.info(f"Stopping selection at {len(optimized)} notes due to email length limit")
                    break
            
            # Add directory diversity preference (not strict requirement)
            note_dir: str = str(Path(note_score.file_path).parent)
            
            optimized.append(note_score)
            used_directories.add(note_dir)
            total_chars += estimated_chars
        
        logger.debug(
            f"Optimized selection: {len(optimized)} notes, "
            f"~{total_chars} chars, {len(used_directories)} directories"
        )
        
        return optimized
    
    def get_selection_stats(self, scored_notes: List[NoteScore]) -> Dict[str, Any]:
        """Get detailed statistics about the selection process.
        
        Args:
            scored_notes: List of scored notes.
            
        Returns:
            Dictionary with selection statistics.
        """
        if not scored_notes:
            return {"total_notes": 0}
        
        scores: List[float] = [note.total_score for note in scored_notes]
        importance_counts: Dict[str, int] = {}
        
        for note in scored_notes:
            importance: str = note.content_metrics.importance_level.value
            importance_counts[importance] = importance_counts.get(importance, 0) + 1
        
        return {
            "total_notes": len(scored_notes),
            "avg_score": sum(scores) / len(scores),
            "max_score": max(scores),
            "min_score": min(scores),
            "importance_distribution": importance_counts,
            "avg_word_count": sum(n.content_metrics.word_count for n in scored_notes) / len(scored_notes),
            "avg_freshness_days": sum(n.content_metrics.freshness_days for n in scored_notes) / len(scored_notes)
        }
    
    def clear_selection_history(self) -> None:
        """Clear the selection history cache."""
        self._selection_history.clear()
        logger.debug("Selection algorithm history cleared") 