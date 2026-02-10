"""
Strict JSON schemas for LLM extraction outputs.

Forces all extractions into a fixed structure to prevent hallucinated formatting.
Every extracted value includes a confidence score; < 0.8 flags human-in-the-loop.
"""

from typing import List

from pydantic import BaseModel, Field


# --- Spec extraction (with page numbers) ---


class SpecExtractionItem(BaseModel):
    """One requirement from the spec; used for strict LLM output."""

    key: str = Field(..., description="Attribute name: Material, Finish, Fire Rating, etc.")
    value: str = Field(..., description="Required value from spec")
    citation: str = Field(default="", description="Spec section/paragraph")
    page_number: int = Field(..., ge=1, description="Page number in spec PDF where found")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score; <0.8 = HITL")


class SpecExtractionSchema(BaseModel):
    """Strict schema for spec extraction agent output."""

    requirements: list[SpecExtractionItem] = Field(
        default_factory=list,
        description="All extracted spec requirements with page numbers",
    )


# --- Submittal extraction (with page numbers) ---


class SubmittalExtractionItem(BaseModel):
    """One data point from the submittal; used for strict LLM output."""

    key: str = Field(..., description="Attribute name: Material, Finish, Fire Rating, etc.")
    value: str = Field(..., description="Submitted value")
    page_number: int = Field(..., ge=1, description="Page number in submittal PDF where found")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score; <0.8 = HITL")


class SubmittalExtractionSchema(BaseModel):
    """Strict schema for submittal extraction agent output."""

    data_points: list[SubmittalExtractionItem] = Field(
        default_factory=list,
        description="All extracted submittal data with page numbers",
    )


# --- Action Submittal / TOC (for triage) ---


class ActionSubmittalExtraction(BaseModel):
    """Required Action Submittal items from spec."""

    items: list[dict[str, str]] = Field(
        default_factory=list,
        description="List of {name, citation} for each required submittal",
    )


class SubmittalTOCExtraction(BaseModel):
    """Table of Contents from submittal PDF."""

    entries: List[dict] = Field(
        default_factory=list,
        description="List of {title, page} for each TOC entry",
    )


# --- Variance (audit output) ---


class VarianceExtractionItem(BaseModel):
    """One variance for strict audit output."""

    spec_key: str = Field(..., description="Requirement key")
    spec_value: str = Field(..., description="Required value")
    submittal_value: str = Field(..., description="Submitted value or 'Not Provided'")
    severity: str = Field(default="Minor", description="Minor | Major | Critical")
    explanation: str = Field(default="", description="Brief explanation")
    spec_citation: str = Field(default="", description="Spec reference")


class AuditOutputSchema(BaseModel):
    """Strict schema for audit agent output."""

    variances: list[VarianceExtractionItem] = Field(
        default_factory=list,
        description="All discrepancies between spec and submittal",
    )


# --- Synthesis (review stamp) ---


class SynthesisOutputSchema(BaseModel):
    """Strict schema for synthesis agent output."""

    review_stamp: str = Field(
        ...,
        description="One of: Approved, Approved as Noted, Revise and Resubmit, Rejected",
    )
    notes: str = Field(default="", description="Consolidated narrative for the recommendation")
