"""
Synthesis agent: consolidate findings into a final Review Stamp recommendation.

Recommendation: Approved | Approved as Noted | Revise and Resubmit | Rejected.
"""

from app.pipeline.state import SubmittalState, TriageStatus, ReviewStamp


def synthesis_agent(state: SubmittalState) -> SubmittalState:
    """
    Consolidate triage status, variances, compliance gate, and human-review flags
    into a single Review Stamp and narrative.
    """
    if state.suggested_action_override == "REVISE_AND_RESUBMIT":
        state.review_stamp = ReviewStamp.REVISE_AND_RESUBMIT
        state.synthesis_notes = (
            "Division 01 administrative requirements not met (e.g. Cover sheet, LEED, Buy American). "
            "Revise and resubmit."
        )
        return state

    triage_incomplete = state.triage_status == TriageStatus.INCOMPLETE
    critical = [v for v in state.variances if v.severity == "Critical"]
    major = [v for v in state.variances if v.severity == "Major"]
    minor = [v for v in state.variances if v.severity == "Minor"]
    hitl = bool(state.human_review_items)

    if triage_incomplete or critical:
        stamp = ReviewStamp.REVISE_AND_RESUBMIT
        if critical and not triage_incomplete:
            notes = "Critical variances found; submittal does not meet spec. Revise and resubmit."
        elif triage_incomplete:
            notes = f"Required documents missing: {', '.join(state.triage_missing)}. Complete submittal and resubmit."
        else:
            notes = "Triage incomplete or critical issues; revise and resubmit."
    elif major:
        stamp = ReviewStamp.REVISE_AND_RESUBMIT
        notes = f"Major variances ({len(major)}). Address before approval."
    elif minor or hitl:
        stamp = ReviewStamp.APPROVED_AS_NOTED
        parts = []
        if minor:
            parts.append(f"Minor variances ({len(minor)}) noted.")
        if hitl:
            parts.append(f"Human review recommended for: {', '.join(state.human_review_items)}.")
        notes = " ".join(parts) if parts else "Approved with noted items."
    else:
        stamp = ReviewStamp.APPROVED
        notes = "Submittal meets specification requirements."

    state.review_stamp = stamp
    state.synthesis_notes = notes
    return state
