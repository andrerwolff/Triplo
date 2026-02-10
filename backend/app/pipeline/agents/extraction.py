"""
Extraction agent: multimodal extraction of technical attributes from spec and submittal PDFs.

Returns structured data with Page Number for every value and a Confidence Score per item.
Uses gpt-4o or gemini-1.5-pro (configurable); output forced into strict JSON schema.
"""

import json
import os
import re
from typing import Any, Optional

from app.pipeline.pdf_tools import extract_text_by_page
from app.pipeline.schemas import SpecExtractionItem
from app.pipeline.state import (
    ActionSubmittalItem,
    SubmittalTOCEntry,
    SpecRequirement,
    SubmittalDataPoint,
    SubmittalState,
)


EXTRACTION_ATTRIBUTES = [
    "Material",
    "Finish",
    "Fire Rating",
    "Manufacturer",
    "Model",
    "Dimensions",
    "Thickness",
    "R-Value",
    "Test Standard",
    "Warranty",
    "Color",
]

MAX_CHARS_PER_PAGE = 8000
MAX_PAGES_PER_DOC = 200


def filter_data_points(
    all_data: list[SubmittalDataPoint],
    visual_selections: dict[str, Any],
) -> list[SubmittalDataPoint]:
    """
    Filter submittal data points using visual extraction as a 'Master Key'.

    visual_selections: Same shape as run_visual_extraction(...)["final_selection"]:
        keys "page_N", each value has "page_number" (int) and "highlighted_model_or_value" (str).
    - Pages with no visual selection: keep all data points on that page.
    - Pages with non-empty highlighted_model_or_value: keep only data points that match
      the master value (value equals or contains it, or key is Model/Manufacturer and value matches).
    """
    page_to_master: dict[int, str] = {}
    for key, entry in visual_selections.items():
        if not isinstance(entry, dict):
            continue
        master = (entry.get("highlighted_model_or_value") or "").strip()
        if not master:
            continue
        page_num = entry.get("page_number")
        if page_num is not None:
            page_to_master[int(page_num)] = master

    if not page_to_master:
        return list(all_data)

    result: list[SubmittalDataPoint] = []
    for dp in all_data:
        master_value = page_to_master.get(dp.page_number)
        if master_value is None:
            result.append(dp)
            continue
        val = (dp.value or "").strip().lower()
        master_lower = master_value.strip().lower()
        if val == master_lower or master_lower in val:
            result.append(dp)
    return result


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + "\n[... truncated]"


def _build_spec_extraction_prompt(pages: list[tuple[int, str]]) -> str:
    """Build prompt for spec extraction with page context."""
    parts = [
        "Extract technical requirements from this Specification document. "
        "For each requirement found, you MUST include the exact page number (1-based) where you found it. "
        "Also provide a confidence score between 0.0 and 1.0 for each extraction; if you are unsure, use a lower score (e.g. 0.6). "
        "Focus on attributes such as: " + ", ".join(EXTRACTION_ATTRIBUTES) + ". "
        "Include any other explicit performance or product requirements.\n\n",
    ]
    for page_num, text in pages[:MAX_PAGES_PER_DOC]:
        parts.append(f"--- Page {page_num} ---\n")
        parts.append(_truncate(text, MAX_CHARS_PER_PAGE))
        parts.append("\n\n")
    parts.append(
        "\nRespond with a single JSON object only (no markdown, no code fence), using this exact structure:\n"
        '{"requirements": [{"key": "...", "value": "...", "citation": "...", "page_number": <int>, "confidence": <0.0-1.0>}]}'
    )
    return "".join(parts)


def _build_submittal_extraction_prompt(pages: list[tuple[int, str]]) -> str:
    """Build prompt for submittal extraction with page context."""
    parts = [
        "Extract submitted product/data from this Contractor Submittal document. "
        "For each value found, you MUST include the exact page number (1-based) where you found it. "
        "Provide a confidence score between 0.0 and 1.0 for each; if unsure, use a lower score (e.g. 0.6). "
        "Focus on: " + ", ".join(EXTRACTION_ATTRIBUTES) + ", and any other technical data.\n\n",
    ]
    for page_num, text in pages[:MAX_PAGES_PER_DOC]:
        parts.append(f"--- Page {page_num} ---\n")
        parts.append(_truncate(text, MAX_CHARS_PER_PAGE))
        parts.append("\n\n")
    parts.append(
        "\nRespond with a single JSON object only (no markdown, no code fence):\n"
        '{"data_points": [{"key": "...", "value": "...", "page_number": <int>, "confidence": <0.0-1.0>}]}'
    )
    return "".join(parts)


def _build_toc_extraction_prompt(pages: list[tuple[int, str]]) -> str:
    """Build prompt to extract Table of Contents from submittal (first few pages)."""
    parts = [
        "From this submittal document, extract the Table of Contents (or list of included documents/sections). "
        "For each entry, provide the title and page number if stated.\n\n",
    ]
    for page_num, text in pages[:20]:
        parts.append(f"--- Page {page_num} ---\n")
        parts.append(_truncate(text, MAX_CHARS_PER_PAGE))
        parts.append("\n\n")
    parts.append(
        "\nRespond with a single JSON object only:\n"
        '{"entries": [{"title": "...", "page": <int or null>}]}'
    )
    return "".join(parts)


def _build_action_submittal_prompt(pages: list[tuple[int, str]]) -> str:
    """Build prompt to extract required Action Submittal items from spec."""
    parts = [
        "From this Specification, extract the list of required Action Submittal items "
        "(e.g. Shop Drawings, Product Data, Samples, Test Reports, Warranty). "
        "For each item, give a short name and the spec citation (section/paragraph) if available.\n\n",
    ]
    for page_num, text in pages[:MAX_PAGES_PER_DOC]:
        parts.append(f"--- Page {page_num} ---\n")
        parts.append(_truncate(text, MAX_CHARS_PER_PAGE))
        parts.append("\n\n")
    parts.append(
        "\nRespond with a single JSON object only:\n"
        '{"items": [{"name": "...", "citation": "..."}]}'
    )
    return "".join(parts)


def _parse_json_from_llm(text: str) -> dict[str, Any]:
    """Extract JSON from LLM response; strip markdown if present."""
    raw = text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```\s*$", "", raw)
    start = raw.find("{")
    if start >= 0:
        raw = raw[start:]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        try:
            import json_repair
            return json_repair.loads(raw)
        except Exception:
            return {}


def _call_llm(system: str, user: str, response_schema: Optional[dict] = None) -> str:
    """Call configured LLM (Gemini or OpenAI). Returns raw text."""
    use_openai = os.environ.get("EXTRACTION_LLM", "gemini").lower() == "openai"
    if use_openai:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set for extraction.")
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            model = os.environ.get("OPENAI_EXTRACTION_MODEL", "gpt-4o")
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.1,
                response_format={"type": "json_object"} if response_schema is not None else None,
            )
            return (resp.choices[0].message.content or "").strip()
        except ImportError:
            raise ValueError("openai package not installed. pip install openai")
    else:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set for extraction.")
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model_name = os.environ.get("GEMINI_EXTRACTION_MODEL", "gemini-1.5-pro")
        model = genai.GenerativeModel(
            model_name,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                max_output_tokens=8192,
                response_mime_type="application/json",
            ),
        )
        response = model.generate_content([system, user])
        if not response or not response.text:
            raise RuntimeError("Gemini returned no text.")
        return response.text.strip()


SYSTEM_EXTRACTION = (
    "You are a technical document analyst. Extract only what is explicitly stated. "
    "Do not infer or hallucinate. Every extracted value must include the page_number where it appears. "
    "Output must be valid JSON matching the requested schema exactly."
)


def extraction_agent(state: SubmittalState, spec_pdf_bytes: bytes, submittal_pdf_bytes: bytes) -> SubmittalState:
    """
    Multimodal extraction from spec and submittal PDFs.

    - Extracts spec requirements (with page numbers and confidence).
    - Extracts action submittal requirements from spec.
    - Extracts submittal TOC and submittal data points (with page numbers and confidence).
    - Populates human_review_items for any extraction with confidence < 0.8.
    """
    spec_pages = extract_text_by_page(spec_pdf_bytes)
    submittal_pages = extract_text_by_page(submittal_pdf_bytes)

    # 1) Spec requirements
    if spec_pages:
        prompt = _build_spec_extraction_prompt(spec_pages)
        raw = _call_llm(SYSTEM_EXTRACTION, prompt)
        data = _parse_json_from_llm(raw)
        reqs = data.get("requirements") or []
        state.spec_requirements = []
        for r in reqs:
            if isinstance(r, dict):
                try:
                    item = SpecExtractionItem(
                        key=str(r.get("key", "")),
                        value=str(r.get("value", "")),
                        citation=str(r.get("citation", "")),
                        page_number=int(r.get("page_number", 1)),
                        confidence=float(r.get("confidence", 0.9)),
                    )
                    state.spec_requirements.append(
                        SpecRequirement(
                            key=item.key,
                            value=item.value,
                            citation=item.citation,
                            source_page=item.page_number,
                            confidence=item.confidence,
                        )
                    )
                except (ValueError, TypeError):
                    continue

    # 2) Action submittal requirements from spec
    if spec_pages:
        prompt = _build_action_submittal_prompt(spec_pages)
        raw = _call_llm(SYSTEM_EXTRACTION, prompt)
        data = _parse_json_from_llm(raw)
        items = data.get("items") or []
        state.action_submittal_requirements = []
        for it in items:
            if isinstance(it, dict) and it.get("name"):
                state.action_submittal_requirements.append(
                    ActionSubmittalItem(name=str(it["name"]), citation=str(it.get("citation", "")))
                )

    # 3) Submittal TOC
    if submittal_pages:
        prompt = _build_toc_extraction_prompt(submittal_pages)
        raw = _call_llm(SYSTEM_EXTRACTION, prompt)
        data = _parse_json_from_llm(raw)
        entries = data.get("entries") or []
        state.submittal_toc = []
        for e in entries:
            if isinstance(e, dict) and e.get("title"):
                p = e.get("page")
                state.submittal_toc.append(
                    SubmittalTOCEntry(title=str(e["title"]), page=int(p) if p is not None and str(p).isdigit() else None)
                )

    # 4) Submittal data points (with page and confidence)
    if submittal_pages:
        prompt = _build_submittal_extraction_prompt(submittal_pages)
        raw = _call_llm(SYSTEM_EXTRACTION, prompt)
        data = _parse_json_from_llm(raw)
        points = data.get("data_points") or []
        state.submittal_data = []
        human_review_keys: list[str] = []
        for p in points:
            if not isinstance(p, dict):
                continue
            try:
                conf = float(p.get("confidence", 0.9))
                key = str(p.get("key", ""))
                if conf < 0.8:
                    human_review_keys.append(key)
                state.submittal_data.append(
                    SubmittalDataPoint(
                        key=key,
                        value=str(p.get("value", "")),
                        page_number=int(p.get("page_number", 1)),
                        confidence=conf,
                        human_review_required=conf < 0.8,
                    )
                )
            except (ValueError, TypeError):
                continue
        state.human_review_items = list(dict.fromkeys(human_review_keys))

    return state
