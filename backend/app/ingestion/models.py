"""
Pydantic models for Ingestion Orchestrator.

DocumentMetadata is a tagged union so the frontend can show type-specific
auto-filled fields. PreFlightReport wraps metadata + confidence + risks.
"""

from typing import Literal, Optional, Union

from pydantic import BaseModel, Field


# --- Spec (from Part 1) ---


class SpecMetadata(BaseModel):
    """Auto-filled fields from a Specification PDF (Part 1)."""

    doc_type: Literal["SPEC"] = "SPEC"
    section_id: str = Field(default="", description="CSI or spec section number (e.g. 03 30 00)")
    title: str = Field(default="", description="Section title")
    required_submittal_types: list[str] = Field(
        default_factory=list,
        description="List of required submittal types from Part 1",
    )


# --- Submittal (cover sheet + coordinate-aware extraction) ---


class SubmittalMetadata(BaseModel):
    """Auto-filled fields from a Submittal PDF (cover sheet)."""

    doc_type: Literal["SUBMITTAL"] = "SUBMITTAL"
    submittal_number: str = Field(default="", description="Submittal # from cover sheet")
    revision: str = Field(default="", description="Revision (e.g. 0, 1, 2)")
    spec_section: str = Field(
        default="",
        description="Spec section referenced on cover sheet (for validation vs user selection)",
    )


# --- RFI ---


class RFIMetadata(BaseModel):
    """Auto-filled fields from an RFI document."""

    doc_type: Literal["RFI"] = "RFI"
    question: str = Field(default="", description="Extracted RFI question")
    suggested_solution: str = Field(default="", description="Suggested solution if present")
    mentions_cost: bool = Field(default=False, description="True if 'cost' or cost-related terms appear")
    mentions_schedule: bool = Field(default=False, description="True if 'schedule' or schedule-related terms appear")


# --- Union for API response (discriminated by doc_type) ---


DocumentMetadata = Union[SpecMetadata, SubmittalMetadata, RFIMetadata]


# --- Pre-Flight Report (API output) ---


class PreFlightReport(BaseModel):
    """Report returned after process_upload for frontend confirmation and risk display."""

    metadata: Union[SpecMetadata, SubmittalMetadata, RFIMetadata] = Field(
        ...,
        description="Auto-filled fields for the uploaded document type",
    )
    processing_confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall confidence in extraction (0.0–1.0); <0.8 suggests human review",
    )
    identified_risks: list[str] = Field(
        default_factory=list,
        description="Risks to surface (e.g. missing signature, spec section mismatch)",
    )
