import logging
import uuid
from pathlib import Path
from typing import Any, Dict
from sqlalchemy.orm import Session

from app.models import Source, Chunk
from app.rag.ingestion import ingestion_service
from app.rag.splitter import split_text
from app.rag.embedder import bge_embedder

logger = logging.getLogger(__name__)


def run_runtime_ingestion_pipeline(source_id: uuid.UUID, db: Session) -> Source:
    """
    Executes the complete runtime RAG ingestion pipeline for a document source:
    
    User uploads document
           ↓
    Document extraction (PDF/DOCX/TXT/MD parsing)
           ↓
    Runtime document analysis (recommend_chunk_size for THIS document)
           ↓
    Recursive Character Text Splitting
           ↓
    Generate BGE embeddings (384-dim) for the chunks
           ↓
    Store chunks + embeddings in PostgreSQL/pgvector
           ↓
    Mark source as completed
    """
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise ValueError(f"Source with id {source_id} not found.")

    file_path = Path(source.file_path) if source.file_path else None
    if file_path and not file_path.exists() and str(source.file_path).startswith("/app/"):
        backend_dir = Path(__file__).resolve().parent.parent.parent
        rel_path = str(source.file_path)[5:]  # strip '/app/'
        file_path = backend_dir / rel_path

    if not file_path or not file_path.exists():
        source.status = "failed"
        source.error_message = f"Source file does not exist: {source.file_path}"
        db.commit()
        return source

    try:
        # Step 1 & 2: Document extraction & analysis
        logger.info(f"[RAG Pipeline] Step 1 & 2: Extracting & analyzing source {source_id}")
        source.status = "analyzing"
        db.commit()

        parsed_result = ingestion_service.parse(
            file_path=file_path,
            document_id=source.id,
        )

        extracted_text = parsed_result.get("full_text", "")
        analysis = parsed_result.get("analysis", {})
        
        # Determine recommended chunk size for THIS document
        recommended_chunk_size = analysis.get("recommended_chunk_size", 800)
        
        source.content_text = extracted_text
        source.token_count = len(extracted_text.split()) if extracted_text else 0
        source.analysis = analysis

        if not extracted_text or not extracted_text.strip():
            source.status = "completed"
            source.error_message = "Warning: Document contains no text content."
            db.commit()
            return source

        # Step 3: Recursive Character Text Splitting
        logger.info(f"[RAG Pipeline] Step 3: Chunking source {source_id} with chunk_size={recommended_chunk_size}")
        source.status = "chunking"
        db.commit()

        chunk_overlap = max(0, int(recommended_chunk_size * 0.2))
        text_chunks = split_text(
            text=extracted_text,
            chunk_size=recommended_chunk_size,
            chunk_overlap=chunk_overlap,
        )

        # Delete any pre-existing chunks for this source if re-processing
        db.query(Chunk).filter(Chunk.source_id == source.id).delete()
        db.commit()

        if not text_chunks:
            source.status = "completed"
            db.commit()
            return source

        # Step 4: Generate embeddings for chunks
        logger.info(f"[RAG Pipeline] Step 4: Generating embeddings for {len(text_chunks)} chunks")
        source.status = "embedding"
        db.commit()

        embeddings = bge_embedder.generate_embeddings(text_chunks)

        # Step 5: Store chunks + embeddings in PostgreSQL/pgvector
        logger.info(f"[RAG Pipeline] Step 5: Storing {len(text_chunks)} chunks in pgvector")
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
                }
            )
            db_chunks.append(chunk_obj)

        db.add_all(db_chunks)
        
        # Step 6: Mark source as completed
        source.status = "completed"
        source.error_message = None
        db.commit()
        db.refresh(source)
        logger.info(f"[RAG Pipeline] Successfully completed ingestion for source {source.id}")

    except Exception as exc:
        logger.error(f"[RAG Pipeline] Ingestion failed for source {source.id}: {exc}", exc_info=True)
        source.status = "failed"
        source.error_message = str(exc)
        db.commit()
        db.refresh(source)

    return source
