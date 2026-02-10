import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Body

from app import storage, extractors, audit, document_summary
from app.models import Project, ReferenceDoc, Submittal, RFI

router = APIRouter()


def _project_to_response(p: dict) -> dict:
    """Ensure all nested items have ids and consistent shape."""
    out = dict(p)
    for key, default_name in [
        ("reference_docs", "Document"),
        ("open_submittals", "Submittal"),
        ("closed_submittals", "Submittal"),
        ("rfis", "RFI"),
    ]:
        items = out.get(key) or []
        for i, item in enumerate(items):
            if isinstance(item, dict) and not item.get("id"):
                items[i] = {**item, "id": str(uuid.uuid4())}
        out[key] = items
    return out


@router.options("")
def options_projects():
    """CORS preflight for /api/projects."""
    return {"ok": True}


@router.get("")
def list_projects():
    projects = storage.load_projects()
    return {"projects": [_project_to_response(p) for p in projects]}


@router.post("")
def create_project(name: str = Form(...)):
    projects = storage.load_projects()
    new_id = str(uuid.uuid4())
    new_project = {
        "id": new_id,
        "name": name,
        "open_submittals": [],
        "closed_submittals": [],
        "reference_docs": [],
        "rfis": [],
    }
    projects.append(new_project)
    storage.save_projects(projects)
    return _project_to_response(new_project)


@router.get("/{project_id}")
def get_project(project_id: str):
    p = storage.get_project_by_id(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return _project_to_response(p)


@router.patch("/{project_id}")
def update_project(project_id: str, body: Optional[dict] = Body(None)):
    p = storage.get_project_by_id(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    if body and "name" in body and body["name"] is not None:
        storage.update_project(project_id, {"name": body["name"]})
    return _project_to_response(storage.get_project_by_id(project_id))


@router.delete("/{project_id}")
def delete_project(project_id: str):
    projects = storage.load_projects()
    filtered = [p for p in projects if p.get("id") != project_id]
    if len(filtered) == len(projects):
        raise HTTPException(status_code=404, detail="Project not found")
    storage.save_projects(filtered)
    return {"ok": True}


# Reference documents
@router.post("/{project_id}/reference-docs")
async def add_reference_doc(
    project_id: str,
    file: UploadFile = File(...),
    csi_division: str = Form(""),
):
    p = storage.get_project_by_id(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    text = extractors.extract_text_from_file(file.filename or "", content)
    if text is None:
        raise HTTPException(status_code=400, detail="Could not extract text from file")
    summary = document_summary.summarize_document(file.filename or "", text)
    refs = p.get("reference_docs") or []
    refs.append({
        "id": str(uuid.uuid4()),
        "name": file.filename or "Document",
        "csi_division": csi_division or None,
        "extracted_text": text,
        "summary": summary or "Document uploaded. Enable GEMINI_API_KEY for an AI-generated description.",
    })
    storage.update_project(project_id, {"reference_docs": refs})
    return _project_to_response(storage.get_project_by_id(project_id))


# Submittals
@router.post("/{project_id}/submittals")
async def add_submittal(
    project_id: str,
    file: UploadFile = File(...),
    csi_division: str = Form(""),
):
    p = storage.get_project_by_id(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    text = extractors.extract_text_from_file(file.filename or "", content)
    if text is None:
        raise HTTPException(status_code=400, detail="Could not extract text from file")
    summary = document_summary.summarize_document(file.filename or "", text)
    open_subs = p.get("open_submittals") or []
    open_subs.append({
        "id": str(uuid.uuid4()),
        "name": file.filename or "Submittal",
        "csi_division": csi_division or None,
        "extracted_text": text,
        "summary": summary or "Document uploaded. Enable GEMINI_API_KEY for an AI-generated description.",
    })
    storage.update_project(project_id, {"open_submittals": open_subs})
    return _project_to_response(storage.get_project_by_id(project_id))


@router.options("/{project_id}/submittals/{submittal_id}/evaluate")
def options_evaluate(project_id: str, submittal_id: str):
    """CORS preflight for evaluate."""
    return {"ok": True}


@router.post("/{project_id}/submittals/{submittal_id}/evaluate")
def evaluate_submittal(
    project_id: str,
    submittal_id: str,
    body: Optional[dict] = Body(None),
):
    p = storage.get_project_by_id(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    open_subs = p.get("open_submittals") or []
    closed_subs = p.get("closed_submittals") or []
    sub = None
    in_open = True
    for s in open_subs:
        if s.get("id") == submittal_id:
            sub = s
            break
    if not sub:
        for s in closed_subs:
            if s.get("id") == submittal_id:
                sub = s
                in_open = False
                break
    if not sub:
        raise HTTPException(status_code=404, detail="Submittal not found")

    ref_docs = p.get("reference_docs") or []
    ref_doc_ids = (body or {}).get("reference_doc_ids")
    if ref_doc_ids is not None:
        ref_docs = [r for r in ref_docs if r.get("id") in ref_doc_ids]
    if not ref_docs:
        raise HTTPException(
            status_code=400,
            detail="No reference documents to evaluate against. Add reference docs (specs) to the project first.",
        )

    spec_blocks = [(r.get("name") or "Document", (r.get("extracted_text") or "")) for r in ref_docs]
    submittal_name = sub.get("name") or "Submittal"
    submittal_text = sub.get("extracted_text") or ""
    spec_section = (body or {}).get("spec_section") if body else None

    try:
        report = audit.run_audit(spec_blocks, submittal_name, submittal_text, spec_section)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    evaluated_at = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    sub_copy = dict(sub)
    sub_copy["evaluation_report"] = report
    sub_copy["evaluated_at"] = evaluated_at

    if in_open:
        open_subs = [s if s.get("id") != submittal_id else sub_copy for s in open_subs]
        storage.update_project(project_id, {"open_submittals": open_subs})
    else:
        closed_subs = [s if s.get("id") != submittal_id else sub_copy for s in closed_subs]
        storage.update_project(project_id, {"closed_submittals": closed_subs})

    updated = storage.get_project_by_id(project_id)
    return {"report": report, "evaluated_at": evaluated_at, "project": _project_to_response(updated)}


@router.post("/{project_id}/submittals/{submittal_id}/complete")
def complete_submittal(project_id: str, submittal_id: str):
    p = storage.get_project_by_id(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    open_subs = p.get("open_submittals") or []
    closed_subs = p.get("closed_submittals") or []
    found = None
    for sub in open_subs:
        if sub.get("id") == submittal_id:
            found = sub
            break
    if not found:
        raise HTTPException(status_code=404, detail="Submittal not found")
    open_subs = [s for s in open_subs if s.get("id") != submittal_id]
    closed_subs.append(found)
    storage.update_project(project_id, {"open_submittals": open_subs, "closed_submittals": closed_subs})
    return _project_to_response(storage.get_project_by_id(project_id))


# RFIs
@router.post("/{project_id}/rfis")
def add_rfi(
    project_id: str,
    title: str = Form(...),
    description: str = Form(""),
    status: str = Form("Open"),
):
    p = storage.get_project_by_id(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    rfis = p.get("rfis") or []
    rfis.append({
        "id": str(uuid.uuid4()),
        "title": title or "Untitled",
        "description": description,
        "status": status,
        "date": datetime.now().strftime("%Y-%m-%d"),
    })
    storage.update_project(project_id, {"rfis": rfis})
    return _project_to_response(storage.get_project_by_id(project_id))
