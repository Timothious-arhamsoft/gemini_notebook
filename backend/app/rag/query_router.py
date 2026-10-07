"""Classify user chat messages before retrieval / LLM grounding."""

from __future__ import annotations

import re
from typing import Literal

MessageRoute = Literal["conversational", "source_inventory", "rag"]

# Short meta-questions about notebook uploads — answered from Source rows, not RAG chunks.
_SOURCE_INVENTORY_PATTERNS = (
    re.compile(r"\bwhat\s+source\s+file", re.I),
    re.compile(r"\bwhat\s+source\s+files?\b", re.I),
    re.compile(r"\bwhich\s+source\s+files?\b", re.I),
    re.compile(r"\bwhich\s+files?\s+(are\s+)?available\b", re.I),
    re.compile(r"\bwhich\s+(files?|documents?)\s+(do\s+i|have|are)\b", re.I),
    re.compile(r"\bwhat\s+(files?|documents?)\s+(do\s+i|have|are|you)\b", re.I),
    re.compile(r"\bwhat\s+documents?\s+have\s+i\s+uploaded\b", re.I),
    re.compile(r"\bhow\s+many\s+(sources?|files?|documents?)\b", re.I),
    re.compile(r"\blist\s+(my\s+|the\s+)?(sources?|files?|documents?)\b", re.I),
    re.compile(r"\b(sources?|files?|documents?)\s+(do\s+)?you\s+have\b", re.I),
    re.compile(r"\bwhat\s+have\s+i\s+uploaded\b", re.I),
    re.compile(r"\bfiles?\s+in\s+this\s+notebook\b", re.I),
    re.compile(r"\bdocuments?\s+in\s+this\s+notebook\b", re.I),
)

# Avoid treating content questions that merely mention "source/file" as inventory queries.
_INVENTORY_EXCLUDE_MARKERS = (
    "say about",
    "says about",
    "according to",
    "in the document",
    "from the document",
    "from the source",
    "what does",
    "how does",
    "why does",
)

_CONVERSATIONAL_EXACT = frozenset(
    {
        "hi",
        "hello",
        "hey",
        "howdy",
        "thanks",
        "thank you",
        "thx",
        "bye",
        "goodbye",
        "yo",
        "sup",
    }
)

_CONVERSATIONAL_PATTERNS = (
    re.compile(r"^(hi|hello|hey|howdy)\b", re.I),
    re.compile(r"^good\s+(morning|afternoon|evening)\b", re.I),
    re.compile(r"\bhow\s+are\s+you\b", re.I),
    re.compile(r"\bhow(?:'s|\s+is)\s+it\s+going\b", re.I),
    re.compile(r"\btell\s+me\s+about\s+yourself\b", re.I),
    re.compile(r"\btell\s+me\s+about\s+you\b", re.I),
    re.compile(r"\bwho\s+are\s+you\b", re.I),
    re.compile(r"\bwhat\s+are\s+you\b", re.I),
    re.compile(r"\bwhat\s+can\s+you\s+do\b", re.I),
    re.compile(r"\bwhat\s+is\s+notegenio\b", re.I),
    re.compile(r"^(thanks|thank\s+you|thx)\b", re.I),
    re.compile(r"^(bye|goodbye|see\s+you)\b", re.I),
)

# Document-style questions must stay on the RAG path even if they look chatty.
_RAG_OVERRIDE_MARKERS = (
    "document",
    "documents",
    "source",
    "sources",
    "upload",
    "uploaded",
    "notebook",
    "file",
    "files",
    "pdf",
    "chunk",
    "cite",
    "summary",
    "summarize",
    "according to",
    "transmission",
    " say about",
    " says about",
)


def _normalize_query(query: str) -> str:
    return " ".join((query or "").strip().split())


def is_source_inventory_query(query: str) -> bool:
    """True for short questions about which files/sources exist in the notebook."""
    q = _normalize_query(query)
    if not q or len(q) > 160:
        return False
    lower = q.lower()
    if any(marker in lower for marker in _INVENTORY_EXCLUDE_MARKERS):
        return False
    return any(pattern.search(q) for pattern in _SOURCE_INVENTORY_PATTERNS)


def is_conversational_query(query: str) -> bool:
    """True for greetings and meta chat about the assistant — not document Q&A."""
    q = _normalize_query(query)
    if not q or len(q) > 120:
        return False

    lower = q.lower()
    if any(marker in lower for marker in _RAG_OVERRIDE_MARKERS):
        return False

    stripped = lower.rstrip("?!. ")
    if stripped in _CONVERSATIONAL_EXACT:
        return True

    return any(pattern.search(q) for pattern in _CONVERSATIONAL_PATTERNS)


def classify_user_message(query: str) -> MessageRoute:
    if is_source_inventory_query(query):
        return "source_inventory"
    if is_conversational_query(query):
        return "conversational"
    return "rag"
