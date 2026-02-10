"""Extract text from PDF and DOCX. No UI dependencies."""
import hashlib
import io
from collections import OrderedDict
from typing import Optional

from docx import Document
import fitz  # PyMuPDF

_MAX_CACHE = 128
_pdf_cache = OrderedDict()
_docx_cache = OrderedDict()


def _content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _cache_get(cache: OrderedDict, key: str):
    if key not in cache:
        return None
    cache.move_to_end(key)
    return cache[key]


def _cache_set(cache: OrderedDict, key: str, value, maxsize: int = _MAX_CACHE):
    cache[key] = value
    cache.move_to_end(key)
    while len(cache) > maxsize:
        cache.popitem(last=False)


def extract_text_from_pdf(pdf_bytes: bytes) -> Optional[str]:
    if not pdf_bytes:
        return None
    key = _content_hash(pdf_bytes)
    cached = _cache_get(_pdf_cache, key)
    if cached is not None:
        return cached
    try:
        stream = io.BytesIO(pdf_bytes)
        doc = fitz.open(stream=stream, filetype="pdf")
        text = ""
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text += page.get_text()
        doc.close()
        result = text.strip() or "No extractable text found (possibly an image-based PDF)"
    except Exception:
        result = None
    _cache_set(_pdf_cache, key, result)
    return result


def extract_text_from_docx(docx_bytes: bytes) -> Optional[str]:
    if not docx_bytes:
        return None
    key = _content_hash(docx_bytes)
    cached = _cache_get(_docx_cache, key)
    if cached is not None:
        return cached
    try:
        stream = io.BytesIO(docx_bytes)
        doc = Document(stream)
        result = "\n".join(para.text for para in doc.paragraphs)
    except Exception:
        result = None
    _cache_set(_docx_cache, key, result or "")
    return result or ""


def extract_text_from_file(filename: str, content: bytes) -> Optional[str]:
    """Dispatch by extension. Returns extracted text or None on error."""
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        return extract_text_from_pdf(content)
    if name.endswith(".docx"):
        return extract_text_from_docx(content)
    if name.endswith(".txt"):
        return content.decode("utf-8", errors="replace")
    return None
