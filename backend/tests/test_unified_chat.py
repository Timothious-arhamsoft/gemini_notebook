"""Tests for unified LLM chat path (no regex query router)."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import ChatMessage, Notebook, Source, User
from app.rag.generation import (
    build_retrieval_query,
    format_source_inventory,
    load_conversation_history,
    run_rag_pipeline,
)
from app.rag.llm import UNIFIED_SYSTEM_PROMPT, _build_system_content, _build_user_content
from app.rag.retrieval import RetrievedChunk


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _seed_notebook(session, *, with_source: bool = True):
    nb_id = uuid.uuid4()
    user = User(
        id=uuid.uuid4(),
        email=f"{uuid.uuid4().hex[:8]}@test.com",
        username=f"u{uuid.uuid4().hex[:8]}",
        hashed_password="pass",
    )
    nb = Notebook(id=nb_id, user_id=user.id, title="Test NB")
    session.add_all([user, nb])
    if with_source:
        session.add(
            Source(
                id=uuid.uuid4(),
                notebook_id=nb_id,
                source_type="pdf",
                title="who_cholera.pdf",
                status="completed",
            )
        )
    session.commit()
    return nb_id


def test_unified_prompt_covers_intent_boundaries():
    text = UNIFIED_SYSTEM_PROMPT.lower()
    assert "notegenio assistant" in text
    assert "retrieved document" in text
    assert "ignore them completely" in text or "ignore them" in text
    assert "source inventory" in text
    assert "couldn't find enough information" in text
    assert "conversation history" in text


def test_system_content_includes_inventory_and_models():
    content = _build_system_content(
        source_inventory="The notebook currently has 1 source file:\n- who_cholera.pdf",
        chat_model="openai/gpt-oss-120b",
        embedding_model="BAAI/bge-small-en-v1.5",
    )
    assert "who_cholera.pdf" in content
    assert "openai/gpt-oss-120b" in content
    assert "BAAI/bge-small-en-v1.5" in content
    assert "NoteGenio Assistant" in content


def test_user_content_marks_missing_and_present_docs():
    empty = _build_user_content("Who are you?", None)
    assert "none available" in empty.lower()
    assert "Who are you?" in empty

    with_docs = _build_user_content(
        "What causes malaria?",
        "[Source 1]\nDocument: malaria.pdf\n\nMalaria is caused by Plasmodium.",
    )
    assert "[Source 1]" in with_docs
    assert "use only when relevant" in with_docs.lower()


def test_build_retrieval_query_is_conversation_aware():
    history = [
        {"role": "user", "content": "What are the main causes of malaria?"},
        {"role": "assistant", "content": "Malaria is caused by Plasmodium..."},
    ]
    q = build_retrieval_query("What about prevention?", history)
    assert "malaria" in q.lower()
    assert "prevention" in q.lower()

    assert build_retrieval_query("hello", []) == "hello"


def test_format_source_inventory():
    assert "no source files" in format_source_inventory([]).lower()
    text = format_source_inventory(["who_cholera.pdf", "notes.txt"])
    assert "2 source files" in text
    assert "who_cholera.pdf" in text
    assert "notes.txt" in text


def test_load_conversation_history_orders_oldest_first():
    from datetime import datetime, timedelta, timezone

    session = _session()
    try:
        nb_id = _seed_notebook(session, with_source=False)
        t0 = datetime.now(timezone.utc)
        session.add_all(
            [
                ChatMessage(
                    id=uuid.uuid4(),
                    notebook_id=nb_id,
                    role="user",
                    content="What are the main causes of malaria?",
                    created_at=t0,
                ),
                ChatMessage(
                    id=uuid.uuid4(),
                    notebook_id=nb_id,
                    role="assistant",
                    content="Plasmodium parasites.",
                    created_at=t0 + timedelta(seconds=1),
                ),
            ]
        )
        session.commit()
        history = load_conversation_history(nb_id, session)
        assert [h["role"] for h in history] == ["user", "assistant"]
        assert "malaria" in history[0]["content"].lower()
    finally:
        session.close()


def _fake_chunks() -> List[RetrievedChunk]:
    return [
        RetrievedChunk(
            chunk_id=uuid.uuid4(),
            source_id=uuid.uuid4(),
            source_name="malaria.pdf",
            chunk_index=0,
            content="Malaria is caused by Plasmodium parasites transmitted by Anopheles mosquitoes.",
            similarity=0.91,
            page=1,
        )
    ]


def test_pipeline_passes_history_inventory_and_context_to_llm():
    """Semantic path: one generate_answer call carries the right information sources."""
    session = _session()
    try:
        nb_id = _seed_notebook(session)
        history = [
            {"role": "user", "content": "What are the main causes of malaria?"},
            {"role": "assistant", "content": "Caused by Plasmodium. [Source 1]"},
        ]
        captured: Dict[str, Any] = {}

        def fake_generate(
            query: str,
            *,
            document_context: Optional[str] = None,
            conversation_history=None,
            source_inventory: Optional[str] = None,
            embedding_model: str = "",
            model=None,
        ) -> Tuple[str, Optional[Dict[str, Any]]]:
            captured["query"] = query
            captured["document_context"] = document_context
            captured["conversation_history"] = list(conversation_history or [])
            captured["source_inventory"] = source_inventory
            captured["embedding_model"] = embedding_model
            if "who are you" in query.lower():
                return ("I'm the NoteGenio assistant.", {"model": "openai/gpt-oss-120b"})
            if "prevention" in query.lower():
                return (
                    "Prevention includes bed nets. [Source 1]",
                    {"model": "openai/gpt-oss-120b"},
                )
            if "files" in query.lower() or "documents" in query.lower():
                return (
                    "You currently have 1 source file:\n- who_cholera.pdf",
                    {"model": "openai/gpt-oss-120b"},
                )
            return ("Malaria is caused by Plasmodium. [Source 1]", {"model": "openai/gpt-oss-120b"})

        with patch("app.rag.generation.retrieve_chunks", return_value=_fake_chunks()), patch(
            "app.rag.generation.groq_service.generate_answer",
            side_effect=fake_generate,
        ):
            # Product / assistant question — should still call LLM; inventory present;
            # irrelevant chunks may be retrieved but answer should not require citations.
            meta = run_rag_pipeline(
                notebook_id=nb_id,
                query="Who are you?",
                db=session,
                conversation_history=[],
            )
            assert "NoteGenio" in meta["answer"]
            assert meta["citations"] == []
            assert "who_cholera.pdf" in (captured["source_inventory"] or "")

            # Document follow-up uses conversation-aware retrieval query + history in LLM.
            follow = run_rag_pipeline(
                notebook_id=nb_id,
                query="What about prevention?",
                db=session,
                conversation_history=history,
            )
            assert captured["conversation_history"] == history
            assert captured["document_context"] and "[Source 1]" in captured["document_context"]
            assert follow["citations"]
            assert follow["citations"][0]["citation_index"] == 1

            # Inventory question receives inventory text (semantic, not regex).
            inv = run_rag_pipeline(
                notebook_id=nb_id,
                query="what files have I uploaded?",
                db=session,
                conversation_history=[],
            )
            assert "who_cholera.pdf" in inv["answer"]
            assert "who_cholera.pdf" in (captured["source_inventory"] or "")
    finally:
        session.close()


def test_pipeline_queries_use_correct_information_channels():
    """Each example query reaches generate_answer with the expected context shape."""
    session = _session()
    try:
        nb_id = _seed_notebook(session)
        calls: List[Dict[str, Any]] = []

        def fake_generate(query: str, **kwargs):
            calls.append({"query": query, **kwargs})
            q = query.lower()
            if "malaria" in q and "cause" in q:
                return ("Causes include Plasmodium. [Source 1]", {"ok": True})
            if "prevention" in q:
                return ("Use insecticide-treated nets. [Source 1]", {"ok": True})
            if "did i just ask" in q or "disease was i asking" in q:
                return ("You asked about malaria.", {"ok": True})
            if "files" in q or "how many documents" in q:
                return ("1 source file: who_cholera.pdf", {"ok": True})
            if "notegenio" in q or "who are you" in q or "models" in q:
                return ("I'm NoteGenio assistant using Groq + BGE.", {"ok": True})
            return ("ok", {"ok": True})

        history_after_malaria = [
            {"role": "user", "content": "What are the main causes of malaria?"},
            {
                "role": "assistant",
                "content": "Malaria is caused by Plasmodium parasites. [Source 1]",
            },
        ]

        cases = [
            ("Who are you?", []),
            ("what is NoteGenio?", []),
            ("could you tell me more about NoteGenio", []),
            ("could you tell me more about NoteGenio assistant", []),
            ("what models are you using?", []),
            ("what are the main causes of malaria?", []),
            ("what about prevention?", history_after_malaria),
            ("what did I just ask?", history_after_malaria),
            ("what disease was I asking about?", history_after_malaria),
            ("what files have I uploaded?", []),
            ("how many documents are in this notebook?", []),
        ]

        with patch("app.rag.generation.retrieve_chunks", return_value=_fake_chunks()), patch(
            "app.rag.generation.groq_service.generate_answer",
            side_effect=fake_generate,
        ):
            for query, history in cases:
                result = run_rag_pipeline(
                    notebook_id=nb_id,
                    query=query,
                    db=session,
                    conversation_history=history,
                )
                assert result["answer"]
                assert result["usage"] is not None

        assert len(calls) == len(cases)

        # Meta / product questions always receive inventory and may receive docs,
        # but the LLM call is the same unified path (no regex branch).
        who = next(c for c in calls if c["query"] == "Who are you?")
        assert "who_cholera.pdf" in (who.get("source_inventory") or "")

        note = next(
            c for c in calls if c["query"] == "could you tell me more about NoteGenio"
        )
        assert note.get("conversation_history") == []

        prev = next(c for c in calls if c["query"] == "what about prevention?")
        assert prev.get("conversation_history") == history_after_malaria
        assert prev.get("document_context")

        asked = next(c for c in calls if c["query"] == "what did I just ask?")
        assert asked.get("conversation_history") == history_after_malaria

        files = next(c for c in calls if c["query"] == "what files have I uploaded?")
        assert "who_cholera.pdf" in (files.get("source_inventory") or "")
    finally:
        session.close()


def test_who_are_you_does_not_fail_just_because_chunks_were_retrieved():
    session = _session()
    try:
        nb_id = _seed_notebook(session)

        def fake_generate(query: str, **kwargs):
            # Simulate correct semantic behavior: ignore malaria chunks.
            assert kwargs.get("document_context")
            return ("I'm the NoteGenio assistant in your notebook.", {"model": "x"})

        with patch("app.rag.generation.retrieve_chunks", return_value=_fake_chunks()), patch(
            "app.rag.generation.groq_service.generate_answer",
            side_effect=fake_generate,
        ):
            result = run_rag_pipeline(
                notebook_id=nb_id,
                query="Who are you?",
                db=session,
                conversation_history=[],
            )

        assert "couldn't find enough information" not in result["answer"].lower()
        assert "NoteGenio" in result["answer"]
        assert result["citations"] == []
    finally:
        session.close()


def test_document_question_keeps_citations_and_grounding_path():
    session = _session()
    try:
        nb_id = _seed_notebook(session)

        def fake_generate(query: str, **kwargs):
            assert kwargs.get("document_context") and "Plasmodium" in kwargs["document_context"]
            return (
                "The main causes involve Plasmodium parasites. [Source 1]",
                {"model": "openai/gpt-oss-120b"},
            )

        with patch("app.rag.generation.retrieve_chunks", return_value=_fake_chunks()), patch(
            "app.rag.generation.groq_service.generate_answer",
            side_effect=fake_generate,
        ):
            result = run_rag_pipeline(
                notebook_id=nb_id,
                query="what are the main causes of malaria?",
                db=session,
                conversation_history=[],
            )

        assert result["citations"]
        assert result["citations"][0]["citation_index"] == 1
        assert "Plasmodium" in result["answer"]
    finally:
        session.close()
