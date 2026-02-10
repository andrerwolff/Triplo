"""
Orchestrator: runs the Spec vs. Submittal audit pipeline in sequence.

Assembly line order:
  1. extraction_agent   (spec + submittal PDFs -> spec_requirements, submittal_data, TOC, action items)
  2. precedence_agent  (Rule of Precedence: visual silences conflicting text -> submittal_data_filtered)
  3. triage_agent      (action submittal vs TOC -> triage_status, triage_missing)
  4. compliance_gate_agent (Division 01 administrative checks)
  5. audit_agent       (spec vs submittal_data_filtered with unit norm -> variances)
  6. synthesis_agent   (variances + triage + gate override -> review_stamp, synthesis_notes)
"""

from typing import Optional

from app.pipeline.state import SubmittalState
from app.pipeline.agents import (
    triage_agent,
    extraction_agent,
    precedence_agent,
    audit_agent,
    synthesis_agent,
    compliance_gate_agent,
)


def run_pipeline(
    spec_pdf_bytes: bytes,
    submittal_pdf_bytes: bytes,
    *,
    initial_state: Optional[SubmittalState] = None,
    visual_result: Optional[dict] = None,
) -> SubmittalState:
    """
    Run the full audit pipeline in sequence.

    Args:
        spec_pdf_bytes: Raw bytes of the specification PDF.
        submittal_pdf_bytes: Raw bytes of the contractor submittal PDF.
        initial_state: Optional starting state (e.g. pre-filled metadata). Defaults to empty SubmittalState.
        visual_result: Optional output of run_visual_extraction; when provided, precedence uses it
            and does not re-run visual extraction. When None, precedence_agent runs visual extraction
            internally.

    Returns:
        SubmittalState with spec_requirements, submittal_data, submittal_data_filtered,
        triage_status, variances, review_stamp, synthesis_notes, and human_review_items populated.
    """
    state = initial_state if initial_state is not None else SubmittalState()

    # Step 1: Extraction (multimodal; populates spec, submittal, TOC, action requirements)
    state = extraction_agent(state, spec_pdf_bytes, submittal_pdf_bytes)

    # Step 2: Rule of Precedence (visual silences conflicting text; populates submittal_data_filtered)
    state = precedence_agent(state, submittal_pdf_bytes, visual_result=visual_result)

    # Step 3: Triage (required docs vs TOC)
    state = triage_agent(state)

    # Step 4: Division 01 compliance gate (administrative checks)
    state = compliance_gate_agent(state)

    # Step 5: Audit (spec vs submittal with unit normalization)
    state = audit_agent(state)

    # Step 6: Synthesis (review stamp + notes; respects suggested_action_override)
    state = synthesis_agent(state)

    return state
