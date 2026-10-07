import logging
from typing import Any, Dict, List, Tuple

from app.rag.retrieval import RetrievedChunk

logger = logging.getLogger(__name__)


def _chunk_to_evidence_ref(idx: int, chunk: RetrievedChunk) -> Dict[str, Any]:
    """Build a stable evidence/citation ref keyed by [Source N] index."""
    content = chunk.content.strip()
    excerpt = content[:300] + "..." if len(content) > 300 else content
    return {
        "id": f"citation-{idx}",
        "citation_index": idx,
        "source_id": str(chunk.source_id),
        "source_title": chunk.source_name,
        "source_name": chunk.source_name,
        "chunk_id": str(chunk.chunk_id),
        "chunk_index": chunk.chunk_index,
        "page": chunk.page,
        "section": chunk.section,
        "excerpt": excerpt,
        "content": content,
        "similarity": chunk.similarity,
    }


def build_context(retrieved_chunks: List[RetrievedChunk]) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Converts a list of retrieved chunks into:
    1. Formatted prompt context string with numbered [Source N] headers.
    2. Evidence metadata list (retrieval order = citation_index).
    """
    if not retrieved_chunks:
        return "", []

    context_blocks: List[str] = []
    evidence_refs: List[Dict[str, Any]] = []

    for idx, chunk in enumerate(retrieved_chunks, start=1):
        lines: List[str] = [f"[Source {idx}]", f"Document: {chunk.source_name}"]

        if chunk.page is not None:
            lines.append(f"Page: {chunk.page}")
        if chunk.section:
            lines.append(f"Section: {chunk.section}")

        lines.append(f"Chunk: {chunk.chunk_index}")
        lines.append("")
        lines.append(chunk.content.strip())

        context_blocks.append("\n".join(lines))
        evidence_refs.append(_chunk_to_evidence_ref(idx, chunk))

    context_str = "\n\n---\n\n".join(context_blocks)
    logger.info(f"[RAG Context] Built context string with {len(retrieved_chunks)} source blocks")
    return context_str, evidence_refs
