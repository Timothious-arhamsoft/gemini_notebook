"""RAG package for Gemini Notebook."""
from app.rag.embedder import bge_embedder
from app.rag.retrieval import retrieve_chunks, RetrievedChunk
from app.rag.context import build_context
from app.rag.llm import groq_service
from app.rag.generation import run_rag_pipeline

__all__ = [
    "bge_embedder",
    "retrieve_chunks",
    "RetrievedChunk",
    "build_context",
    "groq_service",
    "run_rag_pipeline",
]
