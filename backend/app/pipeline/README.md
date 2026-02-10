# Spec vs. Submittal Audit Pipeline

Multi-step agentic "assembly line" for construction Spec vs. Submittal audits. State is managed with Pydantic; each step is a pure function that takes and returns `SubmittalState`.

## File Structure

```
pipeline/
├── __init__.py       # Public API: SubmittalState, run_pipeline, enums
├── state.py          # SubmittalState and all Pydantic models (TriageStatus, ReviewStamp, Variance, etc.)
├── schemas.py        # Strict JSON schemas for LLM extraction (confidence scores, page numbers)
├── pdf_tools.py      # PyMuPDF page-level extraction (extract_text_by_page)
├── units.py          # Unit normalization for audit (time → minutes, length → inches)
├── orchestrator.py   # run_pipeline(spec_pdf_bytes, submittal_pdf_bytes) → SubmittalState
├── agents/
│   ├── __init__.py
│   ├── triage.py     # triage_agent: Action Submittal requirements vs Submittal TOC
│   ├── extraction.py# extraction_agent: spec + submittal PDFs → requirements/data with page #s + confidence
│   ├── audit.py      # audit_agent: spec vs submittal comparison with unit normalization
│   └── synthesis.py  # synthesis_agent: review_stamp (Approved | Approved as Noted | Revise and Resubmit)
└── README.md
```

## State (`SubmittalState`)

- **spec_requirements**: Technical specs from spec PDF (with optional source_page, confidence).
- **submittal_data**: Extracted data points from submittal PDF; each has `page_number` and `confidence`; `human_review_required` is True when confidence < 0.8.
- **action_submittal_requirements** / **submittal_toc**: Used by triage.
- **triage_status**: `Complete` | `Incomplete` (based on required documents vs TOC).
- **variances**: List of discrepancies (spec_key, spec_value, submittal_value, severity, explanation).
- **review_stamp**: `Approved` | `Approved as Noted` | `Revise and Resubmit` | `Rejected`.
- **human_review_items**: Keys with confidence < 0.8 for human-in-the-loop.

## Execution Order

1. **extraction_agent**: Extracts from both PDFs (spec requirements, action submittal list, submittal TOC, submittal data). Uses GPT-4o or Gemini 1.5 Pro; output forced to strict JSON. Every value has a page number and confidence.
2. **triage_agent**: Compares required Action Submittal items to submittal TOC; sets triage_status and triage_missing.
3. **audit_agent**: Compares spec_requirements to submittal_data with unit normalization (e.g. 2 hours ≡ 120 mins); populates variances.
4. **synthesis_agent**: Sets review_stamp and synthesis_notes from triage + variances + human_review_items.

## Tooling

- **PDF**: PyMuPDF (`fitz`) via `pdf_tools.extract_text_by_page()`.
- **LLM**: Set `EXTRACTION_LLM=gemini` (default) or `openai`. Gemini: `GEMINI_API_KEY`, `GEMINI_EXTRACTION_MODEL=gemini-1.5-pro`. OpenAI: `OPENAI_API_KEY`, `OPENAI_EXTRACTION_MODEL=gpt-4o`.
- **Safety**: Confidence score per extraction; items with confidence < 0.8 are flagged in `human_review_items` and `SubmittalDataPoint.human_review_required`.

## API

- **POST /api/pipeline/audit**: Form-data with `spec_pdf` and `submittal_pdf` (both PDF files). Returns full `SubmittalState` as JSON.

## Usage

```python
from app.pipeline import run_pipeline, SubmittalState

state = run_pipeline(spec_pdf_bytes, submittal_pdf_bytes)
print(state.triage_status, state.review_stamp, state.variances, state.human_review_items)
```
