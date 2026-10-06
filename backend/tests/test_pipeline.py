import pytest
from app.rag.splitter import split_text
from app.rag.embedder import bge_embedder


def test_recursive_splitter_with_custom_chunk_size():
    sample_text = ("This is a test paragraph for chunking. " * 30)
    chunks = split_text(sample_text, chunk_size=300)
    
    assert len(chunks) > 1
    for chunk in chunks:
        # allow small overflow margin due to sentence boundaries
        assert len(chunk) <= 350


def test_bge_embedder_dimensions():
    sample_chunks = ["First text chunk", "Second text chunk for embedding"]
    embeddings = bge_embedder.generate_embeddings(sample_chunks)
    
    assert len(embeddings) == 2
    assert len(embeddings[0]) == 384
    assert len(embeddings[1]) == 384
    assert isinstance(embeddings[0][0], float)
