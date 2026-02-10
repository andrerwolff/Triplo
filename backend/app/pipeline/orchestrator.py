"""
Orchestrator: runs the Spec vs. Submittal audit pipeline in sequence.

Assembly line order:
  1. extraction_agent  (spec + submittal PDFs -> spec_requirements, submittal_data, TOC, action items)
  2. filter_data_points (when visual_extraction_result provided -> reduces catalog noise)
  3. triage_agent     (action submittal vs TOC -> triage_status, triage_missing)
  4. compliance_gate_agent (Division 01 administrative checks)
  5. audit_agent      (spec vs submittal with unit norm -> variances)
  6. synthesis_agent  (variances + triage + gate override -> review_stamp, synthesis_notes)
"""

from typing import Optional

from app.pipeline.state import SubmittalState
from app.pipeline.agents import (
    triage_agent,
    extraction_agent,
    audit_agent,
    synthesis_agent,
    compliance_gate_agent,
)
from app.pipeline.agents.extraction import filter_data_points


def run_pipeline(
    spec_pdf_bytes: bytes,
    submittal_pdf_bytes: bytes,
    *,
    initial_state: Optional[SubmittalState] = None,
    visual_extraction_result: Optional[dict] = None,
) -> SubmittalState:
    """
    Run the full audit pipeline in sequence.

    Args:
        spec_pdf_bytes: Raw bytes of the specification PDF.
        submittal_pdf_bytes: Raw bytes of the contractor submittal PDF.
        initial_state: Optional starting state (e.g. pre-filled metadata). Defaults to empty SubmittalState.
        visual_extraction_result: Optional output of run_visual_extraction; when provided and
            final_selection has at least one non-empty highlighted_model_or_value, submittal_data
            is filtered to reduce catalog noise.

    Returns:
        SubmittalState with spec_requirements, submittal_data, triage_status,
        variances, review_stamp, synthesis_notes, and human_review_items populated.
    """
    state = initial_state if initial_state is not None else SubmittalState()
    if visual_extraction_result is not None:
        state.visual_selection_result = visual_extraction_result

    # Step 1: Extraction (multimodal; populates spec, submittal, TOC, action requirements)
    state = extraction_agent(state, spec_pdf_bytes, submittal_pdf_bytes)

    # Step 2: Selection filter (when visual extraction result has master keys)
    if state.visual_selection_result:
        final_selection = state.visual_selection_result.get("final_selection") or {}
        has_master = any(
            (e or {}).get("highlighted_model_or_value", "").strip()
            for e in final_selection.values()
        )
        if has_master:
            state.submittal_data = filter_data_points(
                state.submittal_data, final_selection
            )

    # Step 3: Triage (required docs vs TOC)
    state = triage_agent(state)

    # Step 4: Division 01 compliance gate (administrative checks)
    state = compliance_gate_agent(state)

    # Step 5: Audit (spec vs submittal with unit normalization)
    state = audit_agent(state)

    # Step 6: Synthesis (review stamp + notes; respects suggested_action_override)
    state = synthesis_agent(state)

    return state
