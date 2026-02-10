"""
Triage agent: compare Action Submittal requirements (from spec) vs Submittal Table of Contents.

Sets triage_status (Complete/Incomplete) and triage_missing list.
"""

from app.pipeline.state import (
    ActionSubmittalItem,
    SubmittalState,
    SubmittalTOCEntry,
    TriageStatus,
)


def _normalize_for_match(s: str) -> str:
    """Lowercase, collapse whitespace, remove common punctuation for fuzzy match."""
    import re
    s = (s or "").lower().strip()
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s


def _toc_covers_requirement(requirement: ActionSubmittalItem, toc_entries: list[SubmittalTOCEntry]) -> bool:
    """Return True if any TOC entry reasonably matches the required item name."""
    req_norm = _normalize_for_match(requirement.name)
    if not req_norm:
        return False
    for entry in toc_entries:
        title_norm = _normalize_for_match(entry.title)
        if not title_norm:
            continue
        # Requirement substring in TOC title, or vice versa
        if req_norm in title_norm or title_norm in req_norm:
            return True
        # Word overlap: if most key words appear in title, consider it covered
        req_words = set(req_norm.split())
        title_words = set(title_norm.split())
        if req_words & title_words and len(req_words & title_words) >= min(2, len(req_words)):
            return True
    return False


def triage_agent(state: SubmittalState) -> SubmittalState:
    """
    Compare Action Submittal requirements in the Spec against the Submittal's Table of Contents.

    Updates:
    - triage_status: Complete if every required item has a matching TOC entry; else Incomplete
    - triage_missing: list of required item names not found in TOC
    """
    required = state.action_submittal_requirements
    toc = state.submittal_toc

    missing: list[str] = []
    for item in required:
        if not _toc_covers_requirement(item, toc):
            missing.append(item.name)

    state.triage_status = TriageStatus.COMPLETE if not missing else TriageStatus.INCOMPLETE
    state.triage_missing = missing
    return state
