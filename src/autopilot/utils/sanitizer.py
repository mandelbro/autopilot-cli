"""Secret redaction utility.

Direct port from RepEngine sanitizer.py (32 lines). Regex-based
pattern matching strips API keys, bearer tokens, and passwords
from text output before logging or display.
"""

from __future__ import annotations

import re

_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # API keys (Anthropic, OpenAI, AWS, generic)
    (re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"), "[REDACTED_API_KEY]"),
    (re.compile(r"sk-[A-Za-z0-9]{20,}"), "[REDACTED_API_KEY]"),
    (re.compile(r"AKIA[A-Z0-9]{16}"), "[REDACTED_AWS_KEY]"),
    # Bearer tokens
    (re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]{20,}"), "Bearer [REDACTED_TOKEN]"),
    # Generic tokens/keys in assignment context
    (
        re.compile(
            r"(?i)(api[_-]?key|token|secret|password|passwd|credentials)"
            r'\s*[=:]\s*["\']?[A-Za-z0-9._~+/=-]{8,}["\']?'
        ),
        r"\1=[REDACTED]",
    ),
    # GitHub tokens
    (re.compile(r"ghp_[A-Za-z0-9]{36}"), "[REDACTED_GH_TOKEN]"),
    (re.compile(r"gho_[A-Za-z0-9]{36}"), "[REDACTED_GH_TOKEN]"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{22,}"), "[REDACTED_GH_TOKEN]"),
]


def sanitize(text: str) -> str:
    """Redact secrets from *text* using known patterns."""
    result = text
    for pattern, replacement in _PATTERNS:
        result = pattern.sub(replacement, result)
    return result
