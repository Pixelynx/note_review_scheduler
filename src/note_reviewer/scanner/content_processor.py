"""
Content processing utilities for advanced note analysis.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse

import requests
from loguru import logger


@dataclass(frozen=True)
class LinkValidationResult:
    """Result of validating a link."""
    url: str
    is_valid: bool
    status_code: Optional[int]
    error_message: Optional[str]
    response_time_ms: Optional[float]


class ContentProcessor:
    """Advanced content processing for notes."""
    
    def __init__(self, enable_link_validation: bool = False) -> None:
        """Initialize content processor.
        
        Args:
            enable_link_validation: Whether to validate links (requires network)
        """
        self.enable_link_validation = enable_link_validation
        logger.info(f"ContentProcessor initialized - link validation: {enable_link_validation}")
    
    def generate_content_summary(self, content: str, max_length: int = 200) -> Optional[str]:
        """Generate a brief summary of content."""
        if not content.strip():
            return None
        
        # Remove markdown formatting for cleaner summary
        clean_content = self._clean_markdown(content)
        
        # Split into sentences
        sentences = re.split(r'[.!?]+', clean_content)
        clean_sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        
        if not clean_sentences:
            return None
        
        # Build summary within length limit
        summary_parts: List[str] = []
        total_length = 0
        
        for sentence in clean_sentences[:3]:
            if total_length + len(sentence) > max_length:
                break
            summary_parts.append(sentence)
            total_length += len(sentence)
        
        if summary_parts:
            summary = '. '.join(summary_parts) + '.'
            return summary if len(summary) <= max_length else summary[:max_length-3] + '...'
        
        return None
    
    def categorize_content(self, content: str, tags: Set[str]) -> List[str]:
        """Categorize content based on keywords and tags."""
        categories: List[str] = []
        content_lower = content.lower()
        
        # Technical categories
        tech_keywords = ['code', 'programming', 'development', 'api', 'database', 'algorithm']
        if any(keyword in content_lower for keyword in tech_keywords) or any('tech' in tag.lower() for tag in tags):
            categories.append('Technical')
        
        # Project categories
        project_keywords = ['project', 'deadline', 'milestone', 'task', 'sprint']
        if any(keyword in content_lower for keyword in project_keywords) or any('project' in tag.lower() for tag in tags):
            categories.append('Project')
        
        # Learning categories
        learning_keywords = ['learn', 'study', 'course', 'tutorial', 'education']
        if any(keyword in content_lower for keyword in learning_keywords) or any('learn' in tag.lower() for tag in tags):
            categories.append('Learning')
        
        # Personal categories
        personal_keywords = ['personal', 'goal', 'habit', 'reflection']
        if any(keyword in content_lower for keyword in personal_keywords) or any('personal' in tag.lower() for tag in tags):
            categories.append('Personal')
        
        # Meeting categories
        meeting_keywords = ['meeting', 'agenda', 'attendees', 'action items']
        if any(keyword in content_lower for keyword in meeting_keywords) or any('meeting' in tag.lower() for tag in tags):
            categories.append('Meeting')
        
        return categories if categories else ['General']
    
    def extract_key_phrases(self, content: str, max_phrases: int = 10) -> List[str]:
        """Extract key phrases from content."""
        # Simple keyword extraction based on frequency and context
        clean_content = self._clean_markdown(content)
        
        # Find potential key phrases (2-4 words)
        phrase_pattern = r'\b(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b'
        phrases = re.findall(phrase_pattern, clean_content)
        
        # Count frequency
        phrase_counts: Dict[str, int] = {}
        for phrase in phrases:
            phrase_counts[phrase] = phrase_counts.get(phrase, 0) + 1
        
        # Sort by frequency and return top phrases
        sorted_phrases = sorted(phrase_counts.items(), key=lambda x: x[1], reverse=True)
        return [phrase for phrase, _ in sorted_phrases[:max_phrases]]
    
    def _clean_markdown(self, content: str) -> str:
        """Remove markdown formatting for text analysis."""
        # Remove headers
        content = re.sub(r'^#+\s+', '', content, flags=re.MULTILINE)
        
        # Remove bold/italic
        content = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', content)
        content = re.sub(r'_{1,2}([^_]+)_{1,2}', r'\1', content)
        
        # Remove links
        content = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', content)
        
        # Remove code blocks
        content = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
        content = re.sub(r'`([^`]+)`', r'\1', content)
        
        # Remove extra whitespace
        content = re.sub(r'\s+', ' ', content)
        
        return content.strip()


class TagExtractor:
    """Extract and normalize tags from content."""
    
    def __init__(self) -> None:
        """Initialize tag extractor."""
        logger.debug("TagExtractor initialized")
    
    def extract_all_tags(self, content: str, file_format: str) -> Set[str]:
        """Extract all types of tags from content."""
        tags: Set[str] = set()
        
        # Common tag patterns
        tags.update(self._extract_hashtags(content))
        tags.update(self._extract_mentions(content))
        
        # Format-specific tags
        if file_format == 'markdown':
            tags.update(self._extract_yaml_tags(content))
        elif file_format == 'org-mode':
            tags.update(self._extract_org_tags(content))
        
        # Normalize tags
        normalized_tags = {self._normalize_tag(tag) for tag in tags}
        return {tag for tag in normalized_tags if tag}  # Remove empty strings
    
    def _extract_hashtags(self, content: str) -> Set[str]:
        """Extract #hashtag style tags."""
        return set(re.findall(r'#(\w+)', content))
    
    def _extract_mentions(self, content: str) -> Set[str]:
        """Extract @mention style tags."""
        return set(re.findall(r'@(\w+)', content))
    
    def _extract_yaml_tags(self, content: str) -> Set[str]:
        """Extract tags from YAML frontmatter."""
        tags: Set[str] = set()
        
        frontmatter = re.search(r'^---\s*\n(.*?)\n---', content, re.DOTALL | re.MULTILINE)
        if not frontmatter:
            return tags
        
        yaml_content = frontmatter.group(1)
        
        # Look for tags: line
        tag_match = re.search(r'^tags:\s*(.+)', yaml_content, re.MULTILINE)
        if tag_match:
            tag_value = tag_match.group(1).strip()
            
            # Handle array format: [tag1, tag2, tag3]
            if tag_value.startswith('[') and tag_value.endswith(']'):
                tag_content = tag_value[1:-1]
                tag_list = [tag.strip().strip('"\'') for tag in tag_content.split(',')]
            else:
                # Handle comma-separated: tag1, tag2, tag3
                tag_list = [tag.strip() for tag in tag_value.split(',')]
            
            tags.update(tag for tag in tag_list if tag)
        
        return tags
    
    def _extract_org_tags(self, content: str) -> Set[str]:
        """Extract tags from Org-mode format."""
        tags: Set[str] = set()
        
        # #+TAGS: directive
        tag_matches = re.findall(r'^\s*#\+TAGS:\s*(.+)', content, re.MULTILINE)
        for match in tag_matches:
            tag_list = [tag.strip() for tag in match.split()]
            tags.update(tag_list)
        
        # :tag: format
        inline_tags = re.findall(r':(\w+):', content)
        tags.update(inline_tags)
        
        return tags
    
    def _normalize_tag(self, tag: str) -> str:
        """Normalize tag format."""
        # Convert to lowercase
        tag = tag.lower()
        
        # Remove special characters
        tag = re.sub(r'[^a-z0-9_-]', '', tag)
        
        # Remove leading/trailing hyphens and underscores
        tag = tag.strip('-_')
        
        return tag


class LinkValidator:
    """Validate links found in notes."""
    
    def __init__(self, timeout_seconds: float = 5.0) -> None:
        """Initialize link validator.
        
        Args:
            timeout_seconds: Request timeout for link validation
        """
        self.timeout = timeout_seconds
        logger.info(f"LinkValidator initialized with {timeout_seconds}s timeout")
    
    def validate_links(self, links: List[str]) -> List[LinkValidationResult]:
        """Validate a list of links.
        
        Args:
            links: List of URLs to validate
            
        Returns:
            List of validation results
        """
        results: List[LinkValidationResult] = []
        
        for url in links:
            result = self.validate_link(url)
            results.append(result)
        
        return results
    
    def validate_link(self, url: str) -> LinkValidationResult:
        """Validate a single link.
        
        Args:
            url: URL to validate
            
        Returns:
            LinkValidationResult with validation status
        """
        # Basic URL format validation
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return LinkValidationResult(
                url=url,
                is_valid=False,
                status_code=None,
                error_message="Invalid URL format",
                response_time_ms=None
            )
        
        # Skip validation for non-HTTP(S) URLs
        if parsed.scheme not in ('http', 'https'):
            return LinkValidationResult(
                url=url,
                is_valid=True,  # Assume valid for non-HTTP URLs
                status_code=None,
                error_message=None,
                response_time_ms=None
            )
        
        # Perform HTTP validation
        try:
            start_time = time.time()
            
            response = requests.head(url, timeout=self.timeout, allow_redirects=True)
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            is_valid = response.status_code < 400
            
            return LinkValidationResult(
                url=url,
                is_valid=is_valid,
                status_code=response.status_code,
                error_message=None if is_valid else f"HTTP {response.status_code}",
                response_time_ms=response_time
            )
            
        except requests.exceptions.RequestException as e:
            return LinkValidationResult(
                url=url,
                is_valid=False,
                status_code=None,
                error_message=str(e),
                response_time_ms=None
            ) 