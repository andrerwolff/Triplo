"""Use Gemini to summarize uploaded documents for display (type, purpose, key topics)."""
import os
import re
from typing import Optional

from app.constants import CSI_DIVS

# Reasonable limit so we don't blow context; Gemini gets the gist from the start
MAX_CHARS_FOR_SUMMARY = 30_000

# Look at the first N chars for division/section hints (specs usually state this early)
MAX_CHARS_FOR_CSI_INFER = 15_000


def infer_csi_division_from_text(extracted_text: str, _filename: str = "") -> Optional[str]:
    """
    Infer a CSI division from extracted document text using heuristics.
    Prefer matches in the first part of the document (specs/submittals often state division early).
    Returns one of the CSI_DIVS strings, or None if no clear match.
    """
    text = (extracted_text or "").strip()
    if not text:
        return None
    head = text[:MAX_CHARS_FOR_CSI_INFER].upper()

    # Build division number -> full CSI label (e.g. "01" -> "01 - GENERAL REQUIREMENTS")
    div_to_label: dict[str, str] = {}
    for label in CSI_DIVS:
        if " - " in label:
            num = label.split(" - ", 1)[0].strip()
            div_to_label[num] = label

    # 1) "Division 01" or "DIVISION 01"
    m = re.search(r"\bDIVISION\s*(\d{2})\b", head, re.IGNORECASE)
    if m:
        num = m.group(1)
        if num in div_to_label:
            return div_to_label[num]

    # 2) "Section 09 29 00" or "Section 01 11 00" (MasterFormat) -> first two digits are division
    m = re.search(r"\bSECTION\s*(\d{2})\s*\d{2}\s*\d{2}\b", head, re.IGNORECASE)
    if m:
        num = m.group(1)
        if num in div_to_label:
            return div_to_label[num]

    # 3) Standalone "09 29 00" or "01 11 00" in heading
    m = re.search(r"\b(\d{2})\s+\d{2}\s+\d{2}\b", head)
    if m:
        num = m.group(1)
        if num in div_to_label:
            return div_to_label[num]

    # 4) Exact or prominent substring of a CSI label (e.g. "09 - FINISHES" or "GENERAL REQUIREMENTS")
    for label in CSI_DIVS:
        if label.upper() in head:
            return label
        # Label without number, e.g. "GENERAL REQUIREMENTS" for "01 - GENERAL REQUIREMENTS"
        if " - " in label:
            suffix = label.split(" - ", 1)[1].strip().upper()
            if len(suffix) > 4 and suffix in head:
                return label

    return None


def summarize_document(filename: str, extracted_text: str) -> Optional[str]:
    """
    Use Gemini to describe what the document is: type, purpose, main topics.
    Returns a short summary string, or None if API key is missing or the call fails.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or not api_key.strip():
        return None

    text = (extracted_text or "").strip()
    if not text:
        return "Empty or unreadable document."

    if len(text) > MAX_CHARS_FOR_SUMMARY:
        text = text[:MAX_CHARS_FOR_SUMMARY] + "\n\n[... truncated for summary]"

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model_name = os.environ.get("GEMINI_AUDIT_MODEL", "gemini-2.5-flash")
        model = genai.GenerativeModel(
            model_name,
            generation_config=genai.types.GenerationConfig(
                temperature=0.2,
                max_output_tokens=512,
            ),
        )

        prompt = f"""You are summarizing an uploaded document for a construction/project management app.

Filename: {filename or "unknown"}

Based on the following extracted text, provide a brief description (2–4 sentences) that explains:
- What kind of document this is (e.g. specification, submittal, product data, drawing list).
- What it covers or its main purpose.
- Any key topics, sections, or identifiers (e.g. CSI division, product names) if obvious.

Write in clear, neutral language. Do not include the full text—only your summary.

Document text:
---
{text}
---"""

        response = model.generate_content(prompt)
        if response and response.text:
            return response.text.strip()
    except Exception:
        pass
    return None
