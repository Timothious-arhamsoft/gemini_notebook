from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict
from uuid import UUID


class DocumentIngestionError(Exception):
    """Base exception for document ingestion errors."""
    pass


class UnsupportedFileTypeError(DocumentIngestionError):
    """Raised when an unsupported file type is provided."""
    pass


class DocumentParsingError(DocumentIngestionError):
    """Raised when document parsing fails."""
    pass


class EmptyDocumentError(DocumentIngestionError):
    """Raised when the document contains no extractable text or content."""
    pass


class DocumentParser(ABC):
    """Abstract base class for all document parsers."""

    @abstractmethod
    def parse(self, file_path: Path, document_id: UUID) -> Dict[str, Any]:
        """
        Parse a document and return extracted structural content and metadata.

        Args:
            file_path: Absolute or relative path to the target document.
            document_id: Unique UUID identifying the document.

        Returns:
            Dict containing document_id, source, file_type, metadata,
            structural elements/pages, and extracted full_text.
        """
        pass
