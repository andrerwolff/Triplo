"""
API router for the Ingestion Orchestrator.

POST /api/ingestion/process: upload a file with doc_type (SPEC | SUBMITTAL | RFI),
optional user_spec_section for submittal validation. Returns Pre-Flight Report JSON.
"""

from typing import Literal, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.ingestion.models import PreFlightReport
from app.ingestion.orchestrator import process_upload

router = APIRouter()


@router.post("/process", response_model=PreFlightReport)
async def process_upload_endpoint(
    file: UploadFile = File(..., description="PDF document (Spec, Submittal, or RFI)"),
    doc_type: Literal["SPEC", "SUBMITTAL", "RFI"] = Form(
        ...,
        description="Type of document for routing extraction",
    ),
    user_spec_section: Optional[str] = Form(
        None,
        description="For SUBMITTAL: spec section selected in UI; used to validate against PDF",
    ),
) -> PreFlightReport:
    """
    Process an uploaded document and return a Pre-Flight Report.

    - **SPEC**: Extracts Section ID, Title, and required Submittal types from Part 1.
    - **SUBMITTAL**: Extracts Cover Sheet (Submittal #, Rev, Spec Section) with coordinate-aware
      parsing; validates against `user_spec_section` if provided.
    - **RFI**: Extracts Question, Suggested Solution, and flags cost/schedule mentions.

    Response includes metadata (auto-filled fields), processing_confidence_score (0.0–1.0),
    and identified_risks (e.g. missing signature, spec section mismatch).
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Upload must be a PDF file",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="File is empty")

    try:
        report = process_upload(
            file_bytes,
            doc_type,
            user_spec_section=user_spec_section,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return report
