"""
Rule of Precedence engine: filter catalog noise by letting visual highlights
silence conflicting text-extracted data on the same page.

Consumes extracted_data_points (submittal_data) and optional visual_selection_result
(from run_visual_extraction). Outputs a filtered and enriched list of SubmittalDataPoint
with source_reliability and requires_confirmation set.
"""

from typing import Any

from app.pipeline.state import SubmittalDataPoint
from app.pipeline.units import values_equivalent


def _norm_key(key: str) -> str:
    """Normalize key for case-insensitive matching."""
    return (key or "").strip().lower()


def _norm_value(value: str) -> str:
    """Normalize value for display/storage (strip)."""
    return (value or "").strip()


def _technical_specs_to_dict(specs: Any) -> dict[str, str]:
    """
    Normalize technical_specs from LLM to a single dict key -> value.
    Handles dict or list of {key, value} or [{key, value}, ...].
    """
    out: dict[str, str] = {}
    if not specs:
        return out
    if isinstance(specs, dict):
        for k, v in specs.items():
            if k is not None and v is not None:
                out[_norm_key(str(k))] = _norm_value(str(v))
        return out
    if isinstance(specs, list):
        for item in specs:
            if isinstance(item, dict):
                k = item.get("key") or item.get("name")
                v = item.get("value")
                if k is not None and v is not None:
                    out[_norm_key(str(k))] = _norm_value(str(v))
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                out[_norm_key(str(item[0]))] = _norm_value(str(item[1]))
        return out
    return out


def _build_visual_by_page(visual_selection_result: dict[str, Any] | None) -> dict[int, dict[str, str]]:
    """
    Build a map page_number -> { norm_key -> value } from visual_selection_result.
    Skip entries that are skipped or have error. Include highlighted_model_or_value as "Model".
    """
    by_page: dict[int, dict[str, str]] = {}
    if not visual_selection_result:
        return by_page
    final_selection = visual_selection_result.get("final_selection") or {}
    for page_key, entry in final_selection.items():
        if not isinstance(entry, dict):
            continue
        if entry.get("skipped") or entry.get("error"):
            continue
        page_num = entry.get("page_number")
        if page_num is None:
            # Parse from page_5 -> 5
            try:
                page_num = int(str(page_key).replace("page_", "").strip())
            except (ValueError, TypeError):
                continue
        if page_num < 1:
            continue
        spec_dict = _technical_specs_to_dict(entry.get("technical_specs"))
        if entry.get("highlighted_model_or_value"):
            spec_dict[_norm_key("Model")] = _norm_value(str(entry["highlighted_model_or_value"]))
        by_page[page_num] = spec_dict
    return by_page


def _values_match(a: str, b: str) -> bool:
    """True if the two values are considered the same (unit-aware)."""
    return values_equivalent(a or "", b or "")


def apply_precedence(
    extracted_data_points: list[SubmittalDataPoint],
    visual_selection_result: dict[str, Any] | None,
) -> list[SubmittalDataPoint]:
    """
    Filter and enrich submittal data using the Rule of Precedence.

    - On pages with a visual selection: discard text points whose key matches
      the visual key but value differs; keep matching or non-visual keys;
      inject visual-only keys. Set source_reliability and requires_confirmation accordingly.
    - On pages with no visual: keep all points, set MEDIUM_TEXT and requires_confirmation=True.

    Returns the combined list (kept + added), ordered by page then key.
    """
    visual_by_page = _build_visual_by_page(visual_selection_result)

    # All pages that appear in either source
    pages: set[int] = set()
    for dp in extracted_data_points:
        pages.add(dp.page_number)
    for p in visual_by_page:
        pages.add(p)

    result: list[SubmittalDataPoint] = []

    for page_num in sorted(pages):
        page_visual = visual_by_page.get(page_num)
        points_on_page = [dp for dp in extracted_data_points if dp.page_number == page_num]

        if page_visual:
            # Page has visual selection
            kept_keys_on_page: set[str] = set()
            for dp in points_on_page:
                nk = _norm_key(dp.key)
                vis_val = page_visual.get(nk)
                if vis_val is not None:
                    if not _values_match(dp.value, vis_val):
                        continue  # discard conflicting
                    if nk in kept_keys_on_page:
                        continue  # already kept one for this key (duplicate from extraction)
                    kept_keys_on_page.add(nk)
                    # keep; same value as visual
                    result.append(
                        SubmittalDataPoint(
                            key=dp.key,
                            value=dp.value,
                            page_number=dp.page_number,
                            confidence=dp.confidence,
                            human_review_required=dp.human_review_required,
                            source_reliability="HIGH_VISUAL",
                            requires_confirmation=False,
                        )
                    )
                else:
                    # key not in visual -> keep but mark
                    result.append(
                        SubmittalDataPoint(
                            key=dp.key,
                            value=dp.value,
                            page_number=dp.page_number,
                            confidence=dp.confidence,
                            human_review_required=dp.human_review_required,
                            source_reliability="MEDIUM_TEXT",
                            requires_confirmation=True,
                        )
                    )
            # Inject visual-only keys (no kept point for that key on this page)
            for nk, vis_val in page_visual.items():
                if nk in kept_keys_on_page:
                    continue
                # Prefer original key casing from extraction if any; else title-case (e.g. Model, Size)
                display_key = next(
                    (dp.key for dp in extracted_data_points if _norm_key(dp.key) == nk),
                    nk.title() if nk else "Model",
                )
                result.append(
                    SubmittalDataPoint(
                        key=display_key,
                        value=vis_val,
                        page_number=page_num,
                        confidence=0.9,
                        human_review_required=False,
                        source_reliability="HIGH_VISUAL",
                        requires_confirmation=False,
                    )
                )
        else:
            # No visual on this page: keep all, mark MEDIUM_TEXT and requires_confirmation
            for dp in points_on_page:
                result.append(
                    SubmittalDataPoint(
                        key=dp.key,
                        value=dp.value,
                        page_number=dp.page_number,
                        confidence=dp.confidence,
                        human_review_required=dp.human_review_required,
                        source_reliability="MEDIUM_TEXT",
                        requires_confirmation=True,
                    )
                )

    # Sort by page then key for predictability
    result.sort(key=lambda dp: (dp.page_number, _norm_key(dp.key)))
    return result
