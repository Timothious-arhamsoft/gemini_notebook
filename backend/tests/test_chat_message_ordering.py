"""Chat history must reload in authoritative chronological order."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db.models import ChatMessage, Notebook, User
from app.routers.chat import (
    ChatMessageCreate,
    _assistant_created_at,
    _to_chat_response,
    create_chat_message,
    list_chat_messages,
)


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _seed_notebook(session):
    user = User(
        id=uuid.uuid4(),
        email=f"{uuid.uuid4().hex[:8]}@test.com",
        username=f"u{uuid.uuid4().hex[:8]}",
        hashed_password="pass",
    )
    nb = Notebook(id=uuid.uuid4(), user_id=user.id, title="Ordering NB")
    session.add_all([user, nb])
    session.commit()
    return user, nb.id


def test_assistant_created_at_is_strictly_after_user():
    t0 = datetime(2026, 10, 7, 12, 0, 0, tzinfo=timezone.utc)
    later = _assistant_created_at(t0)
    assert later > t0


def test_list_chat_messages_orders_by_created_at_then_id():
    session = _session()
    try:
        user, nb_id = _seed_notebook(session)
        t0 = datetime(2026, 10, 7, 12, 0, 0, tzinfo=timezone.utc)

        # Insert deliberately out of chronological order; listing must still
        # return user → assistant pairs by created_at.
        rows = [
            ChatMessage(
                id=uuid.uuid4(),
                notebook_id=nb_id,
                role="assistant",
                content="I'm NoteGenio",
                created_at=t0 + timedelta(seconds=2, microseconds=1),
            ),
            ChatMessage(
                id=uuid.uuid4(),
                notebook_id=nb_id,
                role="user",
                content="who are you",
                created_at=t0 + timedelta(seconds=2),
            ),
            ChatMessage(
                id=uuid.uuid4(),
                notebook_id=nb_id,
                role="assistant",
                content="Hello reply",
                created_at=t0 + timedelta(microseconds=1),
            ),
            ChatMessage(
                id=uuid.uuid4(),
                notebook_id=nb_id,
                role="user",
                content="hello",
                created_at=t0,
            ),
        ]
        session.add_all(rows)
        session.commit()

        with patch("app.routers.chat._verify_notebook_access", return_value=None):
            listed = list_chat_messages(notebook_id=nb_id, db=session, current_user=user)

        assert [r.role for r in listed] == ["user", "assistant", "user", "assistant"]
        assert [r.content for r in listed] == [
            "hello",
            "Hello reply",
            "who are you",
            "I'm NoteGenio",
        ]
    finally:
        session.close()


def test_create_chat_message_persists_strict_chronological_timestamps():
    session = _session()
    try:
        user, nb_id = _seed_notebook(session)

        def fake_pipeline(**kwargs):
            return {
                "answer": "I'm the NoteGenio assistant.",
                "citations": [],
                "retrieved_evidence": [],
                "usage": {"model": "openai/gpt-oss-120b"},
            }

        with patch("app.routers.chat._verify_notebook_access", return_value=None), patch(
            "app.routers.chat.load_conversation_history", return_value=[]
        ), patch("app.routers.chat.run_rag_pipeline", side_effect=fake_pipeline):
            returned = create_chat_message(
                notebook_id=nb_id,
                payload=ChatMessageCreate(content="who are you"),
                db=session,
                current_user=user,
            )

        assert len(returned) == 2
        assert returned[0].role == "user"
        assert returned[1].role == "assistant"
        assert returned[1].created_at > returned[0].created_at

        with patch("app.routers.chat._verify_notebook_access", return_value=None):
            listed = list_chat_messages(notebook_id=nb_id, db=session, current_user=user)

        assert [m.role for m in listed] == ["user", "assistant"]
        assert listed[0].content == "who are you"
        assert "NoteGenio" in listed[1].content
    finally:
        session.close()


def test_multi_turn_reload_preserves_user_assistant_pairs():
    session = _session()
    try:
        user, nb_id = _seed_notebook(session)
        answers = [
            "Hello!",
            "I'm NoteGenio.",
            "Malaria is caused by Plasmodium. [Source 1]",
            "Prevention includes bed nets. [Source 1]",
            "I'm NoteGenio.",
            "You were asking about malaria.",
        ]
        queries = [
            "hello",
            "who are you",
            "what are the main causes of malaria?",
            "what about prevention?",
            "who are you?",
            "what disease was I asking about?",
        ]

        def fake_pipeline(**kwargs):
            return {
                "answer": answers.pop(0),
                "citations": [],
                "retrieved_evidence": [],
                "usage": None,
            }

        with patch("app.routers.chat._verify_notebook_access", return_value=None), patch(
            "app.routers.chat.run_rag_pipeline", side_effect=fake_pipeline
        ):
            for q in queries:
                create_chat_message(
                    notebook_id=nb_id,
                    payload=ChatMessageCreate(content=q),
                    db=session,
                    current_user=user,
                )

        with patch("app.routers.chat._verify_notebook_access", return_value=None):
            listed = list_chat_messages(notebook_id=nb_id, db=session, current_user=user)

        assert [m.role for m in listed] == ["user", "assistant"] * 6
        assert [m.content for m in listed][0::2] == queries
        for i in range(0, len(listed), 2):
            assert listed[i].created_at < listed[i + 1].created_at
        for i in range(len(listed) - 1):
            assert listed[i].created_at <= listed[i + 1].created_at
    finally:
        session.close()


def test_to_chat_response_preserves_created_at():
    msg = ChatMessage(
        id=uuid.uuid4(),
        notebook_id=uuid.uuid4(),
        role="user",
        content="hi",
        created_at=datetime(2026, 10, 7, 15, 30, tzinfo=timezone.utc),
    )
    resp = _to_chat_response(msg)
    assert resp.created_at == msg.created_at
