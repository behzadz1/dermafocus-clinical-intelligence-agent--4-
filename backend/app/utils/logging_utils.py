"""
Logging utilities (PHI redaction).
"""

from __future__ import annotations

import re


PHI_PATTERNS = [
    (r"\b\d{3}-\d{2}-\d{4}\b", "[SSN_REDACTED]"),  # SSN
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL_REDACTED]"),
    (r"\b\d{10,11}\b", "[PHONE_REDACTED]"),
    (r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", "[DATE_REDACTED]"),
    (r"\b\d{4}-\d{2}-\d{2}\b", "[DATE_REDACTED]"),
]


def redact_phi(text: str) -> str:
    """Redact potential PHI from text for safe logging."""
    if not text:
        return text
    for pattern, replacement in PHI_PATTERNS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text
