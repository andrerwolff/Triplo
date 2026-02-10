"""JSON persistence for projects."""
import json
import os
import uuid
from typing import Any, List, Optional

from app.models import Project, ReferenceDoc, Submittal, RFI

DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "..", "triplo_data.json")


def _ensure_ids(projects: List[dict]) -> List[dict]:
    out = []
    for p in projects:
        p = dict(p)
        if not p.get("id"):
            p["id"] = str(uuid.uuid4())
        for key, default in [
            ("reference_docs", []),
            ("open_submittals", []),
            ("closed_submittals", []),
            ("rfis", []),
        ]:
            items = p.get(key) or []
            for i, item in enumerate(items):
                if isinstance(item, dict) and not item.get("id"):
                    items[i] = {**item, "id": str(uuid.uuid4())}
            p[key] = items
        out.append(p)
    return out


def load_projects(path: Optional[str] = None) -> List[dict]:
    path = path or DEFAULT_PATH
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        raw = data.get("projects", [])
        return _ensure_ids(raw)
    except (json.JSONDecodeError, OSError):
        return []


def save_projects(projects: List[dict], path: Optional[str] = None) -> None:
    path = path or DEFAULT_PATH
    data = {"projects": projects}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_project_by_id(project_id: str, path: Optional[str] = None) -> Optional[dict]:
    for p in load_projects(path):
        if p.get("id") == project_id:
            return p
    return None


def update_project(project_id: str, data: dict, path: Optional[str] = None) -> Optional[dict]:
    projects = load_projects(path)
    for i, p in enumerate(projects):
        if p.get("id") == project_id:
            projects[i] = {**p, **data, "id": project_id}
            save_projects(projects, path)
            return projects[i]
    return None
