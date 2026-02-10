"""
Ingestion Orchestrator: initial upload handling for Specs, Submittals, and RFIs.

Provides process_upload(file, doc_type) routing, validation, and Pre-Flight Report
output for frontend auto-fill and risk surfacing.
"""

from app.ingestion.models import (
    DocumentMetadata,
    SpecMetadata,
    SubmittalMetadata,
    RFIMetadata,
    PreFlightReport,
)
from app.ingestion.orchestrator import process_upload

__all__ = [
    "process_upload",
    "DocumentMetadata",
    "SpecMetadata",
    "SubmittalMetadata",
    "RFIMetadata",
    "PreFlightReport",
]
