import math
from typing import Any, Dict

MIN_RECOMMENDED_CHUNK_SIZE = 400
MAX_RECOMMENDED_CHUNK_SIZE = 2000
DEFAULT_CHUNK_SIZE = 800


def recommend_recursive_chunk_size(stats: Dict[str, Any]) -> int:
    """
    Deterministically recommend a character-based chunk size suitable for
    future RecursiveCharacterTextSplitter.

    Uses paragraph distribution metrics (P90, P95, median, average) while
    protecting against single large outlier paragraphs.

    Args:
        stats: Dictionary containing paragraph/text-block distribution metrics:
            - total_characters: int
            - median_paragraph_chars: int or float
            - p75_paragraph_chars: int or float
            - p90_paragraph_chars: int or float
            - p95_paragraph_chars: int or float
            - avg_paragraph_chars: int or float

    Returns:
        int: Recommended chunk size in characters (bounded between 400 and 2000).
    """
    total_chars = stats.get("total_characters", 0)
    if total_chars <= 0:
        return DEFAULT_CHUNK_SIZE

    median_p = stats.get("median_paragraph_chars") or 0
    p90_p = stats.get("p90_paragraph_chars") or 0
    p95_p = stats.get("p95_paragraph_chars") or 0
    avg_p = stats.get("avg_paragraph_chars") or 0

    # Short document fallback
    if total_chars < 800:
        raw_size = max(total_chars, MIN_RECOMMENDED_CHUNK_SIZE)
        return min(raw_size, DEFAULT_CHUNK_SIZE)

    # Base target selection based on paragraph distribution
    # We aim to fit roughly 2-4 typical paragraphs or 1-2 large paragraphs per chunk
    if p90_p > 0:
        # Scale recommendation around 1.5x P90 or 3x Median to capture paragraph context smoothly
        target_size = max(p90_p * 1.5, median_p * 3.0, avg_p * 2.5)
    elif median_p > 0:
        target_size = max(median_p * 3.0, avg_p * 2.5)
    else:
        target_size = DEFAULT_CHUNK_SIZE

    # Apply default baseline floor/ceiling prior to rounding
    target_size = max(target_size, 600)

    # Round to nearest 50 characters
    rounded_size = int(round(target_size / 50.0) * 50)

    # Enforce strict bounds [400, 2000]
    final_size = max(MIN_RECOMMENDED_CHUNK_SIZE, min(rounded_size, MAX_RECOMMENDED_CHUNK_SIZE))
    return final_size
