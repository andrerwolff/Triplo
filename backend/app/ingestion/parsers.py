"""
Document-type-specific extraction for the Ingestion Orchestrator.

Uses PyMuPDF for text and coordinate-aware extraction. Optional: Marker or
LlamaParse can be wired in for deeper layout/table analysis (see orchestrator).
"""

import io
import re
from typing import List, Optional, Tuple

import fitz  # PyMuPDF

from app.ingestion.models import RFIMetadata, SpecMetadata, SubmittalMetadata


def _normalize_section(s: str) -> str:
    """Normalize spec section for comparison (strip, upper, collapse spaces)."""
    if not s or not isinstance(s, str):
        return ""
    return " ".join(s.upper().split()).strip()


def _extract_text_by_page(pdf_bytes: bytes) -> list[tuple[int, str]]:
    """Extract plain text per page. Returns list of (1-based_page_number, text)."""
    if not pdf_bytes:
        return []
    try:
        doc = fitz.open(stream=io.BytesIO(pdf_bytes), filetype="pdf")
        result = []
        for i in range(len(doc)):
            page = doc.load_page(i)
            result.append((i + 1, page.get_text().strip()))
        doc.close()
        return result
    except Exception:
        return []


def _get_first_page_dict(pdf_bytes: bytes) -> Optional[List]:
    """Get PyMuPDF 'dict' structure for first page (blocks with bbox) for coordinate-aware parsing."""
    if not pdf_bytes:
        return None
    try:
        doc = fitz.open(stream=io.BytesIO(pdf_bytes), filetype="pdf")
        if len(doc) == 0:
            doc.close()
            return None
        page = doc.load_page(0)
        data = page.get_text("dict")
        doc.close()
        return data.get("blocks") if isinstance(data, dict) else None
    except Exception:
        return None


# --- Spec (Part 1: Section ID, Title, Required Submittals) ---

# CSI section pattern: digits and spaces e.g. "03 30 00", "01 23 45 00"
_CSI_SECTION_RE = re.compile(
    r"\b(\d{2}\s+\d{2}\s+\d{2}(?:\s+\d{2})?)\b",
    re.IGNORECASE,
)
# Part 1 marker
_PART1_RE = re.compile(r"PART\s+1\s*(?:[-–—]\s*)?(?:GENERAL|SCOPE)?", re.IGNORECASE)
# Submittal list bullets/numbers under Part 1
_SUBMITTAL_ITEM_RE = re.compile(
    r"(?:^|\n)\s*(?:\d+\.|[•\-\*])\s*([A-Za-z0-9][^\n]{5,120})",
    re.MULTILINE,
)


def extract_spec_metadata(pdf_bytes: bytes) -> Tuple[SpecMetadata, float, list[str]]:
    """
    Extract Section ID, Title, and required Submittal types from Part 1 of a spec PDF.
    Returns (SpecMetadata, confidence 0–1, list of risks).
    """
    pages = _extract_text_by_page(pdf_bytes)
    full_text = "\n\n".join(t for _, t in pages)
    risks: list[str] = []
    section_id = ""
    title = ""
    required_submittal_types: list[str] = []

    if not full_text or len(full_text) < 50:
        return (
            SpecMetadata(section_id="", title="", required_submittal_types=[]),
            0.0,
            ["Document is empty or could not be extracted"],
        )

    # Prefer first few pages for section header (title page / Part 1)
    header_text = "\n".join(t for _, t in pages[:5])
    # Section number: often at start or near "SECTION" keyword
    section_match = re.search(
        r"SECTION\s+(\d{2}\s+\d{2}\s+\d{2}(?:\s+\d{2})?)",
        header_text,
        re.IGNORECASE,
    )
    if section_match:
        section_id = _normalize_section(section_match.group(1))
    else:
        for m in _CSI_SECTION_RE.finditer(header_text):
            cand = _normalize_section(m.group(1))
            if cand and len(cand) >= 5:
                section_id = cand
                break

    # Title: line after section number or first substantial line
    if section_id:
        after_section = re.split(re.escape(section_id), header_text, 1, re.IGNORECASE)
        if len(after_section) > 1:
            rest = after_section[1].strip()
            title = rest.split("\n")[0].strip()[:200] if rest else ""
    if not title:
        lines = [ln.strip() for ln in header_text.split("\n") if len(ln.strip()) > 10]
        if lines:
            title = lines[0][:200]

    # Part 1 / Submittals
    part1_pos = _PART1_RE.search(full_text)
    if part1_pos:
        chunk = full_text[part1_pos.start() : part1_pos.start() + 4000]
        submittal_section = re.search(
            r"1\.1\s+Submittals?|Submittals?\s*:?\s*(?:Include|Submit|Provide)",
            chunk,
            re.IGNORECASE,
        )
        if submittal_section:
            start = submittal_section.start()
            end = min(start + 2500, len(chunk))
            sub_chunk = chunk[start:end]
            for m in _SUBMITTAL_ITEM_RE.finditer(sub_chunk):
                item = m.group(1).strip()
                if item and "submittal" not in item.lower()[:20]:
                    required_submittal_types.append(item[:150])
    else:
        risks.append("Part 1 (GENERAL) not clearly identified; submittal list may be incomplete")

    # Dedupe and clean submittal types
    seen = set()
    unique = []
    for s in required_submittal_types:
        key = s.lower()[:80]
        if key not in seen:
            seen.add(key)
            unique.append(s)
    required_submittal_types = unique[:30]

    # Confidence: higher when we have section + title + at least one submittal type
    score = 0.0
    if section_id:
        score += 0.35
    if title:
        score += 0.35
    if required_submittal_types:
        score += 0.3
    else:
        score += 0.1  # Part 1 present but no list
    if not part1_pos:
        score *= 0.85
    confidence = min(1.0, score)

    return (
        SpecMetadata(
            section_id=section_id,
            title=title,
            required_submittal_types=required_submittal_types,
        ),
        confidence,
        risks,
    )


# --- Submittal (cover sheet: Submittal #, Rev, Spec Section; coordinate-aware) ---

_COVER_SHEET_LABELS = [
    ("submittal no", "submittal_number", r"#?\s*[:.]?\s*([A-Za-z0-9\-_]+)"),
    ("submittal number", "submittal_number", r"#?\s*[:.]?\s*([A-Za-z0-9\-_]+)"),
    ("revision", "revision", r"[:.]?\s*(\d+|Rev\s*\.?\s*\d+|[\w\-]+)"),
    ("rev\b", "revision", r"[:.]?\s*(\d+|Rev\s*\.?\s*\d+|[\w\-]+)"),
    ("spec section", "spec_section", r"[:.]?\s*([\d\s\-\.]+)"),
    ("section", "spec_section", r"[:.]?\s*(\d{2}\s*\d{2}\s*\d{2}[\s\d]*)"),
]
_SIGNATURE_RISK_PHRASES = ["signature", "signed", "approval", "approved by"]


def _parse_cover_sheet_from_dict(blocks: list) -> Tuple[str, str, str]:
    """From coordinate-aware blocks, try to find label-value pairs for submittal #, rev, spec section."""
    submittal_number = ""
    revision = ""
    spec_section = ""
    if not blocks:
        return submittal_number, revision, spec_section

    # Build list of (y, x0, text) for ordering
    fragments: list[tuple[float, float, str]] = []
    for block in blocks:
        bbox = block.get("bbox") or (0, 0, 0, 0)
        y0, x0 = bbox[1], bbox[0]
        for line in block.get("lines") or []:
            for span in line.get("spans") or []:
                text = (span.get("text") or "").strip()
                if text:
                    fragments.append((y0, x0, text))

    full_line = " ".join(t for _, _, t in fragments).lower()
    # Fallback: regex on combined text
    for label_key, field, pattern in _COVER_SHEET_LABELS:
        if label_key not in full_line:
            continue
        try:
            re_pat = re.compile(
                re.escape(label_key) + pattern,
                re.IGNORECASE,
            )
            m = re.search(re_pat, " ".join(t for _, _, t in fragments))
            if m:
                val = m.group(1).strip()
                if field == "submittal_number" and not submittal_number:
                    submittal_number = val
                elif field == "revision" and not revision:
                    revision = val
                elif field == "spec_section" and not spec_section:
                    spec_section = _normalize_section(val)
        except Exception:
            continue

    # Fallback: plain text regex on first page if dict didn't yield enough
    if not spec_section:
        first_page_text = " ".join(t for _, _, t in fragments)
        sec_m = re.search(
            r"(?:spec\s*section|section)\s*[:.]?\s*(\d{2}\s*\d{2}\s*\d{2}(?:\s*\d{2})?)",
            first_page_text,
            re.IGNORECASE,
        )
        if sec_m:
            spec_section = _normalize_section(sec_m.group(1))

    return submittal_number, revision, spec_section


def extract_submittal_metadata(pdf_bytes: bytes) -> Tuple[SubmittalMetadata, float, list[str]]:
    """
    Extract cover sheet info (Submittal #, Rev, Spec Section) using coordinate-aware parsing.
    Returns (SubmittalMetadata, confidence 0–1, list of risks).
    """
    risks: list[str] = []
    pages = _extract_text_by_page(pdf_bytes)
    first_page_text = pages[0][1] if pages else ""
    blocks = _get_first_page_dict(pdf_bytes)

    submittal_number = ""
    revision = ""
    spec_section = ""

    if blocks:
        submittal_number, revision, spec_section = _parse_cover_sheet_from_dict(blocks)
    if not submittal_number and first_page_text:
        m = re.search(
            r"Submittal\s*#?\s*[:.]?\s*([A-Za-z0-9\-_]+)",
            first_page_text,
            re.IGNORECASE,
        )
        if m:
            submittal_number = m.group(1).strip()
    if not revision and first_page_text:
        m = re.search(
            r"Re(?:vision|v)\.?\s*[:.]?\s*(\d+|[\w\-]+)",
            first_page_text,
            re.IGNORECASE,
        )
        if m:
            revision = m.group(1).strip()
    if not spec_section and first_page_text:
        m = re.search(
            r"(?:Spec\s*)?Section\s*[:.]?\s*(\d{2}\s*\d{2}\s*\d{2}(?:\s*\d{2})?)",
            first_page_text,
            re.IGNORECASE,
        )
        if m:
            spec_section = _normalize_section(m.group(1))

    # Risk: missing signature on cover sheet
    combined = first_page_text.lower()
    if not any(p in combined for p in _SIGNATURE_RISK_PHRASES):
        risks.append("Missing or unclear signature/approval block on cover sheet")

    score = 0.0
    if submittal_number:
        score += 0.4
    if spec_section:
        score += 0.4
    if revision:
        score += 0.2
    confidence = min(1.0, score) if (submittal_number or spec_section) else 0.3

    return (
        SubmittalMetadata(
            submittal_number=submittal_number,
            revision=revision,
            spec_section=spec_section,
        ),
        confidence,
        risks,
    )


# --- RFI (Question, Suggested Solution, cost/schedule flags) ---

_RFI_QUESTION_PATTERNS = [
    r"(?:question|rfi\s*question|description)\s*[:.]?\s*(.+?)(?=(?:suggested|response|answer)|$)",
    r"(?:what|how|when|where|please)\s+([^\n]{20,500})",
]
_RFI_SOLUTION_PATTERNS = [
    r"Suggested\s*Solution\s*[:.]?\s*(.+?)(?=(?:cost|schedule|impact)|$)",
    r"Recommend(?:ed)?\s*(?:Solution|Response)?\s*[:.]?\s*(.+?)(?=\n\n|$)",
]
_COST_KEYWORDS = re.compile(
    r"\b(cost|pricing|price|budget|additional\s+cost|cost\s+impact|expense)\b",
    re.IGNORECASE,
)
_SCHEDULE_KEYWORDS = re.compile(
    r"\b(schedule|time\s+impact|delay|duration|calendar|milestone|critical\s+path)\b",
    re.IGNORECASE,
)


def extract_rfi_metadata(pdf_bytes: bytes) -> Tuple[RFIMetadata, float, list[str]]:
    """
    Extract Question, Suggested Solution, and cost/schedule flags from an RFI PDF.
    Returns (RFIMetadata, confidence 0–1, list of risks).
    """
    risks: list[str] = []
    pages = _extract_text_by_page(pdf_bytes)
    full_text = "\n\n".join(t for _, t in pages)

    question = ""
    suggested_solution = ""
    for pattern in _RFI_QUESTION_PATTERNS:
        m = re.search(pattern, full_text, re.IGNORECASE | re.DOTALL)
        if m:
            question = m.group(1).strip()[:2000]
            break
    for pattern in _RFI_SOLUTION_PATTERNS:
        m = re.search(pattern, full_text, re.IGNORECASE | re.DOTALL)
        if m:
            suggested_solution = m.group(1).strip()[:2000]
            break

    mentions_cost = bool(_COST_KEYWORDS.search(full_text))
    mentions_schedule = bool(_SCHEDULE_KEYWORDS.search(full_text))

    if not question and len(full_text) > 100:
        question = full_text[:1500].strip()
        risks.append("Question not clearly identified; first portion of text used")

    score = 0.3
    if question:
        score += 0.4
    if suggested_solution:
        score += 0.2
    if mentions_cost or mentions_schedule:
        score += 0.1
    confidence = min(1.0, score)

    return (
        RFIMetadata(
            question=question,
            suggested_solution=suggested_solution,
            mentions_cost=mentions_cost,
            mentions_schedule=mentions_schedule,
        ),
        confidence,
        risks,
    )
