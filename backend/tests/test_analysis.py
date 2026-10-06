"""
Tests for the document analyzer and chunk size recommender.
"""
import uuid
from pathlib import Path

import docx
import pymupdf
import pytest

from app.rag.ingestion.analyzer import DocumentAnalyzer, document_analyzer
from app.rag.ingestion.recommender import (
    MIN_RECOMMENDED_CHUNK_SIZE,
    MAX_RECOMMENDED_CHUNK_SIZE,
    DEFAULT_CHUNK_SIZE,
    recommend_recursive_chunk_size,
)
from app.rag.ingestion.service import ingestion_service


# ─── Helper: Build minimal parsed_result ─────────────────────────────────────

def _make_parsed(full_text: str, file_type: str = "txt", pages=None, elements=None, sections=None):
    result = {
        "document_id": str(uuid.uuid4()),
        "source": f"test.{file_type}",
        "file_type": file_type,
        "metadata": {},
        "full_text": full_text,
    }
    if pages is not None:
        result["pages"] = pages
    if elements is not None:
        result["elements"] = elements
    if sections is not None:
        result["sections"] = sections
    return result


# ─── Recommender Unit Tests ───────────────────────────────────────────────────

class TestRecommender:
    def test_empty_stats_returns_default(self):
        result = recommend_recursive_chunk_size({"total_characters": 0})
        assert result == DEFAULT_CHUNK_SIZE

    def test_small_document_stays_within_bounds(self):
        stats = {
            "total_characters": 300,
            "median_paragraph_chars": 60,
            "avg_paragraph_chars": 60,
            "p90_paragraph_chars": 80,
            "p95_paragraph_chars": 90,
        }
        result = recommend_recursive_chunk_size(stats)
        assert MIN_RECOMMENDED_CHUNK_SIZE <= result <= DEFAULT_CHUNK_SIZE

    def test_normal_document_reasonable_recommendation(self):
        """Normal document with paragraphs around 100–200 chars should get ~600-900 range."""
        stats = {
            "total_characters": 20000,
            "median_paragraph_chars": 150,
            "avg_paragraph_chars": 160,
            "p75_paragraph_chars": 200,
            "p90_paragraph_chars": 260,
            "p95_paragraph_chars": 320,
        }
        result = recommend_recursive_chunk_size(stats)
        assert 400 <= result <= 2000
        # With median 150, P90 260: target ~ max(260*1.5=390, 150*3=450, 160*2.5=400) -> 450 -> 450 -> 450
        assert result >= 400

    def test_outlier_paragraph_does_not_dominate(self):
        """
        9 paragraphs ~150 chars + 1 outlier at 8000 chars.
        Result must NOT be 8000 and must NOT exceed MAX.
        """
        stats = {
            "total_characters": 9350,
            "median_paragraph_chars": 150,
            "avg_paragraph_chars": 935,   # inflated by outlier
            "p75_paragraph_chars": 160,
            "p90_paragraph_chars": 170,   # P90 still reflects normal paragraphs
            "p95_paragraph_chars": 4000,  # only P95 gets hit by outlier
        }
        result = recommend_recursive_chunk_size(stats)
        assert result != 8000
        assert result <= MAX_RECOMMENDED_CHUNK_SIZE
        assert result >= MIN_RECOMMENDED_CHUNK_SIZE

    def test_bounds_enforced_high(self):
        """Even with huge paragraphs, cap at MAX."""
        stats = {
            "total_characters": 500000,
            "median_paragraph_chars": 5000,
            "avg_paragraph_chars": 5000,
            "p90_paragraph_chars": 8000,
            "p95_paragraph_chars": 9000,
        }
        result = recommend_recursive_chunk_size(stats)
        assert result == MAX_RECOMMENDED_CHUNK_SIZE

    def test_bounds_enforced_low(self):
        """Even with tiny paragraphs, floor at MIN."""
        stats = {
            "total_characters": 50000,
            "median_paragraph_chars": 10,
            "avg_paragraph_chars": 10,
            "p90_paragraph_chars": 15,
            "p95_paragraph_chars": 20,
        }
        result = recommend_recursive_chunk_size(stats)
        assert result >= MIN_RECOMMENDED_CHUNK_SIZE

    def test_result_is_multiple_of_50(self):
        stats = {
            "total_characters": 30000,
            "median_paragraph_chars": 120,
            "avg_paragraph_chars": 130,
            "p90_paragraph_chars": 200,
            "p95_paragraph_chars": 280,
        }
        result = recommend_recursive_chunk_size(stats)
        assert result % 50 == 0


# ─── Analyzer Unit Tests ──────────────────────────────────────────────────────

class TestDocumentAnalyzer:
    def test_small_document(self):
        parsed = _make_parsed("Hello world. Short doc.")
        result = DocumentAnalyzer().analyze(parsed)
        assert result["total_characters"] == 23
        assert result["total_words"] > 0
        assert result["recommended_strategy"] == "recursive"
        assert MIN_RECOMMENDED_CHUNK_SIZE <= result["recommended_chunk_size"] <= DEFAULT_CHUNK_SIZE

    def test_normal_txt_document_statistics(self):
        paras = ["A" * 150, "B" * 200, "C" * 100, "D" * 180, "E" * 130]
        full_text = "\n\n".join(paras)
        parsed = _make_parsed(full_text, "txt")
        result = DocumentAnalyzer().analyze(parsed)

        assert result["paragraph_count"] == 5
        assert result["total_characters"] == len(full_text)
        assert result["min_paragraph_chars"] == 100
        assert result["max_paragraph_chars"] == 200
        assert result["recommended_strategy"] == "recursive"
        assert isinstance(result["recommended_chunk_size"], int)

    def test_outlier_paragraph_analysis(self):
        """9 normal paragraphs + 1 giant outlier of 8000 chars."""
        normal_paras = ["X" * 150 for _ in range(9)]
        outlier = "Y" * 8000
        all_paras = normal_paras + [outlier]
        full_text = "\n\n".join(all_paras)
        parsed = _make_parsed(full_text, "txt")
        result = DocumentAnalyzer().analyze(parsed)

        assert result["paragraph_count"] == 10
        assert result["max_paragraph_chars"] == 8000
        assert result["median_paragraph_chars"] == 150
        # P90 should still be around 150-8000, but chunk should not be 8000
        assert result["recommended_chunk_size"] != 8000
        assert result["recommended_chunk_size"] <= MAX_RECOMMENDED_CHUNK_SIZE

    def test_pdf_page_stats(self, tmp_path: Path):
        # Create a real PDF with 3 pages of varying text lengths
        pdf_path = tmp_path / "test.pdf"
        doc = pymupdf.open()
        for i, text in enumerate(["Short text.", "Medium length paragraph content here.", "A" * 500]):
            page = doc.new_page()
            page.insert_text((50, 50), text, fontsize=12)
        doc.save(str(pdf_path))
        doc.close()

        result = ingestion_service.parse(pdf_path, uuid.uuid4())
        analysis = result["analysis"]

        assert analysis["file_type"] == "pdf"
        assert analysis["page_count"] == 3
        assert analysis["avg_page_chars"] is not None
        assert analysis["median_page_chars"] is not None
        assert analysis["min_page_chars"] is not None
        assert analysis["max_page_chars"] is not None

    def test_empty_document_fallback(self):
        """Empty full_text should gracefully return default chunk size."""
        parsed = _make_parsed("", "txt")
        result = DocumentAnalyzer().analyze(parsed)
        assert result["total_characters"] == 0
        assert result["recommended_chunk_size"] == DEFAULT_CHUNK_SIZE

    def test_docx_heading_count(self, tmp_path: Path):
        docx_path = tmp_path / "test.docx"
        d = docx.Document()
        d.add_heading("Section 1", level=1)
        d.add_paragraph("Content of section 1.")
        d.add_heading("Section 2", level=2)
        d.add_paragraph("Content of section 2.")
        d.save(str(docx_path))

        result = ingestion_service.parse(docx_path, uuid.uuid4())
        analysis = result["analysis"]

        assert analysis["file_type"] == "docx"
        assert analysis["heading_count"] == 2
        assert analysis["recommended_strategy"] == "recursive"

    def test_markdown_section_count(self, tmp_path: Path):
        md_path = tmp_path / "test.md"
        md_path.write_text(
            "# Intro\n\nSome intro content.\n\n## Methods\n\nMethod details.\n\n## Results\n\nResult details.",
            encoding="utf-8"
        )

        result = ingestion_service.parse(md_path, uuid.uuid4())
        analysis = result["analysis"]

        assert analysis["file_type"] == "markdown"
        assert analysis["section_count"] is not None
        assert analysis["section_count"] >= 3
        assert analysis["recommended_strategy"] == "recursive"

    def test_multiple_resources_independent(self, tmp_path: Path):
        """Each resource must receive its own independent analysis."""
        txt1 = tmp_path / "doc1.txt"
        txt2 = tmp_path / "doc2.txt"

        # Small doc
        txt1.write_text("A" * 100, encoding="utf-8")
        # Large doc
        txt2.write_text(("\n\n".join(["B" * 300] * 50)), encoding="utf-8")

        r1 = ingestion_service.parse(txt1, uuid.uuid4())
        r2 = ingestion_service.parse(txt2, uuid.uuid4())

        a1 = r1["analysis"]
        a2 = r2["analysis"]

        assert a1["filename"] == "doc1.txt"
        assert a2["filename"] == "doc2.txt"
        assert a1["total_characters"] != a2["total_characters"]
        # Two different recommendations
        assert isinstance(a1["recommended_chunk_size"], int)
        assert isinstance(a2["recommended_chunk_size"], int)

    def test_analysis_error_fallback_in_service(self):
        """If analyzer raises, service should still return analysis with error key."""
        # Build a malformed parsed result (no full_text key at all)
        analyzer = DocumentAnalyzer()
        result = analyzer.analyze({
            "source": "bad.txt",
            "file_type": "txt",
            "full_text": "",
        })
        # Should not raise; returns graceful defaults
        assert result["recommended_strategy"] == "recursive"
        assert result["recommended_chunk_size"] == DEFAULT_CHUNK_SIZE
