"""Helpers for mapping model [Source N] mentions to structured citation metadata."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Sequence

SOURCE_CITATION_RE = re.compile(r"\[Source\s+(\d+)\]", re.IGNORECASE)
# Models sometimes emit CJK / fullwidth brackets instead of ASCII [Source N]
_ALT_SOURCE_CITATION_RE = re.compile(
    r"[【［]\s*Source\s+(\d+)\s*[】］]",
    re.IGNORECASE,
)
INSUFFICIENT_INFO_PHRASE = "couldn't find enough information about that in the uploaded sources"


def normalize_citation_markers(text: str) -> str:
    """Rewrite alternate citation wrappers to canonical [Source N]."""
    if not text:
        return text
    return _ALT_SOURCE_CITATION_RE.sub(r"[Source \1]", text)


def extract_cited_indices(answer: str) -> List[int]:
    """Return unique citation indices in order of first appearance in the answer."""
    if not answer:
        return []
    answer = normalize_citation_markers(answer)
    seen: set[int] = set()
    ordered: List[int] = []
    for match in SOURCE_CITATION_RE.finditer(answer):
        idx = int(match.group(1))
        if idx not in seen:
            seen.add(idx)
            ordered.append(idx)
    return ordered


def is_insufficient_answer(answer: str) -> bool:
    return INSUFFICIENT_INFO_PHRASE in (answer or "").lower()


def select_answer_citations(
    answer: str,
    evidence_refs: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Return only evidence refs that the model actually cited via [Source N].

    Invalid indices (e.g. [Source 99] when only 3 sources exist) are ignored.
    Insufficient-context answers never produce answer citations.
    """
    if not evidence_refs or is_insufficient_answer(answer):
        return []

    by_index = {
        int(ref["citation_index"]): ref
        for ref in evidence_refs
        if ref.get("citation_index") is not None
    }
    citations: List[Dict[str, Any]] = []
    for idx in extract_cited_indices(answer):
        ref = by_index.get(idx)
        if ref is not None:
            citations.append(dict(ref))
    return citations
