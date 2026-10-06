import logging
from pathlib import Path
from typing import Any, Dict, Optional, Type
from uuid import UUID

from app.rag.ingestion.analyzer import document_analyzer
from app.rag.ingestion.base import (
    DocumentParser,
    DocumentParsingError,
    UnsupportedFileTypeError,
)
from app.rag.ingestion.docx import DocxParser
from app.rag.ingestion.markdown import MarkdownParser
from app.rag.ingestion.pdf import PDFParser
from app.rag.ingestion.txt import TextParser

logger = logging.getLogger(__name__)


class IngestionService:
    """Document Ingestion Service with a clean parser registry."""

    def __init__(self) -> None:
        self._registry: Dict[str, DocumentParser] = {}
        self._register_default_parsers()

    def _register_default_parsers(self) -> None:
        pdf_parser = PDFParser()
        md_parser = MarkdownParser()
        docx_parser = DocxParser()
        txt_parser = TextParser()

        self.register_parser(".pdf", pdf_parser)
        self.register_parser(".md", md_parser)
        self.register_parser(".markdown", md_parser)
        self.register_parser(".docx", docx_parser)
        self.register_parser(".txt", txt_parser)

    def register_parser(self, extension: str, parser: DocumentParser) -> None:
        """Register a parser instance for a given file extension."""
        ext = extension.lower()
        if not ext.startswith("."):
            ext = f".{ext}"
        self._registry[ext] = parser
        logger.debug(f"Registered parser {parser.__class__.__name__} for extension {ext}")

    def get_parser(self, extension: str) -> DocumentParser:
        """Retrieve the parser for a given file extension."""
        ext = extension.lower()
        if not ext.startswith("."):
            ext = f".{ext}"
        
        parser = self._registry.get(ext)
        if not parser:
            supported = ", ".join(sorted(self._registry.keys()))
            raise UnsupportedFileTypeError(
                f"Unsupported file extension '{ext}'. Supported extensions: {supported}"
            )
        return parser

    def parse(self, file_path: Path, document_id: UUID) -> Dict[str, Any]:
        """
        Main entry point to parse a document using the appropriate registered parser
        and calculate document analysis / chunk size recommendations.

        Args:
            file_path: Path to the uploaded document file.
            document_id: UUID identifier of the document.

        Returns:
            Dict containing parsed structure, metadata, pages/sections, extracted content, and analysis.
        """
        file_path = Path(file_path)
        if not file_path.is_file():
            raise DocumentParsingError(f"File path does not exist or is not a file: {file_path}")

        ext = file_path.suffix.lower()
        logger.info(f"Starting document ingestion for {file_path.name} (ID: {document_id})")
        logger.info(f"Detected file type: '{ext}'")

        parser = self.get_parser(ext)
        logger.info(f"Selected parser: {parser.__class__.__name__}")

        result = parser.parse(file_path=file_path, document_id=document_id)
        logger.info(f"Ingestion completed successfully for document {document_id}")

        # Document Analysis & Chunk Size Recommendation step
        try:
            analysis = document_analyzer.analyze(result)
            result["analysis"] = analysis
            logger.info(
                f"Document analysis completed for document {document_id}: "
                f"Recommended chunk size {analysis.get('recommended_chunk_size')} ({analysis.get('recommended_strategy')})"
            )
        except Exception as analysis_err:
            logger.error(f"Document analysis failed for {file_path.name}: {analysis_err}", exc_info=True)
            result["analysis"] = {
                "filename": file_path.name,
                "file_type": ext.lstrip("."),
                "error": f"Document analysis failed: {str(analysis_err)}",
                "recommended_strategy": "recursive",
                "recommended_chunk_size": 800,
            }

        return result


# Singleton instance
ingestion_service = IngestionService()
