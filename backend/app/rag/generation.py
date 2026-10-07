import logging
import uuid
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.rag.citations import select_answer_citations
from app.rag.context import build_context
from app.rag.llm import groq_service
from app.rag.retrieval import RetrievedChunk, retrieve_chunks

logger = logging.getLogger(__name__)


def run_rag_pipeline(
    notebook_id: uuid.UUID,
    query: str,
    db: Session,
    top_k: int = 5,
) -> Dict[str, Any]:
    """
    Executes the end-to-end RAG retrieval & generation pipeline:

    query
      ↓
    retrieve top-k chunks (notebook scoped via pgvector cosine distance)
      ↓
    build structured context & evidence metadata
      ↓
    Groq LLM (gpt-oss-120b) call with grounded system prompt
      ↓
    answer + answer citations + retrieved evidence + usage
    """
    logger.info(f"[RAG Pipeline] Step 1: Retrieving top_{top_k} chunks for query in notebook {notebook_id}")
    chunks: List[RetrievedChunk] = retrieve_chunks(
        notebook_id=notebook_id,
        query=query,
        db=db,
        top_k=top_k,
    )

    if not chunks:
        logger.info(f"[RAG Pipeline] No chunks found for notebook {notebook_id}")
        return {
            "answer": "I couldn't find enough information about that in the uploaded sources.",
            "citations": [],
            "retrieved_evidence": [],
            "sources": [],
            "retrieved_chunks": [],
            "usage": None,
        }

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
