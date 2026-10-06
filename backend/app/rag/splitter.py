import logging
from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


def split_text(
    text: str,
    chunk_size: int = 600,
    chunk_overlap: int | None = None,
    separators: List[str] | None = None,
) -> List[str]:
    """
    Split text recursively based on recommended chunk size.

    Args:
        text: Raw document text to split.
        chunk_size: Target size of each chunk in characters (from document analysis).
        chunk_overlap: Overlap between chunks (defaults to 20% of chunk_size if None).
        separators: Optional list of separator strings to use.

    Returns:
        List of text chunks.
    """
    if not text or not text.strip():
        return []

    if chunk_overlap is None:
        chunk_overlap = max(0, int(chunk_size * 0.2))

    if separators is None:
        separators = ["\n\n", "\n", " ", ""]

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=separators,
        length_function=len,
    )

    chunks = splitter.split_text(text)
    logger.info(
        f"Split document into {len(chunks)} chunks with chunk_size={chunk_size}, overlap={chunk_overlap}"
    )
    return chunks
