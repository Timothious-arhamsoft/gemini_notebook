import logging
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models import Source
from app.rag.citations import select_answer_citations
from app.rag.context import build_context
from app.rag.llm import groq_service
from app.rag.query_router import classify_user_message
from app.rag.retrieval import RetrievedChunk, retrieve_chunks

logger = logging.getLogger(__name__)


def _format_source_inventory_answer(titles: List[str]) -> str:
    if not titles:
        return (
            "You currently have no source files uploaded in this notebook."
        )
    n = len(titles)
    noun = "source file" if n == 1 else "source files"
    lines = "\n".join(f"- {title}" for title in titles)
    return f"You currently have {n} {noun}:\n\n{lines}"


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


def _empty_rag_result(answer: str, usage: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "answer": answer,
        "citations": [],
        "retrieved_evidence": [],
        "sources": [],
        "retrieved_chunks": [],
        "usage": usage,
    }


def run_rag_pipeline(
    notebook_id: uuid.UUID,
    query: str,
    db: Session,
    top_k: int = 5,
) -> Dict[str, Any]:
    """
    Executes chat routing then either:
    - conversational reply (no retrieval),
    - source inventory from Source metadata (no retrieval), or
    - full RAG: retrieve → context → grounded Groq → citations.
    """
    route = classify_user_message(query)

    if route == "source_inventory":
        titles = _list_notebook_source_titles(notebook_id, db)
        answer = _format_source_inventory_answer(titles)
        logger.info(
            "[RAG Pipeline] Source-inventory query for notebook %s (%s files) — skipping retrieval",
            notebook_id,
            len(titles),
        )
        return _empty_rag_result(answer)

    if route == "conversational":
        logger.info(
            "[RAG Pipeline] Conversational query for notebook %s — skipping retrieval",
            notebook_id,
        )
        usage = None
        try:
            answer, usage = groq_service.generate_conversational_answer(query=query)
        except Exception as exc:
            logger.error(f"[RAG Pipeline] Conversational LLM failed: {exc}")
            answer = "Hello! I'm the NoteGenio assistant. Ask me anything about your uploaded documents."
        return _empty_rag_result(answer, usage)

    logger.info(f"[RAG Pipeline] Step 1: Retrieving top_{top_k} chunks for query in notebook {notebook_id}")
    chunks: List[RetrievedChunk] = retrieve_chunks(
        notebook_id=notebook_id,
        query=query,
        db=db,
        top_k=top_k,
    )

    if not chunks:
        logger.info(f"[RAG Pipeline] No chunks found for notebook {notebook_id}")
        return _empty_rag_result(
            "I couldn't find enough information about that in the uploaded sources."
        )

    logger.info(f"[RAG Pipeline] Step 2: Building prompt context from {len(chunks)} chunks")
    context_str, evidence_refs = build_context(chunks)

    logger.info("[RAG Pipeline] Step 3: Invoking Groq LLM for grounded answer generation")
    usage = None
    try:
        answer, usage = groq_service.generate_grounded_answer(
            query=query,
            context_str=context_str,
        )
    except Exception as exc:
        logger.error(f"[RAG Pipeline] Groq LLM generation failed: {exc}")
        answer = f"Error generating LLM response: {str(exc)}"

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
