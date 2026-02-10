"""
Spec vs. Submittal audit pipeline: multi-step agentic assembly line.

Components:
- state: SubmittalState and related Pydantic models
- schemas: Strict extraction schemas with confidence scores
- agents: triage, extraction, audit, synthesis
- orchestrator: Runs pipeline steps in sequence
"""

from app.pipeline.state import (
    SubmittalState,
    TriageStatus,
    ReviewStamp,
    SpecRequirement,
    SubmittalDataPoint,
    Variance,
)
from app.pipeline.orchestrator import run_pipeline

__all__ = [
    "SubmittalState",
    "TriageStatus",
    "ReviewStamp",
    "SpecRequirement",
    "SubmittalDataPoint",
    "Variance",
    "run_pipeline",
]
