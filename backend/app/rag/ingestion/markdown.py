import logging
import re
from pathlib import Path
from typing import Any, Dict, List
from uuid import UUID

from app.rag.ingestion.base import (
    DocumentParser,
    DocumentParsingError,
    EmptyDocumentError,
)

logger = logging.getLogger(__name__)


class MarkdownParser(DocumentParser):
    """Markdown parser preserving headings, lists, code blocks, and section hierarchy."""

    def parse(self, file_path: Path, document_id: UUID) -> Dict[str, Any]:
        file_path = Path(file_path)
        if not file_path.is_file():
            raise DocumentParsingError(f"File not found: {file_path}")

        logger.info(f"Starting Markdown ingestion for document {document_id}: {file_path.name}")

        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                content = file_path.read_text(encoding="latin-1")
            except Exception as e:
                raise DocumentParsingError(f"Failed to read Markdown file '{file_path.name}': {str(e)}") from e
        except Exception as e:
            raise DocumentParsingError(f"Failed to read Markdown file '{file_path.name}': {str(e)}") from e

        if not content.strip():
            raise EmptyDocumentError(f"Markdown document '{file_path.name}' is empty.")

        sections = self._parse_markdown_structure(content)

        logger.info(
            f"Completed Markdown ingestion for document {document_id}: "
            f"parsed {len(sections)} structural sections, {len(content)} characters."
        )

        return {
            "document_id": str(document_id),
            "source": file_path.name,
            "file_type": "markdown",
            "metadata": {
                "title": file_path.stem,
                "file_size": file_path.stat().st_size,
                "section_count": len(sections),
            },
            "sections": sections,
            "full_text": content.strip(),
        }

    def _parse_markdown_structure(self, text: str) -> List[Dict[str, Any]]:
        """Parses Markdown text into structured heading sections and blocks."""
        lines = text.splitlines()
        sections: List[Dict[str, Any]] = []
        current_section = {
            "heading": "Preamble",
            "level": 0,
            "blocks": [],
            "raw_text": [],
        }

        in_code_block = False
        code_block_lang = ""
        code_block_lines: List[str] = []

        for line in lines:
            # Handle fenced code block toggles
            if line.strip().startswith("```"):
                if not in_code_block:
                    in_code_block = True
                    code_block_lang = line.strip().lstrip("`").strip()
                    code_block_lines = []
                    continue
                else:
                    in_code_block = False
                    code_content = "\n".join(code_block_lines)
                    current_section["blocks"].append({
                        "type": "code_block",
                        "language": code_block_lang,
                        "content": code_content,
                    })
                    current_section["raw_text"].append(f"```{code_block_lang}\n{code_content}\n```")
                    continue

            if in_code_block:
                code_block_lines.append(line)
                continue

            # Check heading pattern `# Heading`
            heading_match = re.match(r"^(#{1,6})\s+(.+)$", line.strip())
            if heading_match:
                # Store existing section if it has content or heading
                if current_section["raw_text"] or current_section["level"] > 0:
                    current_section["text"] = "\n".join(current_section["raw_text"]).strip()
                    sections.append(current_section)

                level = len(heading_match.group(1))
                heading_title = heading_match.group(2).strip()

                current_section = {
                    "heading": heading_title,
                    "level": level,
                    "blocks": [{"type": "heading", "level": level, "content": heading_title}],
                    "raw_text": [],
                }
                continue

            # List item
            if re.match(r"^(\*|-|\+|\d+\.)\s+", line.strip()):
                current_section["blocks"].append({
                    "type": "list_item",
                    "content": line.strip()
                })
                current_section["raw_text"].append(line)
                continue

            # Regular paragraph text line
            if line.strip():
                current_section["blocks"].append({
                    "type": "paragraph",
                    "content": line.strip()
                })
                current_section["raw_text"].append(line)

        # Flush final section
        if current_section["raw_text"] or current_section["level"] > 0:
            current_section["text"] = "\n".join(current_section["raw_text"]).strip()
            sections.append(current_section)

        return sections
