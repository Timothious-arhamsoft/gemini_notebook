import logging
import uuid
from typing import Any, Dict, List, Optional, Sequence
import re
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.models import ChatMessage, Source
from app.rag.citations import select_answer_citations
from app.rag.context import build_context
from app.rag.embedder import DEFAULT_MODEL_NAME
from app.rag.llm import groq_service
from app.rag.retrieval import RetrievedChunk, retrieve_chunks

logger = logging.getLogger(__name__)

# How many prior chat turns (user+assistant messages) to send to the LLM.
_MAX_HISTORY_MESSAGES = 12
# How many prior user turns to fold into the retrieval embedding query.
_MAX_RETRIEVAL_USER_TURNS = 2


def _list_notebook_source_titles(notebook_id: uuid.UUID, db: Session) -> List[str]:
    sources = (
        db.query(Source)
        .filter(Source.notebook_id == notebook_id)
        .order_by(Source.created_at.asc())
        .all()
    )
    titles: List[str] = []
    for source in sources:
        title = (source.title or "").strip() or "Untitled source"
        titles.append(title)
    return titles


def format_source_inventory(titles: Sequence[str]) -> str:
    """Compact inventory text injected into the unified system prompt."""
    if not titles:
        return "No source files are currently uploaded in this notebook."
    n = len(titles)
    noun = "source file" if n == 1 else "source files"
    lines = "\n".join(f"- {title}" for title in titles)
    return f"The notebook currently has {n} {noun}:\n{lines}"


def load_conversation_history(
    notebook_id: uuid.UUID,
    db: Session,
    *,
    limit: int = _MAX_HISTORY_MESSAGES,
) -> List[Dict[str, str]]:
    """
    Load recent prior chat turns for the notebook.

    Expects the current user message to not be visible yet (caller should load
    history before inserting the new user row, or pass exclude_message_id).
    """
    if limit <= 0:
        return []

    rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.notebook_id == notebook_id)
        .filter(ChatMessage.role.in_(("user", "assistant")))
        .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        .all()
    )
    if len(rows) > limit:
        rows = rows[-limit:]
    history: List[Dict[str, str]] = []
    for row in rows:
        content = (row.content or "").strip()
        if not content:
            continue
        history.append({"role": row.role, "content": content})
    return history


def build_retrieval_query(
    current_query: str,
    conversation_history: Sequence[Dict[str, str]],
    *,
    max_prior_user_turns: int = _MAX_RETRIEVAL_USER_TURNS,
) -> str:
    """
    Build a conversation-aware retrieval query without an extra LLM rewrite call.

    Follow-ups like "What about prevention?" after a malaria question become
    more useful when prior user turns are included in the embedding text.
    """
    current = " ".join((current_query or "").split()).strip()
    if not current:
        return ""

    prior_user = [
        " ".join((turn.get("content") or "").split()).strip()
        for turn in conversation_history
        if turn.get("role") == "user"
    ]
    prior_user = [text for text in prior_user if text][-max_prior_user_turns:]
    if not prior_user:
        return current
    return " ".join([*prior_user, current])


def _empty_rag_result(answer: str, usage: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "answer": answer,
        "citations": [],
        "retrieved_evidence": [],
        "sources": [],
        "retrieved_chunks": [],
        "usage": usage,
    }

def _format_llm_error(exc: Exception) -> str:
    """Convert provider errors into user-friendly messages."""
    error_text = str(exc)

    # Groq/OpenAI-compatible 429 token/rate-limit error.
    if "429" in error_text or "rate_limit_exceeded" in error_text:
        match = re.search(
            r"try again in\s+([0-9]+(?:\.[0-9]+)?)m",
            error_text,
            re.IGNORECASE,
        )

        if match:
            minutes = max(1, round(float(match.group(1))))
            return (
                "I'm temporarily out of AI capacity. "
                f"Please try again in about {minutes} minutes."
            )

        return (
            "I'm temporarily out of AI capacity. "
            "Please try again in a few minutes."
        )

    return (
        "I couldn't generate a response right now. "
        "Please try again in a moment."
    )

def run_rag_pipeline(
    notebook_id: uuid.UUID,
    query: str,
    db: Session,
    top_k: int = 5,
    conversation_history: Optional[Sequence[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Unified chat path:
    conversation history + source inventory + (optional) retrieved chunks
    → one Groq request with a unified system prompt → answer.

    The LLM decides whether retrieved chunks, inventory, product knowledge,
    or conversation history are relevant. No regex intent router.
    """
    history = list(conversation_history) if conversation_history is not None else load_conversation_history(
        notebook_id, db
    )

    titles = _list_notebook_source_titles(notebook_id, db)
    inventory_text = format_source_inventory(titles)

    retrieval_query = build_retrieval_query(query, history)
    logger.info(
        "[RAG Pipeline] Retrieving top_%s chunks for notebook %s (retrieval_query=%r)",
        top_k,
        notebook_id,
        retrieval_query[:120],
    )

    chunks: List[RetrievedChunk] = []
    if retrieval_query:
        chunks = retrieve_chunks(
            notebook_id=notebook_id,
            query=retrieval_query,
            db=db,
            top_k=top_k,
        )

    context_str = ""
    evidence_refs: List[Dict[str, Any]] = []
    if chunks:
        context_str, evidence_refs = build_context(chunks)

    logger.info(
        "[RAG Pipeline] Invoking unified Groq generation (history=%s, sources=%s, chunks=%s)",
        len(history),
        len(titles),
        len(chunks),
    )

    usage = None
    try:
        answer, usage = groq_service.generate_answer(
            query,
            document_context=context_str or None,
            conversation_history=history,
            source_inventory=inventory_text,
            embedding_model=DEFAULT_MODEL_NAME,
        )
    except Exception as exc:
        logger.error(
            "[RAG Pipeline] Groq LLM generation failed",
            exc_info=True,
        )

        answer = _format_llm_error(exc)

        return _empty_rag_result(answer, usage)

    citations = select_answer_citations(answer, evidence_refs)

    logger.info(
        "[RAG Pipeline] Completed: %s citations from %s retrieved evidence refs",
        len(citations),
        len(evidence_refs),
    )
    return {
        "answer": answer,
        "citations": citations,
        "retrieved_evidence": evidence_refs,
        # Backward-compatible alias used by older call sites/tests
        "sources": citations,
        "retrieved_chunks": [c.model_dump() for c in chunks],
        "usage": usage,
    }
