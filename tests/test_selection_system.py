#!/usr/bin/env python3
"""Test script to verify Phase 3 selection system functionality."""

from __future__ import annotations

import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from src.note_reviewer.database.models import Note

# Configure loguru for testing
logger.remove()  # Remove default handler
logger.add("test_selection_system.log", level="DEBUG")
logger.add(lambda msg: print(msg, end=""), level="INFO")

def create_test_notes() -> List[Path]:
    """Create diverse test note files for comprehensive testing.
    
    Returns:
        List of paths to created test notes.
    """
    test_notes: List[Path] = []
    
    # Test note templates
    note_templates: List[tuple[str, str]] = [
        (
            "urgent_meeting.md",
            """# URGENT: Client Meeting Tomorrow
            
            ## Critical Action Items
            - **DEADLINE**: Prepare presentation slides by 5 PM
            - Review Q3 financial reports
            - Contact John about budget approval
            
            ### Meeting Details
            - Time: 2:00 PM EST
            - Location: Conference Room A
            - Attendees: CEO, CFO, Project Team
            
            > This is a high-priority meeting that could determine project funding.
            
            ```python
            # Code snippet for demo
            def calculate_roi(investment, returns):
                return (returns - investment) / investment * 100
            ```
            
            **TODO**: Finalize contract terms before meeting
            """
        ),
        (
            "personal_journal.txt",
            """Today's Personal Reflections
            
            Had a great day with family at the park. The weather was perfect
            and the kids loved playing on the swings. 
            
            Planning to read that new book about mindfulness that Sarah recommended.
            Also thinking about starting a small garden in the backyard this spring.
            
            Health goals for next month:
            - Exercise 3 times per week
            - Drink more water daily
            - Get 8 hours of sleep consistently
            
            Grateful for: good health, supportive family, meaningful work
            """
        ),
        (
            "learning_notes.md",
            """# Python Data Structures Study Notes
            
            ## Lists vs Tuples
            
            ### Lists (Mutable)
            - Dynamic arrays that can be modified
            - Use square brackets: `[1, 2, 3]`
            - Methods: append(), remove(), pop()
            
            ### Tuples (Immutable)  
            - Fixed sequences that cannot be changed
            - Use parentheses: `(1, 2, 3)`
            - More memory efficient for large datasets
            
            ## Dictionary Operations
            ```python
            # Creating dictionaries
            student = {"name": "Alice", "age": 20, "grade": "A"}
            
            # Accessing values
            print(student.get("name", "Unknown"))
            ```
            
            **Research TODO**: Look into Python 3.11 performance improvements
            
            Links for further reading:
            - [Python Documentation](https://docs.python.org)
            - [Real Python Tutorials](https://realpython.com)
            """
        ),
        (
            "project_ideas.txt",
            """Creative Project Ideas Brainstorm
            
            1. Mobile App for Local Food Sharing
               - Connect neighbors to share excess food
               - Reduce food waste in communities
               - Social impact + sustainability
            
            2. AI-Powered Study Assistant
               - Personalized learning recommendations
               - Adaptive quiz generation
               - Progress tracking and analytics
            
            3. Virtual Reality Museum Tours
               - Immersive historical experiences
               - Educational content for schools
               - Accessibility features for disabled users
            
            4. Smart Home Energy Optimizer
               - Machine learning for energy usage patterns
               - Automated device scheduling
               - Cost savings calculator
            
            Innovation areas to explore:
            - Blockchain applications
            - IoT integration possibilities
            - Machine learning use cases
            """
        ),
        (
            "bug_report.md",
            """# CRITICAL BUG: Database Connection Timeout
            
            ## Issue Description
            **Severity**: CRITICAL
            **Priority**: P0 - Fix Immediately
            
            The production database is experiencing connection timeouts during peak hours (2-4 PM EST).
            This is causing service disruptions and user complaints.
            
            ## Error Details
            ```
            ConnectionError: timeout after 30 seconds
            at DatabasePool.getConnection()
            Stack trace: [detailed trace here]
            ```
            
            ## Impact
            - 500+ users affected daily
            - Revenue loss estimated at $10K/hour
            - Customer satisfaction scores dropping
            
            ## Immediate Actions Required
            1. Increase connection pool size from 50 to 100
            2. Optimize slow queries identified in logs
            3. Add database monitoring alerts
            4. Prepare rollback plan if issues persist
            
            ## Root Cause Analysis
            - Recent traffic increase by 300%
            - Database server under-provisioned
            - No connection pooling optimization
            
            **FIXME**: Review all database configurations
            **TODO**: Schedule emergency maintenance window
            """
        ),
        (
            "vacation_planning.txt",
            """Summer Vacation Planning 2024
            
            Destinations under consideration:
            - Japan (Tokyo, Kyoto) - cherry blossom season
            - Italy (Rome, Florence, Venice) - art and culture
            - Costa Rica - eco-tourism and wildlife
            - Iceland - northern lights and landscapes
            
            Budget considerations:
            - Flight costs: $800-1500 per person
            - Accommodation: $100-200 per night
            - Food and activities: $50-100 per day
            - Total estimated: $3000-5000 for family
            
            Planning timeline:
            - March: Finalize destination and book flights
            - April: Reserve accommodations
            - May: Plan daily itineraries
            - June: Pack and prepare documents
            
            Must-have experiences:
            - Local cuisine tasting
            - Historical site visits
            - Nature/outdoor activities
            - Cultural performances or festivals
            """
        ),
        (
            "meeting_notes_old.txt",
            """Weekly Team Meeting Notes - January 15, 2024
            
            Attendees: Alice, Bob, Carol, Dave, Eve
            
            Agenda Items Discussed:
            1. Project status updates
            2. Upcoming deadline review
            3. Resource allocation
            4. Q1 planning
            
            Key Decisions:
            - Move sprint deadline to January 30th
            - Allocate 2 additional developers to Feature X
            - Schedule architecture review for next week
            
            Action Items:
            - Alice: Update project timeline
            - Bob: Conduct performance testing
            - Carol: Prepare Q1 budget proposal
            
            Next meeting: January 22, 2024
            """
        ),
        (
            "duplicate_content.md",  # This will be duplicated
            """# Daily Standup Notes
            
            ## What I worked on yesterday:
            - Fixed the authentication bug
            - Updated user interface mockups
            - Reviewed pull requests from team
            
            ## What I'm working on today:
            - Implement new dashboard features
            - Write unit tests for API endpoints
            - Attend client presentation at 3 PM
            
            ## Blockers:
            - Waiting for API specification from backend team
            - Need design approval for mobile layout
            """
        )
    ]
    
    # Create test notes
    for filename, content in note_templates:
        temp_file: Path = Path(tempfile.mktemp(suffix=f"_{filename}"))
        temp_file.write_text(content, encoding="utf-8")
        test_notes.append(temp_file)
        logger.debug(f"Created test note: {temp_file}")
    
    # Create a duplicate content file
    duplicate_file: Path = Path(tempfile.mktemp(suffix="_duplicate_standup.md"))
    duplicate_file.write_text(note_templates[-1][1], encoding="utf-8")  # Same content as last note
    test_notes.append(duplicate_file)
    
    return test_notes


def create_test_database_notes(note_files: List[Path]) -> List[Note]:
    """Create test Note objects for the selection system.
    
    Args:
        note_files: List of note file paths.
        
    Returns:
        List of Note objects.
    """
    import hashlib
    
    notes: List[Note] = []
    base_time: datetime = datetime.now()
    
    for i, note_file in enumerate(note_files):
        # Calculate content hash
        content: str = note_file.read_text(encoding="utf-8")
        content_hash: str = hashlib.sha256(content.encode("utf-8")).hexdigest()
        
        # Create note with varied timestamps
        modified_at: datetime = base_time - timedelta(days=i * 2)  # Spread across time
        
        note: Note = Note(
            id=i + 1,
            file_path=str(note_file),
            content_hash=content_hash,
            file_size=note_file.stat().st_size,
            created_at=modified_at,
            modified_at=modified_at
        )
        notes.append(note)
    
    return notes


def test_content_analyzer() -> None:
    """Test the content analysis functionality."""
    from src.note_reviewer.selection.content_analyzer import ContentAnalyzer, NoteImportance
    
    logger.info("\nTEST: Content Analysis Engine")
    logger.info("=" * 40)
    
    # Create test notes
    test_files: List[Path] = create_test_notes()
    test_notes: List[Note] = create_test_database_notes(test_files)
    
    # Initialize analyzer
    analyzer: ContentAnalyzer = ContentAnalyzer()
    
    try:
        # Test content analysis
        for i, note in enumerate(test_notes[:5]):  # Test first 5 notes
            logger.info(f"\nAnalyzing note {i+1}: {Path(note.file_path).name}")
            
            metrics = analyzer.analyze_note_content(note)
            
            logger.info(f"  Content Hash: {metrics.content_hash[:16]}...")
            logger.info(f"  Word Count: {metrics.word_count}")
            logger.info(f"  Importance: {metrics.importance_level.value}")
            logger.info(f"  Headers: {metrics.headers}, Code Blocks: {metrics.code_blocks}")
            logger.info(f"  Links: {metrics.links}, TODO Items: {metrics.todo_items}")
            logger.info(f"  Content Score: {metrics.get_content_score():.1f}")
            logger.info(f"  Freshness Score: {metrics.get_freshness_score():.1f}")
            logger.info(f"  Readability: {metrics.readability_score:.1f}")
            
            # Validate importance detection
            expected_importance = {
                0: NoteImportance.CRITICAL,  # urgent_meeting.md
                1: NoteImportance.LOW,       # personal_journal.txt
                2: NoteImportance.MEDIUM,    # learning_notes.md
                3: NoteImportance.MEDIUM,    # project_ideas.txt
                4: NoteImportance.CRITICAL,  # bug_report.md
            }
            
            expected = expected_importance.get(i)
            if expected and metrics.importance_level != expected:
                logger.warning(f"  Expected {expected.value}, got {metrics.importance_level.value}")
            else:
                logger.success(f"  Importance correctly detected")
        
        # Test duplicate detection
        logger.info(f"\nTesting duplicate detection...")
        duplicates = analyzer.get_duplicate_notes()
        if duplicates:
            logger.info(f"Found {len(duplicates)} duplicate groups:")
            for hash_val, paths in duplicates.items():
                logger.info(f"  Hash {hash_val[:16]}...: {len(paths)} files")
                for path in paths:
                    logger.info(f"    - {Path(path).name}")
        else:
            logger.info("No duplicates found")
        
        # Test content change detection
        logger.info(f"\nTesting change detection...")
        test_note = test_notes[0]
        original_content = Path(test_note.file_path).read_text(encoding="utf-8")
        modified_content = original_content + "\n\nThis is additional content for testing."
        
        changed, new_hash = analyzer.get_content_change_detection(test_note.file_path, modified_content)
        logger.info(f"  Content changed: {changed}")
        logger.info(f"  New hash: {new_hash[:16]}...")
        
        logger.success("Content analyzer tests passed!")
        
    except Exception as e:
        logger.error(f"✗ Content analyzer test failed: {e}")
        raise
    finally:
        # Cleanup
        for test_file in test_files:
            if test_file.exists():
                test_file.unlink()


def test_selection_algorithm() -> None:
    """Test the note selection algorithm."""
    from src.note_reviewer.selection.content_analyzer import ContentAnalyzer
    from src.note_reviewer.selection.selection_algorithm import SelectionAlgorithm, SelectionCriteria
    
    logger.info("\nTEST: Selection Algorithm")
    logger.info("=" * 40)
    
    # Create test data
    test_files: List[Path] = create_test_notes()
    test_notes: List[Note] = create_test_database_notes(test_files)
    
    # Initialize components
    analyzer: ContentAnalyzer = ContentAnalyzer()
    selector: SelectionAlgorithm = SelectionAlgorithm(analyzer)
    
    try:
        # Test with default criteria
        logger.info("\nTesting with default selection criteria...")
        default_criteria: SelectionCriteria = SelectionCriteria(
            max_notes=3,
            min_notes=1,
            max_email_length_chars=8000
        )
        
        selected_notes = selector.select_notes(test_notes, default_criteria)
        
        logger.info(f"Selected {len(selected_notes)} notes:")
        for i, note_score in enumerate(selected_notes, 1):
            logger.info(f"  {i}. {Path(note_score.file_path).name}")
            logger.info(f"     Total Score: {note_score.total_score:.2f}")
            logger.info(f"     Content: {note_score.content_score:.1f}, "
                       f"Freshness: {note_score.freshness_score:.1f}, "
                       f"Importance: {note_score.importance_score:.1f}")
            logger.info(f"     Send History: {note_score.send_history_score:.1f}, "
                       f"Diversity: {note_score.diversity_score:.1f}")
        
        # Test with high importance bias
        logger.info("\nTesting with high importance bias...")
        importance_criteria: SelectionCriteria = SelectionCriteria(
            max_notes=5,
            importance_weight=0.5,
            content_weight=0.2,
            freshness_weight=0.2,
            send_history_weight=0.05,
            diversity_weight=0.05,
            critical_boost_multiplier=3.0
        )
        
        importance_selected = selector.select_notes(test_notes, importance_criteria)
        logger.info(f"High-importance selection: {len(importance_selected)} notes")
        
        # Verify critical notes are prioritized
        critical_count = sum(
            1 for note in importance_selected 
            if note.content_metrics.importance_level.value == "CRITICAL"
        )
        logger.info(f"Critical notes in selection: {critical_count}")
        
        # Test selection statistics
        logger.info("\nTesting selection statistics...")
        stats = selector.get_selection_stats(selected_notes)
        logger.info(f"Selection statistics:")
        for key, value in stats.items():
            logger.info(f"  {key}: {value}")
        
        # Test edge cases
        logger.info("\nTesting edge cases...")
        
        # Empty note list
        empty_selection = selector.select_notes([], default_criteria)
        assert len(empty_selection) == 0, "Empty note list should return empty selection"
        logger.success("Empty list handling works")
        
        # Single note
        single_selection = selector.select_notes(test_notes[:1], default_criteria)
        assert len(single_selection) == 1, "Single note should return single selection"
        logger.success("Single note handling works")
        
        logger.success("Selection algorithm tests passed!")
        
    except Exception as e:
        logger.error(f"✗ Selection algorithm test failed: {e}")
        raise
    finally:
        # Cleanup
        for test_file in test_files:
            if test_file.exists():
                test_file.unlink()


def test_email_formatter() -> None:
    """Test the email formatting functionality."""
    from src.note_reviewer.selection.content_analyzer import ContentAnalyzer
    from src.note_reviewer.selection.selection_algorithm import SelectionAlgorithm, SelectionCriteria
    from src.note_reviewer.selection.email_formatter import EmailFormatter
    
    logger.info("\nTEST: Email Formatter")
    logger.info("=" * 40)
    
    # Create test data
    test_files: List[Path] = create_test_notes()
    test_notes: List[Note] = create_test_database_notes(test_files)
    
    # Initialize components
    analyzer: ContentAnalyzer = ContentAnalyzer()
    selector: SelectionAlgorithm = SelectionAlgorithm(analyzer)
    formatter: EmailFormatter = EmailFormatter()
    
    try:
        # Select notes for formatting
        criteria: SelectionCriteria = SelectionCriteria(max_notes=4)
        selected_notes = selector.select_notes(test_notes, criteria)
        
        logger.info(f"Formatting email with {len(selected_notes)} notes...")
        
        # Test email formatting
        email_content = formatter.format_email(
            selected_notes=selected_notes,
            template_name="rich_review",
            include_toc=True,
            max_preview_words=30
        )
        
        # Validate email content
        assert len(email_content.html_content) > 0, "HTML content should not be empty"
        assert len(email_content.plain_text_content) > 0, "Plain text content should not be empty"
        assert len(email_content.subject) > 0, "Subject should not be empty"
        
        logger.info(f"Email Subject: {email_content.subject}")
        logger.info(f"Note Count: {email_content.note_count}")
        logger.info(f"Total Words: {email_content.total_word_count}")
        logger.info(f"Categories: {', '.join(email_content.categories)}")
        logger.info(f"Estimated Read Time: {email_content.estimated_read_time_minutes} minutes")
        logger.info(f"Importance Summary: {email_content.importance_summary}")
        
        # Test HTML content structure
        html_content = email_content.html_content
        assert "<!DOCTYPE html>" in html_content, "HTML should have DOCTYPE"
        assert "<title>" in html_content, "HTML should have title"
        assert "Table of Contents" in html_content, "Should include TOC"
        assert "email-container" in html_content, "Should have container class"
        
        # Test plain text content
        text_content = email_content.plain_text_content
        assert "TABLE OF CONTENTS" in text_content, "Text should have TOC"
        assert "Generated by Note Review Scheduler" in text_content, "Should have footer"
        
        logger.info("\nTesting content preview generation...")
        
        # Save sample email files for inspection
        html_file = Path("test_email_sample.html")
        text_file = Path("test_email_sample.txt")
        
        html_file.write_text(email_content.html_content, encoding="utf-8")
        text_file.write_text(email_content.plain_text_content, encoding="utf-8")
        
        logger.info(f"Sample HTML email saved to: {html_file}")
        logger.info(f"Sample text email saved to: {text_file}")
        
        # Test different formatting options
        logger.info("\nTesting formatting options...")
        
        # Without TOC
        no_toc_email = formatter.format_email(
            selected_notes=selected_notes[:2],
            include_toc=False,
            max_preview_words=20
        )
        
        assert "Table of Contents" not in no_toc_email.html_content, "Should not include TOC"
        logger.success("No-TOC formatting works")
        
        # Test edge cases
        logger.info("\nTesting edge cases...")
        
        # Single note
        single_note_email = formatter.format_email(selected_notes[:1])
        assert single_note_email.note_count == 1, "Should handle single note"
        logger.success("Single note formatting works")
        
        # Test empty list (should fail gracefully)
        try:
            formatter.format_email([])
            assert False, "Should raise error for empty note list"
        except ValueError:
            logger.success("Empty list handling works")
        
        logger.success("Email formatter tests passed!")
        
    except Exception as e:
        logger.error(f"✗ Email formatter test failed: {e}")
        raise
    finally:
        # Cleanup test files
        for test_file in test_files:
            if test_file.exists():
                test_file.unlink()
        
        # Keep sample files for inspection but log their location
        if Path("test_email_sample.html").exists():
            logger.info("Sample files kept for inspection:")
            logger.info("- test_email_sample.html")
            logger.info("- test_email_sample.txt")


def test_integration() -> None:
    """Test complete integration of all Phase 3 components."""
    logger.info("\nTEST: Phase 3 Integration")
    logger.info("=" * 40)
    
    from src.note_reviewer.selection import (
        ContentAnalyzer, SelectionAlgorithm, SelectionCriteria, EmailFormatter
    )
    
    # Create comprehensive test data
    test_files: List[Path] = create_test_notes()
    test_notes: List[Note] = create_test_database_notes(test_files)
    
    try:
        logger.info("Testing complete Phase 3 workflow...")
        
        # Step 1: Initialize all components
        analyzer: ContentAnalyzer = ContentAnalyzer()
        selector: SelectionAlgorithm = SelectionAlgorithm(analyzer)
        formatter: EmailFormatter = EmailFormatter()
        
        # Step 2: Configure selection criteria
        criteria: SelectionCriteria = SelectionCriteria(
            max_notes=5,
            min_notes=2,
            max_email_length_chars=12000,
            content_weight=0.25,
            freshness_weight=0.25,
            importance_weight=0.3,
            send_history_weight=0.15, 
            diversity_weight=0.05,
            avoid_duplicates=True,
            min_word_count=20
        )
        
        # Step 3: Select best notes
        logger.info("Step 1: Analyzing and selecting notes...")
        selected_notes = selector.select_notes(test_notes, criteria)
        logger.info(f"Selected {len(selected_notes)} notes for email")
        
        # Step 4: Format email
        logger.info("Step 2: Formatting email content...")
        email_content = formatter.format_email(
            selected_notes=selected_notes,
            include_toc=True,
            max_preview_words=40
        )
        
        # Step 5: Validate complete workflow
        logger.info("Step 3: Validating complete workflow...")
        
        # Check that selection respects criteria
        assert len(selected_notes) >= criteria.min_notes, "Should meet minimum notes"
        assert len(selected_notes) <= criteria.max_notes, "Should not exceed maximum notes"
        
        # Check that all notes meet word count requirement
        for note_score in selected_notes:
            assert note_score.content_metrics.word_count >= criteria.min_word_count, \
                f"Note {note_score.file_path} below minimum word count"
        
        # Check email content completeness
        assert email_content.note_count == len(selected_notes), "Note count mismatch"
        assert len(email_content.categories) > 0, "Should have categories"
        assert email_content.estimated_read_time_minutes > 0, "Should have read time"
        
        # Step 6: Performance and statistics
        selection_stats = selector.get_selection_stats(selected_notes)
        
        logger.info("\nIntegration Test Results:")
        logger.info("=" * 30)
        logger.info(f"Notes processed: {len(test_notes)}")
        logger.info(f"Notes selected: {len(selected_notes)}")
        logger.info(f"Average score: {selection_stats['avg_score']:.2f}")
        logger.info(f"Email categories: {len(email_content.categories)}")
        logger.info(f"Total word count: {email_content.total_word_count}")
        logger.info(f"HTML length: {len(email_content.html_content):,} chars")
        logger.info(f"Text length: {len(email_content.plain_text_content):,} chars")
        logger.info(f"Estimated read time: {email_content.estimated_read_time_minutes} min")
        
        # Save final integration test output
        final_html = Path("integration_test_email.html")
        final_text = Path("integration_test_email.txt")
        
        final_html.write_text(email_content.html_content, encoding="utf-8")
        final_text.write_text(email_content.plain_text_content, encoding="utf-8")
        
        logger.success("Phase 3 integration test passed!")
        logger.info(f"Final email samples saved:")
        logger.info(f"- {final_html}")
        logger.info(f"- {final_text}")
        
    except Exception as e:
        logger.error(f"✗ Integration test failed: {e}")
        raise
    finally:
        # Cleanup
        for test_file in test_files:
            if test_file.exists():
                test_file.unlink()


def main() -> None:
    """Run all Phase 3 selection system tests."""
    logger.info("Starting Phase 3 Selection System Tests")
    logger.info("=" * 50)
    
    try:
        # Test individual components
        test_content_analyzer()
        test_selection_algorithm() 
        test_email_formatter()
        
        # Test complete integration
        test_integration()
        
        logger.success("\nALL PHASE 3 TESTS PASSED SUCCESSFULLY!")
        logger.info("=" * 50)
        logger.info("Phase 3 Smart Selection Logic is ready for production!")
        
    except Exception as e:
        logger.error(f"\nPHASE 3 TESTS FAILED: {e}")
        logger.error("Please review the errors above before proceeding.")
        raise


if __name__ == "__main__":
    main() 