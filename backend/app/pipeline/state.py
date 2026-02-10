"""
State definition for the Spec vs. Submittal audit pipeline.

SubmittalState is the single source of truth carried through the assembly line.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TriageStatus(str, Enum):
    """Whether required documents are present per spec."""

    COMPLETE = "Complete"
    INCOMPLETE = "Incomplete"


class ReviewStamp(str, Enum):
    """Final recommendation for the submittal."""

    APPROVED = "Approved"
    APPROVED_AS_NOTED = "Approved as Noted"
    REVISE_AND_RESUBMIT = "Revise and Resubmit"
    REJECTED = "Rejected"


# --- Spec-side structures ---


class SpecRequirement(BaseModel):
    """A single technical requirement extracted from the spec PDF."""

    key: str = Field(..., description="E.g. Material, Finish, Fire Rating")
    value: str = Field(..., description="Required value or description")
    citation: str = Field(default="", description="Spec section/paragraph reference")
    source_page: Optional[int] = Field(default=None, description="Page number in spec PDF")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Extraction confidence")


# --- Submittal-side structures (with page refs and confidence) ---


class SubmittalDataPoint(BaseModel):
    """A single data point extracted from the contractor submittal PDF."""

    key: str = Field(..., description="E.g. Material, Finish, Fire Rating")
    value: str = Field(..., description="Submitted value")
    page_number: int = Field(..., ge=1, description="Page number where value was found")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence; <0.8 flags HITL")
    human_review_required: bool = Field(
        default=False,
        description="True when confidence < 0.8 (human-in-the-loop)",
    )


# --- Action Submittal / TOC ---


class ActionSubmittalItem(BaseModel):
    """One required submittal item from the spec (e.g. Shop Drawings, Product Data)."""

    name: str = Field(..., description="Document or item name")
    citation: str = Field(default="", description="Spec reference")


class SubmittalTOCEntry(BaseModel):
    """One entry in the submittal's Table of Contents."""

    title: str = Field(..., description="TOC title or section name")
    page: Optional[int] = Field(default=None, ge=1, description="Page number if stated")


# --- Variance (audit output) ---


class Variance(BaseModel):
    """A discrepancy between spec and submittal."""

    spec_key: str = Field(..., description="Requirement key from spec")
    spec_value: str = Field(..., description="Required value")
    submittal_value: str = Field(..., description="Submitted value (or 'Not Provided')")
    severity: str = Field(default="Minor", description="Minor | Major | Critical")
    explanation: str = Field(default="", description="Brief explanation of the variance")
    spec_citation: str = Field(default="", description="Spec section/paragraph")


# --- Pipeline state ---


class SubmittalState(BaseModel):
    """
    State object for the multi-step audit pipeline.

    Updated in sequence by: triage_agent -> extraction_agent -> audit_agent -> synthesis_agent.
    """

    # Spec-side
    spec_requirements: list[SpecRequirement] = Field(
        default_factory=list,
        description="Technical specs extracted from the spec PDF",
    )
    action_submittal_requirements: list[ActionSubmittalItem] = Field(
        default_factory=list,
        description="Required Action Submittal items from spec (for triage)",
    )

    # Submittal-side
    submittal_data: list[SubmittalDataPoint] = Field(
        default_factory=list,
        description="Extracted data points from contractor PDF (with page numbers)",
    )
    submittal_toc: list[SubmittalTOCEntry] = Field(
        default_factory=list,
        description="Table of Contents extracted from submittal (for triage)",
    )

    # Triage
    triage_status: TriageStatus = Field(
        default=TriageStatus.INCOMPLETE,
        description="Complete if all required documents present; else Incomplete",
    )
    triage_missing: list[str] = Field(
        default_factory=list,
        description="List of required items not found in submittal TOC",
    )

    # Audit
    variances: list[Variance] = Field(
        default_factory=list,
        description="Discrepancies between spec and submittal",
    )

    # Synthesis
    review_stamp: Optional[ReviewStamp] = Field(
        default=None,
        description="Final recommendation: Approved, Approved as Noted, Revise and Resubmit",
    )
    synthesis_notes: str = Field(
        default="",
        description="Consolidated narrative for the review stamp",
    )

    # Metadata (for HITL and debugging)
    human_review_items: list[str] = Field(
        default_factory=list,
        description="Extraction keys flagged for human-in-the-loop (confidence < 0.8)",
    )

    # Visual extraction (optional): when provided, filter_data_points is applied to submittal_data
    visual_selection_result: Optional[dict] = Field(
        default=None,
        description="Output of run_visual_extraction (final_selection, etc.) when available",
    )

    # Division 01 compliance gate: if failed, synthesis forces REVISE_AND_RESUBMIT
    division01_passed: bool = Field(
        default=True,
        description="True if administrative checks (Cover sheet, LEED, Buy American) passed",
    )
    suggested_action_override: Optional[str] = Field(
        default=None,
        description="When set to REVISE_AND_RESUBMIT, synthesis uses it before technical variances",
    )

    class Config:
        use_enum_values = True
