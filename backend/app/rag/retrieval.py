import logging
import uuid
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import Chunk, Source
from app.rag.embedder import bge_embedder

logger = logging.getLogger(__name__)


class RetrievedChunk(BaseModel):
    chunk_id: uuid.UUID
    source_id: uuid.UUID
    source_name: str
    chunk_index: int
    content: str
    similarity: float
    page: Optional[int] = None
    section: Optional[str] = None


def retrieve_chunks(
    notebook_id: uuid.UUID,
    query: str,
    db: Session,
    top_k: int = 5,
) -> List[RetrievedChunk]:
    """
    Retrieves the top K relevant text chunks for a given user query in a specific notebook.

    Steps:
    1. Embed query using BGE singleton (384-dim normalized vector).
    2. Perform notebook-isolated cosine similarity search.
       - On PostgreSQL: uses pgvector `<=>` cosine_distance operator in-DB.
       - On SQLite (tests): computes cosine distance in Python.
    3. Order by cosine similarity descending.
    4. Return structured RetrievedChunk list.
    """
    if not query or not query.strip():
        return []

    if top_k <= 0:
        return []

    logger.info(f"[RAG Retrieval] Generating query embedding for: '{query[:60]}...'")
    embeddings = bge_embedder.generate_embeddings([query])
    if not embeddings:
        logger.warning("[RAG Retrieval] Failed to generate query embedding.")
        return []

    query_vector = embeddings[0]

    # Verify query embedding dimension (384-dim)
    if len(query_vector) != 384:
        raise ValueError(f"Expected 384-dimensional query embedding, got {len(query_vector)}")

    logger.info(f"[RAG Retrieval] Searching chunks for notebook {notebook_id} (top_k={top_k})")

    # Detect DB dialect to support pgvector on Postgres and fallback on SQLite test DB
    is_postgres = False
    try:
        if db.bind and db.bind.dialect.name == "postgresql":
            is_postgres = True
    except Exception:
        pass

    if is_postgres:
        results = (
            db.query(Chunk, Source, Chunk.embedding.cosine_distance(query_vector).label("distance"))
            .join(Source, Chunk.source_id == Source.id)
            .filter(Source.notebook_id == notebook_id)
            .filter(Source.status.in_(["ready", "completed"]))
            .order_by(Chunk.embedding.cosine_distance(query_vector).asc())
            .limit(top_k)
            .all()
        )
    else:
        # Fallback for SQLite / mock memory test DB
        raw_results = (
            db.query(Chunk, Source)
            .join(Source, Chunk.source_id == Source.id)
            .filter(Source.notebook_id == notebook_id)
            .filter(Source.status.in_(["ready", "completed"]))
            .all()
        )
        scored_list = []
        norm_q = (sum(a * a for a in query_vector)) ** 0.5
        for chunk, source in raw_results:
            vec = chunk.embedding
            if vec:
                dot = sum(a * b for a, b in zip(vec, query_vector))
                norm_v = (sum(a * a for a in vec)) ** 0.5
                sim = dot / (norm_v * norm_q) if norm_v and norm_q else 0.0
                dist = max(0.0, 1.0 - sim)
            else:
                dist = 1.0
            scored_list.append((chunk, source, dist))
        scored_list.sort(key=lambda x: x[2])
        results = scored_list[:top_k]

    retrieved_chunks: List[RetrievedChunk] = []
    for chunk, source, dist in results:
        dist_val = float(dist) if dist is not None else 1.0
        similarity = round(max(0.0, 1.0 - dist_val), 4)

        # Extract metadata without fabrication
        meta = chunk.chunk_metadata or {}
        page_num = meta.get("page") or meta.get("page_number")
        section_name = meta.get("section") or meta.get("heading")

        retrieved_chunks.append(
            RetrievedChunk(
                chunk_id=chunk.id,
                source_id=source.id,
                source_name=source.title or "Untitled Source",
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                similarity=similarity,
                page=int(page_num) if page_num is not None and str(page_num).isdigit() else None,
                section=str(section_name) if section_name else None,
            )
        )

    logger.info(f"[RAG Retrieval] Retrieved {len(retrieved_chunks)} chunks for notebook {notebook_id}")
    return retrieved_chunks
