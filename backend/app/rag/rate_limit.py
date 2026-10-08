"""User-facing helpers for Groq/OpenAI-compatible rate-limit errors."""

from __future__ import annotations

import re
from typing import Optional

# Groq formats waits like "14m52.08s", "13m8.831999999s", or sometimes seconds only.
_RETRY_AFTER_RE = re.compile(
    r"try again in\s+(?:([0-9]+(?:\.[0-9]+)?)m)?\s*(?:([0-9]+(?:\.[0-9]+)?)s)?",
    re.IGNORECASE,
)


def parse_retry_after_minutes(error_text: str) -> Optional[int]:
    """Parse Groq's retry-after phrase into whole minutes (minimum 1)."""
    match = _RETRY_AFTER_RE.search(error_text or "")
    if not match or not (match.group(1) or match.group(2)):
        return None
    minutes_part = float(match.group(1) or 0)
    seconds_part = float(match.group(2) or 0)
    return max(1, round(minutes_part + seconds_part / 60.0))


def format_capacity_error(error_text: str) -> str:
    """Friendly message when every model is rate-limited / unavailable."""
    minutes = parse_retry_after_minutes(error_text)
    if minutes is not None:
        return (
            "I'm temporarily out of AI capacity. "
            f"Please try again in about {minutes} minutes."
        )
    return (
        "I'm temporarily out of AI capacity. "
        "Please try again in a few minutes."
    )
