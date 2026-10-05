import logging
from pathlib import Path
from typing import Any, Dict, List
from uuid import UUID

import docx  # python-docx

from app.rag.ingestion.base import (
    DocumentParser,
    DocumentParsingError,
    EmptyDocumentError,
)

logger = logging.getLogger(__name__)


class DocxParser(DocumentParser):
    """DOCX parser using python-docx preserving headings, paragraphs, lists, and tables."""

    def parse(self, file_path: Path, document_id: UUID) -> Dict[str, Any]:
        file_path = Path(file_path)
        if not file_path.is_file():
            raise DocumentParsingError(f"File not found: {file_path}")

        logger.info(f"Starting DOCX ingestion for document {document_id}: {file_path.name}")

        try:
            doc = docx.Document(file_path)
        except Exception as e:
            raise DocumentParsingError(f"Failed to open DOCX file '{file_path.name}': {str(e)}") from e

        # Extract core properties metadata
        props = doc.core_properties
        metadata = {
            "title": props.title or file_path.stem,
            "author": props.author or "",
            "category": props.category or "",
            "file_size": file_path.stat().st_size,
        }

        elements: List[Dict[str, Any]] = []
        extracted_text_pieces: List[str] = []
        table_count = 0

        # Process document elements in flow order
        # doc.element.body contains block elements (<w:p> paragraphs and <w:tbl> tables)
        for child in doc.element.body:
            tag_name = child.tag.split("}")[-1] if "}" in child.tag else child.tag

            if tag_name == "p":
                para = docx.text.paragraph.Paragraph(child, doc)
                text = para.text.strip()
                if not text:
                    continue

                style_name = para.style.name if para.style else ""
                
                # Heading detection
                if style_name.startswith("Heading"):
                    try:
                        level = int(style_name.replace("Heading", "").strip())
                    except ValueError:
                        level = 1
                    elements.append({
                        "type": "heading",
                        "level": level,
                        "style": style_name,
                        "text": text,
                    })
                    extracted_text_pieces.append(f"\n# {text}\n")
                # List item detection
                elif "List" in style_name or para._element.xpath(".//w:numPr"):
                    elements.append({
                        "type": "list_item",
                        "style": style_name,
                        "text": text,
                    })
                    extracted_text_pieces.append(f"* {text}")
                else:
                    elements.append({
                        "type": "paragraph",
                        "style": style_name,
                        "text": text,
                    })
                    extracted_text_pieces.append(text)

            elif tag_name == "tbl":
                table_count += 1
                tbl = docx.table.Table(child, doc)
                table_data: List[List[str]] = []
                for row in tbl.rows:
                    row_data = [cell.text.strip() for cell in row.cells]
                    table_data.append(row_data)

                elements.append({
                    "type": "table",
                    "table_id": table_count,
                    "rows": len(table_data),
                    "cols": len(table_data[0]) if table_data else 0,
                    "data": table_data,
                })
                # Structured string representation for table text
                table_str_rows = [" | ".join(r) for r in table_data]
                extracted_text_pieces.append("\n" + "\n".join(table_str_rows) + "\n")

        full_text = "\n\n".join(extracted_text_pieces).strip()
        if not full_text:
            raise EmptyDocumentError(f"DOCX document '{file_path.name}' contains no extractable text.")

        metadata["table_count"] = table_count
        metadata["element_count"] = len(elements)

        logger.info(
            f"Completed DOCX ingestion for document {document_id}: "
            f"extracted {len(elements)} structural elements, {table_count} tables, {len(full_text)} characters."
        )

        return {
            "document_id": str(document_id),
            "source": file_path.name,
            "file_type": "docx",
            "metadata": metadata,
            "elements": elements,
            "full_text": full_text,
        }
