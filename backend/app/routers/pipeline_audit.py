"""
API router for the Spec vs. Submittal pipeline audit.

POST /api/pipeline/audit: upload spec PDF + submittal PDF, run full pipeline, return state.
"""

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.pipeline import run_pipeline

router = APIRouter()


@router.post("/audit", response_model=dict)
async def run_pipeline_audit(
    spec_pdf: UploadFile = File(..., description="Specification PDF"),
    submittal_pdf: UploadFile = File(..., description="Contractor submittal PDF"),
):
    """
    Run the multi-step Spec vs. Submittal audit pipeline.

    Upload the spec PDF and the submittal PDF. Returns the full pipeline state:
    spec_requirements, submittal_data, triage_status, variances, review_stamp,
    synthesis_notes, and human_review_items (confidence < 0.8).
    """
    if not spec_pdf.filename or not spec_pdf.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Spec file must be a PDF")
    if not submittal_pdf.filename or not submittal_pdf.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Submittal file must be a PDF")

    spec_bytes = await spec_pdf.read()
    sub_bytes = await submittal_pdf.read()
    if not spec_bytes:
        raise HTTPException(status_code=400, detail="Spec PDF is empty")
    if not sub_bytes:
        raise HTTPException(status_code=400, detail="Submittal PDF is empty")

    try:
        state = run_pipeline(spec_bytes, sub_bytes)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    # Return state as JSON-serializable dict (Pydantic model_dump with enums)
    return state.model_dump(mode="json")


@router.post("/visual-extraction", response_model=dict)
async def run_visual_extraction_endpoint(
    pdf: UploadFile = File(..., description="PDF with highlighted pages (e.g. contractor submittal)"),
):
    """
    Multi-page visual extraction: scout for highlighted/annotated pages, zoom on each
    highlight, and extract the highlighted model + technical specs via multimodal LLM.
    Unmarked pages that look like Performance Curve or Wiring Diagram are flagged for manual review.
    """
    # Lazy-import so OpenCV/NumPy/PIL are not loaded at app startup (avoids hang on first page load)
    from app.pipeline.visual_extraction import run_visual_extraction

    if not pdf.filename or not pdf.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    pdf_bytes = await pdf.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="PDF is empty")
    try:
        result = run_visual_extraction(pdf_bytes)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return result
