"""
Audit agent: compare Spec JSON vs Submittal JSON.

Uses unit normalization (e.g. '2 hours' == '120 mins') when comparing values.
Produces a list of variances (discrepancies).
"""

from app.pipeline.state import SubmittalState, Variance, SpecRequirement, SubmittalDataPoint
from app.pipeline.units import values_equivalent


def _find_submittal_value(state: SubmittalState, spec_key: str) -> tuple[str, bool]:
    """Return (submittal_value, found). found=False means 'Not Provided'."""
    key_lower = spec_key.lower().strip()
    for dp in state.submittal_data:
        if dp.key.lower().strip() == key_lower:
            return (dp.value.strip(), True)
    return ("Not Provided", False)


def audit_agent(state: SubmittalState) -> SubmittalState:
    """
    Compare each spec requirement to the corresponding submittal data point.

    - Uses unit normalization (time, length) for equivalence.
    - Records variances where values differ or are missing.
    """
    variances: list[Variance] = []

    for spec in state.spec_requirements:
        sub_val, found = _find_submittal_value(state, spec.key)
        if not found:
            variances.append(
                Variance(
                    spec_key=spec.key,
                    spec_value=spec.value,
                    submittal_value="Not Provided",
                    severity="Major",
                    explanation=f"Required '{spec.key}' not found in submittal.",
                    spec_citation=spec.citation,
                )
            )
            continue
        if values_equivalent(spec.value, sub_val):
            continue
        # Determine severity heuristics
        severity = "Minor"
        if not found or sub_val == "Not Provided":
            severity = "Major"
        elif "fire" in spec.key.lower() or "rating" in spec.key.lower() or "test" in spec.key.lower():
            severity = "Critical"
        variances.append(
            Variance(
                spec_key=spec.key,
                spec_value=spec.value,
                submittal_value=sub_val,
                severity=severity,
                explanation=f"Spec requires '{spec.value}' but submittal provides '{sub_val}'.",
                spec_citation=spec.citation,
            )
        )

    state.variances = variances
    return state
