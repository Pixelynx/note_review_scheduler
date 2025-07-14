"""Validation utilities."""

from __future__ import annotations

import re
from urllib.parse import urlparse


def validate_email(email: str) -> bool:
    """Validate email address format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_url(url: str) -> bool:
    """Validate URL format."""
    try:
        result = urlparse(url)
        return bool(result.scheme and result.netloc)
    except Exception:
        return False


def validate_time_format(time_str: str) -> bool:
    """Validate time format (HH:MM)."""
    pattern = r'^([01]?[0-9]|2[0-3]):([0-5][0-9])$'
    return bool(re.match(pattern, time_str)) 