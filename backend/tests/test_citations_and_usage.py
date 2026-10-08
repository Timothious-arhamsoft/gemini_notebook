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
from app.db.models import ChatMessage


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


def test_extract_cited_indices_cjk_and_fullwidth_brackets():
    # Narrow no-break space (U+202F) between Source and digit, as models often emit
    answer = (
        "Malaria is caused by Plasmodium【Source\u202f1】. "
        "Also reported in SE Asia【Source 1】【Source 4】. "
        "Fullwidth［Source 2］."
    )
    assert extract_cited_indices(answer) == [1, 4, 2]


def test_select_answer_citations_maps_to_stable_refs():
    evidence = _sample_evidence()
    answer = "Preventer inhalers help. [Source 2] Relievers also help. [Source 2]"
    citations = select_answer_citations(answer, evidence)

    assert len(citations) == 1
    assert citations[0]["citation_index"] == 2
    assert citations[0]["source_title"] == "asthma_patient_information.pdf"
    assert citations[0]["chunk_index"] == 7
    assert citations[0]["page"] == 2


def test_select_answer_citations_from_cjk_markers():
    evidence = _sample_evidence()
    answer = "Preventer inhalers help.【Source 1】 Relievers also help.【Source 2】"
    citations = select_answer_citations(answer, evidence)

    assert [c["citation_index"] for c in citations] == [1, 2]
    assert citations[0]["source_title"] == "asthma-disease-flyer.pdf"
    assert citations[1]["source_title"] == "asthma_patient_information.pdf"


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
    from datetime import datetime, timezone

    msg = ChatMessage(
        id=uuid.uuid4(),
        notebook_id=uuid.uuid4(),
        role="assistant",
        content="Old answer [Source 1]",
        created_at=datetime.now(timezone.utc),
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
