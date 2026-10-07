"""Tests for answer citations vs retrieved evidence and Groq usage/cost."""

import uuid

from app.rag.citations import (
    extract_cited_indices,
    is_insufficient_answer,
    select_answer_citations,
)
from app.rag.context import build_context
from app.rag.pricing import MODEL_PRICING, build_usage_metadata, estimate_cost_usd
from app.rag.retrieval import RetrievedChunk
from app.routers.chat import _parse_source_refs, _to_chat_response
from app.models import ChatMessage


def _sample_evidence():
    chunks = [
        RetrievedChunk(
            chunk_id=uuid.uuid4(),
            source_id=uuid.uuid4(),
            source_name="asthma-disease-flyer.pdf",
            chunk_index=4,
            content="Preventer inhalers reduce airway inflammation.",
            similarity=0.9,
            page=2,
        ),
        RetrievedChunk(
            chunk_id=uuid.uuid4(),
            source_id=uuid.uuid4(),
            source_name="asthma_patient_information.pdf",
            chunk_index=7,
            content="Reliever inhalers quickly relax airway muscles.",
            similarity=0.85,
            page=2,
        ),
        RetrievedChunk(
            chunk_id=uuid.uuid4(),
            source_id=uuid.uuid4(),
            source_name="README.md",
            chunk_index=0,
            content="Project setup instructions.",
            similarity=0.4,
        ),
    ]
    _, evidence = build_context(chunks)
    return evidence


def test_extract_cited_indices_order_and_repeats():
    answer = (
        "Sentence A [Source 2]. Sentence B [Source 2]. Sentence C [Source 1]."
    )
    assert extract_cited_indices(answer) == [2, 1]


def test_select_answer_citations_maps_to_stable_refs():
    evidence = _sample_evidence()
    answer = "Preventer inhalers help. [Source 2] Relievers also help. [Source 2]"
    citations = select_answer_citations(answer, evidence)

    assert len(citations) == 1
    assert citations[0]["citation_index"] == 2
    assert citations[0]["source_title"] == "asthma_patient_information.pdf"
    assert citations[0]["chunk_index"] == 7
    assert citations[0]["page"] == 2


def test_invalid_citation_index_is_ignored():
    evidence = _sample_evidence()
    answer = "Something unsupported. [Source 99]"
    citations = select_answer_citations(answer, evidence)
    assert citations == []


def test_insufficient_answer_has_no_citations_despite_retrieval():
    evidence = _sample_evidence()
    answer = "I couldn't find enough information about that in the uploaded sources."
    assert is_insufficient_answer(answer)
    citations = select_answer_citations(answer, evidence)
    assert citations == []
    assert len(evidence) == 3


def test_estimate_cost_gpt_oss_120b():
    rates = MODEL_PRICING["openai/gpt-oss-120b"]
    cost = estimate_cost_usd("openai/gpt-oss-120b", 1842, 312)
    expected = (1842 / 1_000_000) * rates["input_per_million"] + (
        312 / 1_000_000
    ) * rates["output_per_million"]
    assert cost == round(expected, 10)


def test_estimate_cost_unknown_model_is_none():
    assert estimate_cost_usd("unknown/model", 100, 50) is None


def test_build_usage_metadata_includes_cached_tokens():
    usage = build_usage_metadata(
        model="openai/gpt-oss-120b",
        prompt_tokens=1842,
        completion_tokens=312,
        total_tokens=2154,
        cached_tokens=1024,
        latency_ms=2800,
        request_id="req_123",
    )
    assert usage["prompt_tokens"] == 1842
    assert usage["completion_tokens"] == 312
    assert usage["total_tokens"] == 2154
    assert usage["cached_tokens"] == 1024
    assert usage["model"] == "openai/gpt-oss-120b"
    assert usage["estimated_cost_usd"] is not None
    assert usage["request_id"] == "req_123"
    assert usage["latency_ms"] == 2800.0


def test_parse_legacy_source_refs_list():
    legacy = [
        {
            "source_id": str(uuid.uuid4()),
            "source_title": "old.pdf",
            "excerpt": "legacy excerpt",
        }
    ]
    citations, evidence, usage = _parse_source_refs(legacy)
    assert citations is not None and len(citations) == 1
    assert citations[0].source_title == "old.pdf"
    assert evidence is None
    assert usage is None


def test_parse_v2_source_refs_dict():
    source_id = uuid.uuid4()
    chunk_id = uuid.uuid4()
    refs = {
        "version": 2,
        "citations": [
            {
                "id": "citation-2",
                "citation_index": 2,
                "source_id": str(source_id),
                "source_title": "doc.pdf",
                "chunk_id": str(chunk_id),
                "chunk_index": 7,
                "page": 2,
                "excerpt": "hello",
                "content": "hello world",
            }
        ],
        "retrieved_evidence": [
            {
                "id": "citation-1",
                "citation_index": 1,
                "source_id": str(uuid.uuid4()),
                "source_title": "other.pdf",
                "excerpt": "other",
            },
            {
                "id": "citation-2",
                "citation_index": 2,
                "source_id": str(source_id),
                "source_title": "doc.pdf",
                "excerpt": "hello",
            },
        ],
        "usage": {
            "model": "openai/gpt-oss-120b",
            "prompt_tokens": 100,
            "completion_tokens": 20,
            "total_tokens": 120,
            "estimated_cost_usd": 0.000027,
        },
    }
    citations, evidence, usage = _parse_source_refs(refs)
    assert citations is not None and len(citations) == 1
    assert citations[0].citation_index == 2
    assert evidence is not None and len(evidence) == 2
    assert usage is not None
    assert usage.prompt_tokens == 100
    assert usage.model == "openai/gpt-oss-120b"


def test_historical_message_without_usage_does_not_crash():
    msg = ChatMessage(
        id=uuid.uuid4(),
        notebook_id=uuid.uuid4(),
        role="assistant",
        content="Old answer [Source 1]",
        source_refs=[
            {
                "source_id": str(uuid.uuid4()),
                "source_title": "legacy.pdf",
                "excerpt": "text",
            }
        ],
    )
    response = _to_chat_response(msg)
    assert response.citations is not None
    assert response.usage is None
    assert response.retrieved_evidence is None


def test_source_inventory_query_detection():
    from app.rag.query_router import classify_user_message, is_source_inventory_query

    assert is_source_inventory_query("what source file or files you have")
    assert is_source_inventory_query("What documents have I uploaded?")
    assert is_source_inventory_query("How many documents are in this notebook?")
    assert is_source_inventory_query("Which files are available?")
    assert not is_source_inventory_query("  ")

    # Normal RAG / content questions must NOT short-circuit
    assert not is_source_inventory_query("What does the document say about cholera transmission?")
    assert not is_source_inventory_query("What is cancer?")
    assert classify_user_message("What is cancer?") == "rag"


def test_conversational_query_detection():
    from app.rag.query_router import classify_user_message, is_conversational_query

    assert is_conversational_query("hello")
    assert is_conversational_query("how are you?")
    assert is_conversational_query("tell me about yourself")
    assert is_conversational_query("tell me about you")
    assert classify_user_message("hello") == "conversational"
    assert classify_user_message("how are you?") == "conversational"
    assert classify_user_message("tell me about you") == "conversational"

    assert classify_user_message("what is cholera?") == "rag"
    assert classify_user_message("summarize this document") == "rag"
    assert not is_conversational_query("tell me about cholera")


def test_source_inventory_pipeline_skips_retrieval():
    """Source-list questions answer from Source metadata with no chunk citations."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.database import Base
    from app.models import Notebook, Source, User
    from app.rag.generation import run_rag_pipeline

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        nb_id = uuid.uuid4()
        user = User(
            id=uuid.uuid4(),
            email="inv@test.com",
            username="invuser",
            hashed_password="pass",
        )
        nb = Notebook(id=nb_id, user_id=user.id, title="Cholera NB")
        source = Source(
            id=uuid.uuid4(),
            notebook_id=nb_id,
            source_type="pdf",
            title="who_cholera.pdf",
            status="completed",
        )
        session.add_all([user, nb, source])
        session.commit()

        result = run_rag_pipeline(
            notebook_id=nb_id,
            query="what source file or files you have",
            db=session,
            top_k=5,
        )

        assert "who_cholera.pdf" in result["answer"]
        assert "1 source file" in result["answer"]
        assert result["citations"] == []
        assert result["retrieved_evidence"] == []
        assert result["retrieved_chunks"] == []
        assert result["usage"] is None
    finally:
        session.close()
