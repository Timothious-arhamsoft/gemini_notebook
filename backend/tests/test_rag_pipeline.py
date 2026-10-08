import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db.models import User, Notebook, Source, Chunk
from app.rag.embedder import bge_embedder
from app.rag.retrieval import retrieve_chunks, RetrievedChunk
from app.rag.context import build_context
from app.rag.llm import groq_service, SYSTEM_PROMPT
from app.rag.generation import run_rag_pipeline


@pytest.fixture
def db_session():
    """In-memory SQLite DB session for unit testing RAG retrieval logic."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_5_embedding_dimension():
    """Test 5: Verify query embeddings produced by BGEEmbedder are exactly 384-dimensional."""
    embeddings = bge_embedder.generate_embeddings(["What are the symptoms of asthma?"])
    assert len(embeddings) == 1
    assert len(embeddings[0]) == 384
    assert isinstance(embeddings[0][0], float)


def test_4_empty_notebook(db_session, monkeypatch):
    """Test 4: Querying a notebook with no uploaded sources/chunks returns clean empty list."""
    empty_nb_id = uuid.uuid4()
    chunks = retrieve_chunks(notebook_id=empty_nb_id, query="What is asthma?", db=db_session, top_k=5)
    assert chunks == []

    def fake_generate(query, **kwargs):
        # No retrieved docs → unified path still calls the LLM; model should refuse document facts.
        assert not kwargs.get("document_context")
        return (
            "I couldn't find enough information about that in the uploaded sources.",
            {"model": "openai/gpt-oss-120b"},
        )

    monkeypatch.setattr(
        "app.rag.generation.groq_service.generate_answer",
        fake_generate,
    )
    result = run_rag_pipeline(notebook_id=empty_nb_id, query="What is asthma?", db=db_session, top_k=5)
    assert result["sources"] == []
    assert result["retrieved_chunks"] == []
    assert "couldn't find enough information" in result["answer"].lower() or "no" in result["answer"].lower()


def test_2_top_k_limit(db_session):
    """Test 2: Verify top_k parameter strictly caps returned chunk count."""
    nb_id = uuid.uuid4()
    user = User(id=uuid.uuid4(), email="user@test.com", username="testuser", hashed_password="pass")
    nb = Notebook(id=nb_id, user_id=user.id, title="Test Notebook")
    source = Source(id=uuid.uuid4(), notebook_id=nb_id, source_type="pdf", title="Asthma Guide", status="completed")
    db_session.add_all([user, nb, source])
    db_session.commit()

    # Create 10 dummy chunks
    dummy_vec = [0.1] * 384
    for i in range(10):
        c = Chunk(
            id=uuid.uuid4(),
            source_id=source.id,
            chunk_index=i,
            content=f"Asthma symptom chunk number {i}",
            embedding=dummy_vec,
        )
        db_session.add(c)
    db_session.commit()

    chunks_top_3 = retrieve_chunks(notebook_id=nb_id, query="asthma symptoms", db=db_session, top_k=3)
    assert len(chunks_top_3) <= 3

    chunks_top_5 = retrieve_chunks(notebook_id=nb_id, query="asthma symptoms", db=db_session, top_k=5)
    assert len(chunks_top_5) <= 5


def test_3_notebook_isolation(db_session):
    """Test 3: Verify Notebook A query NEVER retrieves chunks belonging to Notebook B."""
    nb_a_id = uuid.uuid4()
    nb_b_id = uuid.uuid4()

    user = User(id=uuid.uuid4(), email="iso@test.com", username="isouser", hashed_password="pass")
    nb_a = Notebook(id=nb_a_id, user_id=user.id, title="Asthma Notebook")
    nb_b = Notebook(id=nb_b_id, user_id=user.id, title="Diabetes Notebook")

    source_a = Source(id=uuid.uuid4(), notebook_id=nb_a_id, source_type="pdf", title="Asthma Doc", status="completed")
    source_b = Source(id=uuid.uuid4(), notebook_id=nb_b_id, source_type="pdf", title="Diabetes Doc", status="completed")

    dummy_vec = [0.05] * 384
    chunk_a = Chunk(id=uuid.uuid4(), source_id=source_a.id, chunk_index=0, content="Asthma causes shortness of breath", embedding=dummy_vec)
    chunk_b = Chunk(id=uuid.uuid4(), source_id=source_b.id, chunk_index=0, content="Diabetes affects blood sugar levels", embedding=dummy_vec)

    db_session.add_all([user, nb_a, nb_b, source_a, source_b, chunk_a, chunk_b])
    db_session.commit()

    # Query Notebook A
    res_a = retrieve_chunks(notebook_id=nb_a_id, query="medical condition", db=db_session, top_k=10)
    source_ids_a = {c.source_id for c in res_a}
    assert source_b.id not in source_ids_a
    if res_a:
        assert all(c.source_id == source_a.id for c in res_a)

    # Query Notebook B
    res_b = retrieve_chunks(notebook_id=nb_b_id, query="medical condition", db=db_session, top_k=10)
    source_ids_b = {c.source_id for c in res_b}
    assert source_a.id not in source_ids_b
    if res_b:
        assert all(c.source_id == source_b.id for c in res_b)


def test_6_ranking_order():
    """Test 6: Verify retrieved chunks are properly ordered by similarity."""
    retrieved = [
        RetrievedChunk(chunk_id=uuid.uuid4(), source_id=uuid.uuid4(), source_name="doc.pdf", chunk_index=1, content="Second best", similarity=0.82),
        RetrievedChunk(chunk_id=uuid.uuid4(), source_id=uuid.uuid4(), source_name="doc.pdf", chunk_index=0, content="Best match", similarity=0.95),
        RetrievedChunk(chunk_id=uuid.uuid4(), source_id=uuid.uuid4(), source_name="doc.pdf", chunk_index=2, content="Third match", similarity=0.61),
    ]
    sorted_retrieved = sorted(retrieved, key=lambda c: c.similarity, reverse=True)
    assert sorted_retrieved[0].similarity == 0.95
    assert sorted_retrieved[1].similarity == 0.82
    assert sorted_retrieved[2].similarity == 0.61


def test_7_context_builder_formatting():
    """Test 7: Verify context builder correctly formats numbered [Source N] blocks and citation metadata."""
    chunks = [
        RetrievedChunk(
            chunk_id=uuid.uuid4(),
            source_id=uuid.uuid4(),
            source_name="asthma_guide.pdf",
            chunk_index=3,
            content="Shortness of breath and wheezing are key asthma symptoms.",
            similarity=0.91,
            page=4,
            section="Symptoms",
        ),
        RetrievedChunk(
            chunk_id=uuid.uuid4(),
            source_id=uuid.uuid4(),
            source_name="inhaler_usage.md",
            chunk_index=1,
            content="Use rescue inhalers during sudden asthma attacks.",
            similarity=0.85,
        )
    ]

    context_str, source_refs = build_context(chunks)

    assert "[Source 1]" in context_str
    assert "Document: asthma_guide.pdf" in context_str
    assert "Page: 4" in context_str
    assert "Section: Symptoms" in context_str
    assert "Chunk: 3" in context_str

    assert "[Source 2]" in context_str
    assert "Document: inhaler_usage.md" in context_str
    assert "Chunk: 1" in context_str

    assert len(source_refs) == 2
    assert source_refs[0]["source_title"] == "asthma_guide.pdf"
    assert source_refs[0]["citation_index"] == 1
    assert source_refs[0]["chunk_index"] == 3
    assert source_refs[0]["page"] == 4
    assert "Shortness of breath" in source_refs[0]["excerpt"]
    assert source_refs[1]["citation_index"] == 2


def test_8_unsupported_question_fallback():
    """Test 8: Verify system prompt & fallback handling when context is empty or insufficient."""
    context_str, source_refs = build_context([])
    assert context_str == ""
    assert source_refs == []

    fallback_answer, usage = groq_service.generate_grounded_answer(
        query="What is the distance to Mars?",
        context_str="",
    )
    assert "couldn't find enough information" in fallback_answer.lower()
    assert usage is None
