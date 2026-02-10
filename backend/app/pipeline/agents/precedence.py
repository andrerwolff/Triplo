"""
Precedence agent: apply Rule of Precedence to filter catalog noise and populate
submittal_data_filtered. Visual extraction is only used when explicitly passed.
"""

from app.pipeline.state import SubmittalState
from app.pipeline.precedence import apply_precedence


def precedence_agent(
    state: SubmittalState,
    submittal_pdf_bytes: bytes,
    visual_result: dict | None = None,
) -> SubmittalState:
    """
    Apply precedence to state.submittal_data and set state.submittal_data_filtered.

    When visual_result is provided (e.g. from a prior POST /visual-extraction call),
    it is stored and used to silence conflicting text on highlighted pages.
    When None, no visual extraction is run (avoids slow CV/LLM work on every audit);
    precedence still runs and enriches all points as MEDIUM_TEXT with requires_confirmation=True.
    """
    state.visual_selection_result = visual_result
    state.submittal_data_filtered = apply_precedence(
        state.submittal_data,
        state.visual_selection_result,
    )
    return state
