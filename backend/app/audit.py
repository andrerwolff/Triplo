"""Technical Submittal Auditor: LLM-powered comparison of specs vs submittals.

Uses structured JSON (Verified Requirements + Filtered Submittal Data) only; no raw
truncated text. Pre-audit unit normalization marks exact matches before the LLM sees them.
"""
import json
import os
import re
from typing import Any, Optional

from app.pipeline.units import values_equivalent

SYSTEM_PROMPT = """You are a Lead Technical Auditor for a premier Architecture & Engineering firm. Your goal is to conduct a rigorous, objective comparison between a Project Specification (Source of Truth) and a Contractor Submittal (Evidence). Your tone is professional, concise, and purely technical.

Operational Guidelines:
- Strict Grounding: Base every claim on the provided text. If a value is not present in the submittal, state "Not Provided." Do not assume or hallucinate performance data.
- Citation Requirement: Every requirement identified from the Specification must include a reference (e.g., Section 09 29 00, Para 2.1.A). For each requirement, cite spec section and paragraph.
- Conflict Resolution: Prioritize the Specification. If the Submittal offers a "better" product than specified, still flag it as a "Deviation" because it may impact the project budget or interface with other trades.
- Unit Consistency: If spec and submittal use different units (e.g. Metric vs Imperial), convert to a common unit before comparing and state the conversion used.

Evaluation Protocol:
For every submittal review, follow these steps:
- Phase 1 (Spec Extraction): Identify the required Manufacturer, Model, Performance Ratings, Testing Certifications, and required Submittal components (Shop Drawings, Samples, etc.).
- Phase 2 (Submittal Analysis): Extract corresponding data from the Submittal.
- Phase 3 (Comparison): Execute a line-by-line comparison.

You must respond with valid JSON only. No markdown code fences, no commentary outside the JSON. Use this exact schema:

{
  "summary_table": [
    {
      "feature": "string (e.g. Manufacturer)",
      "spec_requirement": "string with citation e.g. Brand X (Section 08 71 00, Para 2.1.B)",
      "submitted_value": "string or 'Not Provided'",
      "status": "Pass | Fail | Deviated | Missing"
    }
  ],
  "compliance_narrative": "Brief paragraph on whether the submittal meets design intent.",
  "missing_information": ["string list of missing documents e.g. Missing ASTM E84 test report"],
  "critical_deviations": ["string list of deal-breakers with citations"],
  "detailed_discrepancies": [
    { "item": "string", "risk": "string explaining impact" }
  ],
  "suggested_action": "APPROVED | APPROVED_AS_NOTED | REVISE_AND_RESUBMIT | REJECTED"
}"""

CHECKLIST = """
Evaluate the submittal against the Specification using these categories. For each requirement, cite spec section and paragraph.

1. Administrative & Scope Compliance
   - Exact Match: Does the submittal's manufacturer and model number match the "Basis of Design" listed in the specs?
   - Completeness: Does the submittal include all components required by the spec (e.g., shop drawings, product data, warranties, and maintenance manuals)?
   - Substitution Status: Is the contractor proposing a substitution ("or equal"), or are they submitting the specified product?

2. Technical Specifications
   - Performance Ratings: Does the submitted product meet or exceed the required performance values (e.g., R-value, fire rating, PSI strength, voltage, or load capacity)?
   - Physical Properties: Do the dimensions, materials, and finishes match the architectural requirements?
   - Testing & Certifications: Are the required third-party test reports (UL, ASTM, FM Global) attached and current?

3. Sustainability & Compliance
   - Regulatory: Does the product comply with local building codes referenced in the spec?
   - Green Requirements: Does it meet LEED, VOC limits, or recycled content requirements specified for this project?

4. Discrepancy Identification
   - Red Flags: Identify any "Exclusions" or "Limitations" mentioned in the submittal that conflict with the project requirements.
   - Deviations: List every instance where the submittal provides a value lower than the specification requirement.
"""

def compute_prematched_pairs(
    verified_requirements: list[dict[str, Any]],
    filtered_submittal_data: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Pre-audit unit normalization: find spec/submittal pairs that are equivalent
    (e.g. 2 hours vs 120 min). Return (exact_match_entries, remaining_spec_requirements).
    """
    sub_by_key: dict[str, dict[str, Any]] = {}
    for dp in filtered_submittal_data:
        k = (dp.get("key") or "").strip().lower()
        if k:
            sub_by_key[k] = dp

    exact_match_entries: list[dict[str, Any]] = []
    remaining_spec_requirements: list[dict[str, Any]] = []

    for req in verified_requirements:
        spec_key = (req.get("key") or "").strip()
        spec_value = (req.get("value") or "").strip()
        citation = (req.get("citation") or "").strip()
        key_lower = spec_key.lower()
        sub = sub_by_key.get(key_lower) if key_lower else None
        sub_value = (sub.get("value") or "").strip() if sub else ""
        if sub and values_equivalent(spec_value, sub_value):
            exact_match_entries.append({
                "feature": spec_key,
                "spec_requirement": f"{spec_value} ({citation})" if citation else spec_value,
                "submitted_value": sub_value,
                "status": "Pass",
            })
        else:
            remaining_spec_requirements.append(req)

    return (exact_match_entries, remaining_spec_requirements)


def build_structured_audit_prompt(
    verified_requirements: list[dict[str, Any]],
    filtered_submittal_data: list[dict[str, Any]],
    exact_match_entries: Optional[list[dict[str, Any]]] = None,
    remaining_requirements: Optional[list[dict[str, Any]]] = None,
    spec_section: Optional[str] = None,
) -> str:
    """
    Build the user prompt from structured JSON only (no raw truncated text).
    verified_requirements: list of {key, value, citation, source_page}.
    filtered_submittal_data: list of {key, value, page_number, confidence}.
    exact_match_entries: pre-verified (unit-normalized) pairs to list as Pass.
    remaining_requirements: spec requirements still to evaluate (default: all if not pre-matched).
    """
    if exact_match_entries is None:
        exact_match_entries = []
    if remaining_requirements is None:
        remaining_requirements = verified_requirements

    parts = [
        "You are comparing a Project Specification (Source of Truth) to a Contractor Submittal (Evidence). ",
        "The following data is provided as structured JSON only.\n",
    ]
    if spec_section:
        parts.append(f"Focus on Specification Section: {spec_section}\n\n")

    parts.append("--- PRE-VERIFIED (unit-normalized exact match; treat as Pass) ---\n")
    parts.append(json.dumps(exact_match_entries, indent=2))
    parts.append("\n\n--- REMAINING SPEC REQUIREMENTS (evaluate these) ---\n")
    parts.append(json.dumps(remaining_requirements, indent=2))
    parts.append("\n\n--- FILTERED SUBMITTAL DATA ---\n")
    parts.append(json.dumps(filtered_submittal_data, indent=2))
    parts.append("\n\n" + CHECKLIST)
    parts.append(
        "\n\nOutput your evaluation as a single valid JSON object only (no markdown, no code fence). "
        "Include the pre-verified items in summary_table with status 'Pass'. "
        "Use the exact keys: summary_table, compliance_narrative, missing_information, "
        "critical_deviations, detailed_discrepancies, suggested_action."
    )
    return "".join(parts)


def _parse_json_from_response(text: str) -> dict[str, Any]:
    """Extract and parse JSON from model response; strip markdown code blocks if present."""
    raw = text.strip()
    # Remove optional markdown code block
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```\s*$", "", raw)
    # Extract outermost { ... } if there is leading/trailing text
    start = raw.find("{")
    if start > 0:
        raw = raw[start:]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        import json_repair
        return json_repair.loads(raw)  # type: ignore


def _validate_report(data: dict) -> dict[str, Any]:
    """Ensure report has required keys with safe defaults."""
    summary_table = data.get("summary_table")
    if not isinstance(summary_table, list):
        summary_table = []
    return {
        "summary_table": summary_table,
        "compliance_narrative": data.get("compliance_narrative") or "",
        "missing_information": data.get("missing_information") or [],
        "critical_deviations": data.get("critical_deviations") or [],
        "detailed_discrepancies": data.get("detailed_discrepancies") or [],
        "suggested_action": data.get("suggested_action") or "REVISE_AND_RESUBMIT",
    }


def run_audit(
    verified_requirements: list[dict[str, Any]],
    filtered_submittal_data: list[dict[str, Any]],
    *,
    submittal_name: str = "Submittal",
    spec_section: Optional[str] = None,
) -> dict[str, Any]:
    """
    Run the Technical Submittal Auditor using structured JSON only (no raw text).

    verified_requirements: list of {key, value, citation, source_page} (e.g. from SpecRequirement).
    filtered_submittal_data: list of {key, value, page_number, confidence} (e.g. from SubmittalDataPoint).
    Pre-audit unit normalization marks exact matches before the LLM; only remaining items are evaluated.
    Returns the report dict with summary_table, compliance_narrative, etc.
    """
    exact_match_entries, remaining_requirements = compute_prematched_pairs(
        verified_requirements, filtered_submittal_data
    )
    user_prompt = build_structured_audit_prompt(
        verified_requirements,
        filtered_submittal_data,
        exact_match_entries=exact_match_entries,
        remaining_requirements=remaining_requirements,
        spec_section=spec_section,
    )

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or not api_key.strip():
        raise ValueError("GEMINI_API_KEY is not set. Set it in the environment to run submittal evaluation.")

    import google.generativeai as genai

    genai.configure(api_key=api_key)
    model_name = os.environ.get("GEMINI_AUDIT_MODEL", "gemini-2.5-flash")
    model = genai.GenerativeModel(
        model_name,
        generation_config=genai.types.GenerationConfig(
            temperature=0.1,
            max_output_tokens=16384,
        ),
    )

    response = model.generate_content(
        [SYSTEM_PROMPT, user_prompt],
    )

    if not response or not response.text:
        raise RuntimeError("LLM returned no text.")

    try:
        data = _parse_json_from_response(response.text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"LLM response was not valid JSON: {e}") from e

    report = _validate_report(data)
    # Prepend pre-verified exact matches to summary_table so report is complete
    if exact_match_entries and isinstance(report.get("summary_table"), list):
        report["summary_table"] = exact_match_entries + list(report["summary_table"])
    return report
