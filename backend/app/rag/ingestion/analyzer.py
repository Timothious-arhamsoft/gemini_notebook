import math
import statistics
from typing import Any, Dict, List, Optional

from app.rag.ingestion.recommender import recommend_recursive_chunk_size


def _percentile(sorted_data: List[int], p: float) -> int:
    """Calculate percentile from a sorted list of non-negative integers."""
    if not sorted_data:
        return 0
    idx = min(int(math.ceil(p * len(sorted_data))) - 1, len(sorted_data) - 1)
    return sorted_data[max(0, idx)]


class DocumentAnalyzer:
    """
    Deterministic runtime analyzer for extracted document structure and statistics.
    Computes character, word, paragraph, page, and structural metrics, and
    calculates a recommended chunk size for future recursive chunking.
    """

    def analyze(self, parsed_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a parsed document dict produced by a DocumentParser.

        Args:
            parsed_result: Result dictionary from DocumentParser containing:
                - source: filename
                - file_type: extension/type
                - full_text: string
                - pages / elements / sections / metadata (optional)

        Returns:
            Dict containing document statistics and recommended_chunk_size.
        """
        full_text = parsed_result.get("full_text") or ""
        file_name = parsed_result.get("source") or "document"
        file_type = parsed_result.get("file_type") or "txt"
        metadata = parsed_result.get("metadata") or {}

        total_characters = len(full_text)
        total_words = len(full_text.split()) if full_text else 0

        # Split text into paragraph / block structures
        raw_paragraphs = [p.strip() for p in full_text.split("\n\n") if p.strip()]
        if not raw_paragraphs and full_text.strip():
            raw_paragraphs = [full_text.strip()]

        paragraph_count = len(raw_paragraphs)
        para_lengths = [len(p) for p in raw_paragraphs] if raw_paragraphs else [0]
        para_lengths_sorted = sorted(para_lengths)

        min_paragraph_chars = para_lengths_sorted[0]
        max_paragraph_chars = para_lengths_sorted[-1]
        avg_paragraph_chars = round(sum(para_lengths) / max(1, paragraph_count), 2)
        median_paragraph_chars = int(statistics.median(para_lengths_sorted))
        p75_paragraph_chars = _percentile(para_lengths_sorted, 0.75)
        p90_paragraph_chars = _percentile(para_lengths_sorted, 0.90)
        p95_paragraph_chars = _percentile(para_lengths_sorted, 0.95)

        # PDF page metrics
        page_count: Optional[int] = None
        avg_page_chars: Optional[float] = None
        median_page_chars: Optional[int] = None
        min_page_chars: Optional[int] = None
        max_page_chars: Optional[int] = None

        pages = parsed_result.get("pages")
        if isinstance(pages, list) and len(pages) > 0:
            page_count = len(pages)
            page_lengths = [len(p.get("text", "") or "") for p in pages if isinstance(p, dict)]
            if page_lengths:
                page_lengths_sorted = sorted(page_lengths)
                min_page_chars = page_lengths_sorted[0]
                max_page_chars = page_lengths_sorted[-1]
                avg_page_chars = round(sum(page_lengths) / len(page_lengths), 2)
                median_page_chars = int(statistics.median(page_lengths_sorted))
        elif "total_pages" in metadata:
            page_count = metadata["total_pages"]

        # DOCX / Markdown structural metrics
        heading_count: Optional[int] = None
        section_count: Optional[int] = None
        table_count: Optional[int] = metadata.get("table_count")

        elements = parsed_result.get("elements")
        if isinstance(elements, list):
            headings = [e for e in elements if isinstance(e, dict) and e.get("type") == "heading"]
            heading_count = len(headings)

        sections = parsed_result.get("sections")
        if isinstance(sections, list):
            section_count = len(sections)

        # Assemble analysis dictionary
        stats: Dict[str, Any] = {
            "filename": file_name,
            "file_type": file_type,
            "total_characters": total_characters,
            "total_words": total_words,
            "paragraph_count": paragraph_count,
            "avg_paragraph_chars": avg_paragraph_chars,
            "median_paragraph_chars": median_paragraph_chars,
            "min_paragraph_chars": min_paragraph_chars,
            "max_paragraph_chars": max_paragraph_chars,
            "p75_paragraph_chars": p75_paragraph_chars,
            "p90_paragraph_chars": p90_paragraph_chars,
            "p95_paragraph_chars": p95_paragraph_chars,
            "page_count": page_count,
            "avg_page_chars": avg_page_chars,
            "median_page_chars": median_page_chars,
            "min_page_chars": min_page_chars,
            "max_page_chars": max_page_chars,
            "heading_count": heading_count,
            "section_count": section_count,
            "table_count": table_count,
        }

        # Calculate recommendation
        recommended_chunk_size = recommend_recursive_chunk_size(stats)
        stats["recommended_strategy"] = "recursive"
        stats["recommended_chunk_size"] = recommended_chunk_size

        return stats


# Singleton instance
document_analyzer = DocumentAnalyzer()
