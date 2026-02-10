"""
Compliance gate agent: Division 01 administrative checks before technical audit.

Checks for Cover sheet, LEED, Buy American (or equivalent). If any required
administrative item fails, sets suggested_action_override to REVISE_AND_RESUBMIT.
"""

from app.pipeline.state import SubmittalState


# Keywords that indicate presence of Division 01 administrative items
COVER_SHEET_KEYWORDS = ("cover", "submittal form", "transmittal", "title sheet")
LEED_KEYWORDS = ("leed", "leed®", "leed v", "leed 2009", "leed v4", "leed v5")
BUY_AMERICAN_KEYWORDS = ("buy american", "buy america", "baa", "domestic content")


def _normalize(s: str) -> str:
    return (s or "").lower().strip()


def _text_contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    t = _normalize(text)
    return any(kw in t for kw in keywords)


def _toc_has_cover_sheet(state: SubmittalState) -> bool:
    """True if TOC has an entry that looks like a cover/transmittal sheet."""
    for entry in state.submittal_toc:
        if _text_contains_any(entry.title, COVER_SHEET_KEYWORDS):
            return True
    return False


def _spec_requires_leed_or_buy_american(state: SubmittalState) -> tuple[bool, bool]:
    """Check if spec mentions LEED or Buy American (so we require them in submittal)."""
    requires_leed = False
    requires_buy_american = False
    for req in state.spec_requirements:
        combined = _normalize(req.key) + " " + _normalize(req.value)
        if _text_contains_any(combined, LEED_KEYWORDS):
            requires_leed = True
        if _text_contains_any(combined, BUY_AMERICAN_KEYWORDS):
            requires_buy_american = True
    for item in state.action_submittal_requirements:
        combined = _normalize(item.name) + " " + _normalize(item.citation)
        if _text_contains_any(combined, LEED_KEYWORDS):
            requires_leed = True
        if _text_contains_any(combined, BUY_AMERICAN_KEYWORDS):
            requires_buy_american = True
    return requires_leed, requires_buy_american


def _submittal_has_leed(state: SubmittalState) -> bool:
    """True if submittal TOC or data points mention LEED."""
    for entry in state.submittal_toc:
        if _text_contains_any(entry.title, LEED_KEYWORDS):
            return True
    for dp in state.submittal_data:
        if _text_contains_any(dp.key + " " + dp.value, LEED_KEYWORDS):
            return True
    return False


def _submittal_has_buy_american(state: SubmittalState) -> bool:
    """True if submittal TOC or data points mention Buy American."""
    for entry in state.submittal_toc:
        if _text_contains_any(entry.title, BUY_AMERICAN_KEYWORDS):
            return True
    for dp in state.submittal_data:
        if _text_contains_any(dp.key + " " + dp.value, BUY_AMERICAN_KEYWORDS):
            return True
    return False


def compliance_gate_agent(state: SubmittalState) -> SubmittalState:
    """
    Run Division 01 administrative checks.

    - Cover sheet: submittal TOC should have a cover/transmittal-type entry.
    - LEED / Buy American: if spec requires them, submittal must provide evidence.

    On any failure: division01_passed = False, suggested_action_override = "REVISE_AND_RESUBMIT".
    """
    state.division01_passed = True
    state.suggested_action_override = None

    failures: list[str] = []

    if not _toc_has_cover_sheet(state):
        failures.append("Cover sheet / transmittal not clearly identified in submittal TOC.")

    requires_leed, requires_buy_american = _spec_requires_leed_or_buy_american(state)
    if requires_leed and not _submittal_has_leed(state):
        failures.append("Spec references LEED requirements; submittal does not show LEED compliance.")
    if requires_buy_american and not _submittal_has_buy_american(state):
        failures.append("Spec references Buy American; submittal does not show Buy American compliance.")

    if failures:
        state.division01_passed = False
        state.suggested_action_override = "REVISE_AND_RESUBMIT"

    return state
