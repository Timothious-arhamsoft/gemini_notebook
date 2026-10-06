"""Document ingestion package."""
from app.rag.ingestion.analyzer import DocumentAnalyzer, document_analyzer
from app.rag.ingestion.base import (
    DocumentParser,
    DocumentIngestionError,
    UnsupportedFileTypeError,
    DocumentParsingError,
    EmptyDocumentError,
)
from app.rag.ingestion.recommender import recommend_recursive_chunk_size
from app.rag.ingestion.service import IngestionService, ingestion_service

__all__ = [
    "DocumentParser",
    "DocumentIngestionError",
    "UnsupportedFileTypeError",
    "DocumentParsingError",
    "EmptyDocumentError",
    "IngestionService",
    "ingestion_service",
    "DocumentAnalyzer",
    "document_analyzer",
    "recommend_recursive_chunk_size",
]
