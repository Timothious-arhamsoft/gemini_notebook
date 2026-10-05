import logging
from pathlib import Path
from typing import Any, Dict
from uuid import UUID

import pymupdf

from app.rag.ingestion.base import (
    DocumentParser,
    DocumentParsingError,
    EmptyDocumentError,
)

logger = logging.getLogger(__name__)


class PDFParser(DocumentParser):
    """PDF document parser using PyMuPDF."""

    def parse(self, file_path: Path, document_id: UUID) -> Dict[str, Any]:
        file_path = Path(file_path)
        if not file_path.is_file():
            raise DocumentParsingError(f"File not found: {file_path}")

        logger.info(f"Starting PDF ingestion for document {document_id}: {file_path.name}")

        doc = None
        try:
            doc = pymupdf.open(file_path)
        except Exception as e:
            raise DocumentParsingError(f"Failed to open PDF '{file_path.name}': {str(e)}") from e

        try:
            doc_metadata = doc.metadata or {}
            total_pages = len(doc)
            pages = []
            extracted_text_pieces = []

            for page_idx in range(total_pages):
                try:
                    page = doc[page_idx]
                    page_number = page_idx + 1

                    # Extract page text
                    text = page.get_text("text") or ""
                    
                    # Extract structured text blocks with bounding boxes
                    text_blocks = []
                    raw_blocks = page.get_text("blocks") or []
                    for b_idx, block in enumerate(raw_blocks):
                        # block format: (x0, y0, x1, y1, text, block_no, block_type)
                        if len(block) >= 5 and block[4].strip():
                            text_blocks.append({
                                "block_id": b_idx,
                                "bbox": [round(coord, 2) for coord in block[:4]],
                                "text": block[4].strip(),
                                "block_type": block[6] if len(block) > 6 else 0
                            })

                    page_info = {
                        "page_number": page_number,
                        "text": text,
                        "blocks": text_blocks,
                        "metadata": {
                            "width": page.rect.width,
                            "height": page.rect.height,
                            "rotation": page.rotation,
                        }
                    }
                    pages.append(page_info)
                    if text.strip():
                        extracted_text_pieces.append(f"--- Page {page_number} ---\n{text.strip()}")

                except Exception as page_err:
                    logger.warning(
                        f"Error parsing page {page_idx + 1} of document {document_id}: {page_err}"
                    )
                    pages.append({
                        "page_number": page_idx + 1,
                        "text": "",
                        "blocks": [],
                        "error": str(page_err)
                    })

            full_text = "\n\n".join(extracted_text_pieces).strip()
            if not full_text:
                raise EmptyDocumentError(f"PDF document '{file_path.name}' contains no extractable text.")

            logger.info(
                f"Completed PDF ingestion for document {document_id}: "
                f"extracted {len(pages)} pages, {len(full_text)} characters."
            )

            return {
                "document_id": str(document_id),
                "source": file_path.name,
                "file_type": "pdf",
                "metadata": {
                    "title": doc_metadata.get("title") or file_path.stem,
                    "author": doc_metadata.get("author") or "",
                    "subject": doc_metadata.get("subject") or "",
                    "creator": doc_metadata.get("creator") or "",
                    "total_pages": total_pages,
                    "file_size": file_path.stat().st_size,
                },
                "pages": pages,
                "full_text": full_text,
            }

        finally:
            if doc:
                try:
                    doc.close()
                except Exception:
                    pass
