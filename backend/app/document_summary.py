"""Use Gemini to summarize uploaded documents for display (type, purpose, key topics)."""
import os
from typing import Optional

# Reasonable limit so we don't blow context; Gemini gets the gist from the start
MAX_CHARS_FOR_SUMMARY = 30_000


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
