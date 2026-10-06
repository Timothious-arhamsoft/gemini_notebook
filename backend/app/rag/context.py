import logging
from typing import Dict, List, Tuple
from app.rag.retrieval import RetrievedChunk

logger = logging.getLogger(__name__)


def build_context(retrieved_chunks: List[RetrievedChunk]) -> Tuple[str, List[Dict[str, str]]]:
    """
    Converts a list of retrieved chunks into:
    1. Formatted prompt context string with numbered [Source N] headers.
    2. Citation metadata list suitable for storing in ChatMessage.source_refs.
    """
    if not retrieved_chunks:
        return "", []

    context_blocks: List[str] = []
    source_refs: List[Dict[str, str]] = []

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

        # Build citation for UI sidebar highlighting
        excerpt = chunk.content[:300] + "..." if len(chunk.content) > 300 else chunk.content
        source_refs.append(
            {
                "source_id": str(chunk.source_id),
                "source_title": chunk.source_name,
                "excerpt": excerpt,
            }
        )

    context_str = "\n\n---\n\n".join(context_blocks)
    logger.info(f"[RAG Context] Built context string with {len(retrieved_chunks)} source blocks")
    return context_str, source_refs
