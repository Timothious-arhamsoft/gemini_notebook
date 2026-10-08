import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.db.models import Chunk, Source
from app.rag.embedder import bge_embedder
from app.rag.ingestion import ingestion_service
from app.rag.splitter import split_text

logger = logging.getLogger(__name__)

PROCESSING_STATUSES = frozenset(
    {"pending", "processing", "analyzing", "chunking", "embedding"}
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _mark_failed(source: Source, db: Session, exc: Exception, timings: Dict[str, Any]) -> Source:
    source.status = "failed"
    source.error_message = str(exc)
    source.processing_failed_at = _utcnow()
    source.processing_timings = timings
    db.commit()
    db.refresh(source)
    return source


def run_runtime_ingestion_pipeline(source_id: uuid.UUID, db: Session) -> Source:
    """
    Executes the complete runtime RAG ingestion pipeline for a document source.
    Records per-stage timings on the Source record.
    """
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise ValueError(f"Source with id {source_id} not found.")

    # Trust existing Ready/completed state — never re-embed on open/refresh.
    if source.status in ("completed", "ready"):
        logger.info(
            "[RAG Pipeline] Source %s already completed — skipping re-ingestion.",
            source_id,
        )
        return source

    pipeline_started = time.perf_counter()
    timings: Dict[str, Any] = {}

    if not source.processing_started_at:
        source.processing_started_at = _utcnow()
    source.processing_completed_at = None
    source.processing_failed_at = None
    source.status = "processing"
    db.commit()

    file_path = Path(source.file_path) if source.file_path else None
    if file_path and not file_path.exists() and str(source.file_path).startswith("/app/"):
        backend_dir = Path(__file__).resolve().parent.parent.parent
        rel_path = str(source.file_path)[5:]
        file_path = backend_dir / rel_path

    if not file_path or not file_path.exists():
        source.status = "failed"
        source.error_message = f"Source file does not exist: {source.file_path}"
        source.processing_failed_at = _utcnow()
        timings["total_s"] = round(time.perf_counter() - pipeline_started, 3)
        source.processing_timings = timings
        db.commit()
        return source

    try:
        upload_started = time.perf_counter()
        timings["upload_s"] = round(time.perf_counter() - upload_started, 3)

        logger.info("[RAG Pipeline] Step 1 & 2: Extracting & analyzing source %s", source_id)
        source.status = "analyzing"
        db.commit()

        parse_started = time.perf_counter()
        parsed_result = ingestion_service.parse(
            file_path=file_path,
            document_id=source.id,
        )
        timings["parse_and_analysis_s"] = round(time.perf_counter() - parse_started, 3)

        extracted_text = parsed_result.get("full_text", "")
        analysis = parsed_result.get("analysis", {})
        recommended_chunk_size = analysis.get("recommended_chunk_size", 800)

        source.content_text = extracted_text
        source.token_count = len(extracted_text.split()) if extracted_text else 0
        source.analysis = analysis

        if not extracted_text or not extracted_text.strip():
            source.status = "completed"
            source.error_message = "Warning: Document contains no text content."
            source.processing_completed_at = _utcnow()
            timings["total_s"] = round(time.perf_counter() - pipeline_started, 3)
            source.processing_timings = timings
            db.commit()
            return source

        logger.info(
            "[RAG Pipeline] Step 3: Chunking source %s with chunk_size=%s",
            source_id,
            recommended_chunk_size,
        )
        source.status = "chunking"
        db.commit()

        chunk_started = time.perf_counter()
        chunk_overlap = max(0, int(recommended_chunk_size * 0.2))
        text_chunks = split_text(
            text=extracted_text,
            chunk_size=recommended_chunk_size,
            chunk_overlap=chunk_overlap,
        )
        timings["chunking_s"] = round(time.perf_counter() - chunk_started, 3)
        timings["chunk_count"] = len(text_chunks)

        db.query(Chunk).filter(Chunk.source_id == source.id).delete()
        db.commit()

        if not text_chunks:
            source.status = "completed"
            source.processing_completed_at = _utcnow()
            timings["total_s"] = round(time.perf_counter() - pipeline_started, 3)
            source.processing_timings = timings
            db.commit()
            return source

        logger.info("[RAG Pipeline] Step 4: Generating embeddings for %s chunks", len(text_chunks))
        source.status = "embedding"
        db.commit()

        embed_started = time.perf_counter()
        embeddings, embed_metrics = bge_embedder.generate_embeddings_with_metrics(text_chunks)
        timings["embedding_s"] = round(time.perf_counter() - embed_started, 3)
        timings["embedding_model_load_s"] = embed_metrics.get("model_load_s", 0.0)
        timings["embedding_encode_s"] = embed_metrics.get("encode_s", 0.0)

        logger.info("[RAG Pipeline] Step 5: Storing %s chunks in pgvector", len(text_chunks))
        save_started = time.perf_counter()
        db_chunks = []
        for idx, (chunk_text, emb) in enumerate(zip(text_chunks, embeddings)):
            chunk_obj = Chunk(
                id=uuid.uuid4(),
                source_id=source.id,
                chunk_index=idx,
                content=chunk_text,
                embedding=emb,
                chunk_metadata={
                    "chunk_size": recommended_chunk_size,
                    "chunk_overlap": chunk_overlap,
                    "char_length": len(chunk_text),
                    "source_title": source.title,
                },
            )
            db_chunks.append(chunk_obj)

        db.add_all(db_chunks)
        timings["database_save_s"] = round(time.perf_counter() - save_started, 3)
        timings["total_s"] = round(time.perf_counter() - pipeline_started, 3)

        source.status = "completed"
        source.error_message = None
        source.processing_completed_at = _utcnow()
        source.processing_timings = timings
        db.commit()
        db.refresh(source)

        logger.info(
            "[RAG Pipeline] Completed source %s in %.2fs (embed=%.2fs, model_load=%.2fs)",
            source.id,
            timings["total_s"],
            timings.get("embedding_s", 0),
            timings.get("embedding_model_load_s", 0),
        )

    except Exception as exc:
        logger.error("[RAG Pipeline] Ingestion failed for source %s: %s", source.id, exc, exc_info=True)
        timings["total_s"] = round(time.perf_counter() - pipeline_started, 3)
        return _mark_failed(source, db, exc, timings)

    return source
