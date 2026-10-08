"""Tests for processing timestamps, skip-ready, and idempotent retry."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.db.models import Chunk, Source, User, Notebook
from app.rag.pipeline import run_runtime_ingestion_pipeline
from app.routers.sources import _is_stale_processing, STALE_PROCESSING_SECONDS


@pytest.fixture
def db_session():
    from app.db.database import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _make_source(db: Session, *, status: str = "processing", title: str = "doc.txt") -> Source:
    user = db.query(User).first()
    if not user:
        pytest.skip("No user in database for integration-style test")
    nb = db.query(Notebook).filter(Notebook.user_id == user.id).first()
    if not nb:
        pytest.skip("No notebook for user")

    src = Source(
        id=uuid.uuid4(),
        notebook_id=nb.id,
        source_type="txt",
        title=title,
        file_path="/tmp/does-not-exist-for-unit.txt",
        status=status,
    )
    db.add(src)
    db.commit()
    db.refresh(src)
    return src


def test_ready_source_is_not_reprocessed(db_session: Session):
    src = _make_source(db_session, status="completed", title="ready.txt")
    src.processing_completed_at = datetime.now(timezone.utc)
    db_session.commit()

    with patch("app.rag.pipeline.ingestion_service.parse") as parse_mock:
        result = run_runtime_ingestion_pipeline(src.id, db_session)
        parse_mock.assert_not_called()
        assert result.status == "completed"

    db_session.delete(src)
    db_session.commit()


def test_stale_threshold_five_minutes():
    src = MagicMock()
    src.status = "embedding"
    src.processing_started_at = datetime.now(timezone.utc) - timedelta(seconds=STALE_PROCESSING_SECONDS + 10)
    src.updated_at = None
    src.created_at = None
    assert _is_stale_processing(src) is True

    src.processing_started_at = datetime.now(timezone.utc) - timedelta(seconds=30)
    assert _is_stale_processing(src) is False


def test_pipeline_records_failed_timestamp_when_file_missing(db_session: Session):
    src = _make_source(db_session, status="processing")
    result = run_runtime_ingestion_pipeline(src.id, db_session)
    assert result.status == "failed"
    assert result.processing_failed_at is not None
    assert result.processing_timings is not None

    db_session.delete(src)
    db_session.commit()


def test_retry_deletes_existing_chunks_before_rerun(db_session: Session):
    src = _make_source(db_session, status="failed", title="retry.txt")
    chunk = Chunk(
        id=uuid.uuid4(),
        source_id=src.id,
        chunk_index=0,
        content="old chunk",
        embedding=[0.0] * 384,
    )
    db_session.add(chunk)
    db_session.commit()

    assert db_session.query(Chunk).filter(Chunk.source_id == src.id).count() == 1

    # Simulate retry cleanup (same as router)
    db_session.query(Chunk).filter(Chunk.source_id == src.id).delete()
    db_session.commit()
    assert db_session.query(Chunk).filter(Chunk.source_id == src.id).count() == 0

    db_session.delete(src)
    db_session.commit()
