"""
Unit normalization for the audit agent.

Enables comparison of equivalent values: e.g. '2 hours' == '120 mins', '1/2"' == '0.5 in'.
"""

import re
from typing import Optional


# Time: normalize to minutes
TIME_PATTERNS = [
    (re.compile(r"(\d+(?:\.\d+)?)\s*hrs?\b", re.I), 60.0),
    (re.compile(r"(\d+(?:\.\d+)?)\s*hours?\b", re.I), 60.0),
    (re.compile(r"(\d+(?:\.\d+)?)\s*mins?\b", re.I), 1.0),
    (re.compile(r"(\d+(?:\.\d+)?)\s*minutes?\b", re.I), 1.0),
    (re.compile(r"(\d+(?:\.\d+)?)\s*secs?\b", re.I), 1.0 / 60),
    (re.compile(r"(\d+(?:\.\d+)?)\s*seconds?\b", re.I), 1.0 / 60),
]


def normalize_time_to_minutes(value: str) -> Optional[float]:
    """
    Parse a time string and return total minutes, or None if not parseable.

    Examples: "2 hours" -> 120, "120 mins" -> 120, "1.5 hr" -> 90.
    """
    s = (value or "").strip()
    if not s:
        return None
    total = 0.0
    for pattern, factor in TIME_PATTERNS:
        for m in pattern.finditer(s):
            total += float(m.group(1)) * factor
    return total if total > 0 else None


def times_equivalent(a: str, b: str, tolerance_minutes: float = 0.5) -> bool:
    """Return True if both strings represent the same duration (within tolerance)."""
    na = normalize_time_to_minutes(a)
    nb = normalize_time_to_minutes(b)
    if na is None or nb is None:
        return False
    return abs(na - nb) <= tolerance_minutes


# Length: normalize to inches (common in US construction)
LENGTH_IN_PATTERNS = [
    (re.compile(r"(\d+(?:\.\d+)?)\s*in\.?\b", re.I), 1.0),
    (re.compile(r"(\d+(?:\.\d+)?)\s*inches?\b", re.I), 1.0),
    (re.compile(r"(\d+(?:\.\d+)?)\s*ft\.?\b", re.I), 12.0),
    (re.compile(r"(\d+(?:\.\d+)?)\s*feet?\b", re.I), 12.0),
    (re.compile(r"(\d+(?:\.\d+)?)\s*mm\b", re.I), 0.0393701),
    (re.compile(r"(\d+(?:\.\d+)?)\s*cm\b", re.I), 0.393701),
    (re.compile(r"(\d+(?:\.\d+)?)\s*m\b", re.I), 39.3701),
]
# Fractional inches: 1/2", 3/4", etc.
FRAC_INCH = re.compile(r"(\d+)\s*/\s*(\d+)\s*[\"']?", re.I)


def normalize_length_to_inches(value: str) -> Optional[float]:
    """
    Parse a length string and return total inches, or None if not parseable.
    Handles fractions like 1/2" and 3/4".
    """
    s = (value or "").strip()
    if not s:
        return None
    total = 0.0
    for pattern, factor in LENGTH_IN_PATTERNS:
        for m in pattern.finditer(s):
            total += float(m.group(1)) * factor
    for m in FRAC_INCH.finditer(s):
        num, den = float(m.group(1)), float(m.group(2))
        if den:
            total += (num / den)
    return total if total > 0 else None


def lengths_equivalent(a: str, b: str, tolerance_inches: float = 0.01) -> bool:
    """Return True if both strings represent the same length (within tolerance)."""
    na = normalize_length_to_inches(a)
    nb = normalize_length_to_inches(b)
    if na is None or nb is None:
        return False
    return abs(na - nb) <= tolerance_inches


def values_equivalent(spec_value: str, submittal_value: str) -> bool:
    """
    Compare two values with unit normalization.

    - Exact match (case-insensitive strip) -> True
    - Time strings (hours, mins, etc.) -> compare in minutes
    - Length strings (in, ft, mm, etc.) -> compare in inches
    - Otherwise -> exact string match only
    """
    a = (spec_value or "").strip()
    b = (submittal_value or "").strip()
    if a.lower() == b.lower():
        return True
    if times_equivalent(a, b):
        return True
    if lengths_equivalent(a, b):
        return True
    return False
