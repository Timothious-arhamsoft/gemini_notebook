import logging
from pathlib import Path
from typing import Any, Dict
from uuid import UUID

from app.rag.ingestion.base import (
    DocumentParser,
    DocumentParsingError,
    EmptyDocumentError,
)

logger = logging.getLogger(__name__)


class TextParser(DocumentParser):
    """Plain text parser for .txt files."""

    def parse(self, file_path: Path, document_id: UUID) -> Dict[str, Any]:
        file_path = Path(file_path)
        if not file_path.is_file():
            raise DocumentParsingError(f"File not found: {file_path}")

        logger.info(f"Starting Text ingestion for document {document_id}: {file_path.name}")

        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                content = file_path.read_text(encoding="latin-1")
            except Exception as e:
                raise DocumentParsingError(f"Failed to read text file '{file_path.name}': {str(e)}") from e
        except Exception as e:
            raise DocumentParsingError(f"Failed to read text file '{file_path.name}': {str(e)}") from e

        if not content.strip():
            raise EmptyDocumentError(f"Text document '{file_path.name}' is empty.")

        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

        logger.info(
            f"Completed Text ingestion for document {document_id}: "
            f"extracted {len(paragraphs)} paragraphs, {len(content)} characters."
        )

        return {
            "document_id": str(document_id),
            "source": file_path.name,
            "file_type": "txt",
            "metadata": {
                "title": file_path.stem,
                "file_size": file_path.stat().st_size,
                "paragraph_count": len(paragraphs),
            },
            "paragraphs": paragraphs,
            "full_text": content.strip(),
        }
