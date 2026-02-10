"""
Ingestion Orchestrator: routes uploads by doc_type, runs validation, and returns a Pre-Flight Report.
"""

from typing import Literal, Optional

from app.ingestion.models import (
    PreFlightReport,
    RFIMetadata,
    SpecMetadata,
    SubmittalMetadata,
)
from app.ingestion.parsers import (
    extract_rfi_metadata,
    extract_spec_metadata,
    extract_submittal_metadata,
)


def _normalize_section(s: str) -> str:
    """Normalize for comparison."""
    if not s or not isinstance(s, str):
        return ""
    return " ".join(s.upper().split()).strip()


def process_upload(
    file_bytes: bytes,
    doc_type: Literal["SPEC", "SUBMITTAL", "RFI"],
    *,
    user_spec_section: Optional[str] = None,
) -> PreFlightReport:
    """
    Route an uploaded file by doc_type, extract metadata, validate (submittal only),
    and return a Pre-Flight Report for frontend auto-fill and risk display.

    Args:
        file_bytes: Raw PDF (or document) bytes.
        doc_type: One of 'SPEC', 'SUBMITTAL', 'RFI'.
        user_spec_section: For SUBMITTAL only: the spec section the user selected in the UI.
            If provided, we validate that the PDF's extracted spec section matches and add a
            risk if it does not.

    Returns:
        PreFlightReport with metadata, processing_confidence_score (0.0–1.0), and identified_risks.
    """
    if doc_type == "SPEC":
        metadata, confidence, risks = extract_spec_metadata(file_bytes)
    elif doc_type == "SUBMITTAL":
        metadata, confidence, risks = extract_submittal_metadata(file_bytes)
        # Validation: compare PDF spec section to user-selected spec section
        if user_spec_section is not None and isinstance(metadata, SubmittalMetadata):
            user_norm = _normalize_section(user_spec_section)
            pdf_norm = _normalize_section(metadata.spec_section)
            if user_norm and pdf_norm and user_norm != pdf_norm:
                risks.append(
                    f"Spec section mismatch: document shows '{metadata.spec_section}' "
                    f"but selected section is '{user_spec_section}'"
                )
    elif doc_type == "RFI":
        metadata, confidence, risks = extract_rfi_metadata(file_bytes)
    else:
        raise ValueError(f"Unsupported doc_type: {doc_type}")

    return PreFlightReport(
        metadata=metadata,
        processing_confidence_score=confidence,
        identified_risks=risks,
    )
