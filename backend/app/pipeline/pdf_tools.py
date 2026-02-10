"""
PDF parsing for the audit pipeline.

Uses PyMuPDF (fitz) for page-level extraction so extraction_agent can return
page numbers for every value. Reuses app.extractors where appropriate.
"""

import io
from typing import List, Optional, Tuple

import fitz  # PyMuPDF


def extract_text_by_page(pdf_bytes: bytes) -> List[Tuple[int, str]]:
    """
    Extract text from a PDF with one string per page.

    Returns:
        List of (page_number_1based, page_text). Page numbers are 1-based for user display.
    """
    if not pdf_bytes:
        return []
    try:
        stream = io.BytesIO(pdf_bytes)
        doc = fitz.open(stream=stream, filetype="pdf")
        result: List[Tuple[int, str]] = []
        for i in range(len(doc)):
            page = doc.load_page(i)
            text = page.get_text().strip()
            result.append((i + 1, text))  # 1-based page number
        doc.close()
        return result
    except Exception:
        return []


def extract_full_text(pdf_bytes: bytes) -> str:
    """Single concatenated text of all pages (with page markers). For fallback or small docs."""
    pages = extract_text_by_page(pdf_bytes)
    if not pages:
        return ""
    return "\n\n".join(f"[Page {pn}]\n{text}" for pn, text in pages)


def get_page_count(pdf_bytes: bytes) -> int:
    """Return number of pages in the PDF."""
    if not pdf_bytes:
        return 0
    try:
        stream = io.BytesIO(pdf_bytes)
        doc = fitz.open(stream=stream, filetype="pdf")
        n = len(doc)
        doc.close()
        return n
    except Exception:
        return 0


def extract_toc_from_text(full_text: str) -> List[dict]:
    """
    Heuristic: try to find TOC-like structure in extracted text.

    Returns list of {"title": str, "page": int or None}. Used when no explicit
    TOC is present; LLM can also extract TOC from page-by-page text.
    """
    # Placeholder: real TOC detection could use regex for ".... 12" style page refs
    # or delegate to extraction_agent. Here we return empty; triage_agent uses
    # extraction_agent output for TOC when needed.
    return []
