import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db.models import ChatMessage, Notebook, User
from app.routers.chat import get_notebook_token_usage


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _seed_notebook(session, email: str) -> tuple[User, Notebook]:
    user = User(
        id=uuid.uuid4(),
        email=email,
        username=f"user-{uuid.uuid4().hex[:8]}",
        hashed_password="not-a-real-password",
    )
    notebook = Notebook(id=uuid.uuid4(), user_id=user.id, title=email)
    session.add_all([user, notebook])
    session.commit()
    return user, notebook


def _assistant_message(notebook_id: uuid.UUID, usage: dict) -> ChatMessage:
    return ChatMessage(
        id=uuid.uuid4(),
        notebook_id=notebook_id,
        role="assistant",
        content="answer",
        source_refs={"usage": usage},
    )


def test_notebook_usage_aggregates_only_its_assistant_responses():
    session = _session()
    try:
        user_a, notebook_a = _seed_notebook(session, "a@example.test")
        _, notebook_b = _seed_notebook(session, "b@example.test")
        session.add_all([
            _assistant_message(
                notebook_a.id,
                {
                    "model": "openai/gpt-oss-120b",
                    "input_tokens": 100,
                    "output_tokens": 20,
                    "total_tokens": 120,
                    "input_cost": 0.000015,
                    "output_cost": 0.000012,
                    "total_cost": 0.000027,
                },
            ),
            _assistant_message(
                notebook_a.id,
                {
                    "model": "openai/gpt-oss-20b",
                    "prompt_tokens": 50,
                    "completion_tokens": 10,
                    "total_tokens": 60,
                    "estimated_cost_usd": 0.00000675,
                },
            ),
            _assistant_message(
                notebook_b.id,
                {
                    "model": "openai/gpt-oss-120b",
                    "input_tokens": 900,
                    "output_tokens": 100,
                    "input_cost": 0.000135,
                    "output_cost": 0.00006,
                    "total_cost": 0.000195,
                },
            ),
        ])
        session.commit()

        usage = get_notebook_token_usage(
            notebook_id=notebook_a.id,
            db=session,
            current_user=user_a,
        )

        assert usage.input_tokens == 150
        assert usage.output_tokens == 30
        assert usage.total_tokens == usage.input_tokens + usage.output_tokens == 180
        assert usage.input_cost == round(0.000015 + 50 / 1_000_000 * 0.075, 10)
        assert usage.output_cost == round(0.000012 + 10 / 1_000_000 * 0.30, 10)
        assert usage.total_cost == round(0.000027 + 0.00000675, 10)
        assert usage.estimated_cost_usd == usage.total_cost
        assert usage.request_count == 2
        assert usage.unpriced_request_count == 0
    finally:
        session.close()


def test_notebook_usage_ignores_messages_without_usage():
    session = _session()
    try:
        user, notebook = _seed_notebook(session, "empty@example.test")
        session.add(
            ChatMessage(
                id=uuid.uuid4(),
                notebook_id=notebook.id,
                role="assistant",
                content="old response without usage",
            )
        )
        session.commit()

        usage = get_notebook_token_usage(
            notebook_id=notebook.id,
            db=session,
            current_user=user,
        )
        assert usage.input_tokens == 0
        assert usage.output_tokens == 0
        assert usage.total_tokens == 0
        assert usage.total_cost == 0
        assert usage.request_count == 0
    finally:
        session.close()
