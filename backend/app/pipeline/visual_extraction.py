"""
Multi-Page Visual Extraction service.

1. Scout: PyMuPDF low-res page images + CV detection of highlight/ink (yellow, green, red).
2. Zoom & Extract: Bounding box of annotations → 500x500 crop → multimodal LLM for model + specs.
3. State Merger: final_selection dict appends per page (no overwrite).
4. Safety: Pages with no markings but "Performance Curve" or "Wiring Diagram" → flag for manual review.
"""

import io
import json
import os
from typing import Any, Optional

import fitz  # PyMuPDF
import numpy as np
from PIL import Image

from app.pipeline.pdf_tools import extract_text_by_page

# OpenCV optional for headless envs
try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

# --- Constants ---

SCOUT_DPI_SCALE = 1.5  # Low-res for scout (e.g. 72 * 1.5 ≈ 108 dpi)
ZOOM_DPI_SCALE = 2.5   # Higher res for crop extraction
CROP_SIZE = 500
# HSV ranges for highlight colors (OpenCV: H 0-180, S 0-255, V 0-255)
YELLOW_LOWER = np.array([20, 100, 150])
YELLOW_UPPER = np.array([35, 255, 255])
GREEN_LOWER = np.array([35, 80, 80])
GREEN_UPPER = np.array([85, 255, 255])
RED_LOWER_1 = np.array([0, 100, 100])
RED_UPPER_1 = np.array([10, 255, 255])
RED_LOWER_2 = np.array([170, 100, 100])
RED_UPPER_2 = np.array([180, 255, 255])
# Fraction of page pixels that must be in highlight colors to consider page "marked"
ANNOTATION_PIXEL_FRACTION = 0.002
# Keywords for safety check: unmarked pages containing these → manual review
MANUAL_REVIEW_KEYWORDS = ("performance curve", "wiring diagram", "performance curves", "wiring diagrams")


# --- Scout: page → low-res image, detect annotations ---


def _page_to_lowres_image(doc: fitz.Document, page_index: int) -> Optional[np.ndarray]:
    """Render a single page to a low-res RGB numpy array (H, W, 3)."""
    try:
        page = doc.load_page(page_index)
        mat = fitz.Matrix(SCOUT_DPI_SCALE, SCOUT_DPI_SCALE)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if img.shape[2] == 4:
            img = img[:, :, :3]
        return img
    except Exception:
        return None


def _has_annotation_colors_cv2(img: np.ndarray) -> bool:
    """OpenCV-based: True if significant yellow/green/red pixels (HSV)."""
    if img is None or img.size == 0:
        return False
    bgr = img[:, :, :3] if img.shape[2] >= 3 else img
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    total = hsv.shape[0] * hsv.shape[1]
    if total == 0:
        return False
    yellow = cv2.inRange(hsv, YELLOW_LOWER, YELLOW_UPPER)
    green = cv2.inRange(hsv, GREEN_LOWER, GREEN_UPPER)
    red1 = cv2.inRange(hsv, RED_LOWER_1, RED_UPPER_1)
    red2 = cv2.inRange(hsv, RED_LOWER_2, RED_UPPER_2)
    combined = cv2.bitwise_or(cv2.bitwise_or(yellow, green), red)
    count = int(cv2.countNonZero(combined))
    return (count / total) >= ANNOTATION_PIXEL_FRACTION


def _has_annotation_colors_pil(img: np.ndarray) -> bool:
    """PIL/numpy fallback: count pixels in yellow/green/red RGB ranges."""
    if img is None or img.size == 0:
        return False
    rgb = img[:, :, :3] if img.shape[2] >= 3 else img
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    yellow = (r > 180) & (g > 180) & (b < 120)
    green = (g > 140) & (r < 160) & (b < 160)
    red = (r > 180) & (g < 120) & (b < 120)
    combined = yellow | green | red
    count = int(np.sum(combined))
    total = rgb.shape[0] * rgb.shape[1]
    return total > 0 and (count / total) >= ANNOTATION_PIXEL_FRACTION


def _has_annotation_colors(img: np.ndarray) -> bool:
    """True if page has significant highlight/ink (yellow, green, red)."""
    if img is None or img.size == 0:
        return False
    if HAS_CV2:
        return _has_annotation_colors_cv2(img)
    return _has_annotation_colors_pil(img)


def _page_needs_manual_review(page_text: str) -> bool:
    """True if page has no markings but is a Performance Curve or Wiring Diagram."""
    lower = (page_text or "").lower()
    return any(kw in lower for kw in MANUAL_REVIEW_KEYWORDS)


def scout_marked_pages(pdf_bytes: bytes) -> tuple[list[int], list[int]]:
    """
    Scout each PDF page: low-res render + CV check for annotation colors.
    Also identifies unmarked pages that look like Performance Curve or Wiring Diagram.

    Returns:
        (marked_pages, manual_review_pages) — both 1-based page numbers.
    """
    marked: list[int] = []
    manual_review: list[int] = []
    if not pdf_bytes:
        return (marked, manual_review)

    try:
        stream = io.BytesIO(pdf_bytes)
        doc = fitz.open(stream=stream, filetype="pdf")
    except Exception:
        return (marked, manual_review)

    try:
        page_texts = extract_text_by_page(pdf_bytes)
        text_by_page = {pn: text for pn, text in page_texts}

        for i in range(len(doc)):
            page_num = i + 1
            img = _page_to_lowres_image(doc, i)
            if img is None:
                continue
            if _has_annotation_colors(img):
                marked.append(page_num)
            else:
                text = text_by_page.get(page_num, "")
                if _page_needs_manual_review(text):
                    manual_review.append(page_num)
    finally:
        doc.close()

    return (marked, manual_review)


# --- Zoom & Extract: bbox of highlight → 500x500 crop → multimodal LLM ---


def _get_annotation_bbox_cv2(img: np.ndarray) -> Optional[tuple[int, int, int, int]]:
    """OpenCV: bbox (x, y, w, h) of highlight regions."""
    if img is None or img.size == 0:
        return None
    bgr = img[:, :, :3]
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    y = cv2.inRange(hsv, YELLOW_LOWER, YELLOW_UPPER)
    g = cv2.inRange(hsv, GREEN_LOWER, GREEN_UPPER)
    r1 = cv2.inRange(hsv, RED_LOWER_1, RED_UPPER_1)
    r2 = cv2.inRange(hsv, RED_LOWER_2, RED_UPPER_2)
    combined = cv2.bitwise_or(cv2.bitwise_or(y, g), cv2.bitwise_or(r1, r2))
    contours, _ = cv2.findContours(
        combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    if not contours:
        return None
    xs, ys = [], []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        xs.extend([x, x + w])
        ys.extend([y, y + h])
    if not xs or not ys:
        return None
    return (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


def _get_annotation_bbox_pil(img: np.ndarray) -> Optional[tuple[int, int, int, int]]:
    """PIL/numpy fallback: bbox of yellow/green/red pixels."""
    if img is None or img.size == 0:
        return None
    rgb = img[:, :, :3]
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    yellow = (r > 180) & (g > 180) & (b < 120)
    green = (g > 140) & (r < 160) & (b < 160)
    red = (r > 180) & (g < 120) & (b < 120)
    combined = yellow | green | red
    rows, cols = np.where(combined)
    if rows.size == 0 or cols.size == 0:
        return None
    y_min, y_max = int(rows.min()), int(rows.max())
    x_min, x_max = int(cols.min()), int(cols.max())
    return (x_min, y_min, x_max - x_min, y_max - y_min)


def _get_annotation_bbox(img: np.ndarray) -> Optional[tuple[int, int, int, int]]:
    """Bounding box (x, y, w, h) of highlight/ink; None if none found."""
    if img is None or img.size == 0:
        return None
    if HAS_CV2:
        return _get_annotation_bbox_cv2(img)
    return _get_annotation_bbox_pil(img)


def _center_crop_500(image: np.ndarray, bbox: tuple[int, int, int, int]) -> np.ndarray:
    """
    Create a 500x500 crop centered on the center of bbox.
    Clips to image bounds and resizes if needed to produce 500x500.
    """
    x, y, w, h = bbox
    cx = x + w // 2
    cy = y + h // 2
    h_img, w_img = image.shape[:2]
    half = CROP_SIZE // 2
    x1 = max(0, cx - half)
    y1 = max(0, cy - half)
    x2 = min(w_img, cx + half)
    y2 = min(h_img, cy + half)
    crop = image[y1:y2, x1:x2]
    if crop.size == 0:
        return np.zeros((CROP_SIZE, CROP_SIZE, 3), dtype=np.uint8)
    # Resize to exactly 500x500 if crop was smaller (e.g. near edges)
    if HAS_CV2 and (crop.shape[0] != CROP_SIZE or crop.shape[1] != CROP_SIZE):
        crop = cv2.resize(crop, (CROP_SIZE, CROP_SIZE), interpolation=cv2.INTER_LINEAR)
    elif not HAS_CV2:
        pil_crop = Image.fromarray(crop)
        pil_crop = pil_crop.resize((CROP_SIZE, CROP_SIZE), Image.Resampling.LANCZOS)
        crop = np.array(pil_crop)
    return crop


def _page_to_highres_image(doc: fitz.Document, page_index: int) -> Optional[np.ndarray]:
    """Render page at higher res for zoom/extract (same format as scout)."""
    try:
        page = doc.load_page(page_index)
        mat = fitz.Matrix(ZOOM_DPI_SCALE, ZOOM_DPI_SCALE)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if img.shape[2] == 4:
            img = img[:, :, :3]
        return img
    except Exception:
        return None


def _crop_to_png_bytes(crop: np.ndarray) -> bytes:
    """Encode crop as PNG bytes for LLM upload."""
    if crop.shape[2] == 3:
        pil_img = Image.fromarray(crop)
    else:
        pil_img = Image.fromarray(crop[:, :, :3])
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    return buf.getvalue()


def _call_multimodal_llm(crop_png_bytes: bytes, full_page_text: str, page_num: int) -> dict[str, Any]:
    """
    Send crop image + full page text to multimodal LLM.
    Returns dict with: highlighted_model_or_value, technical_specs (list or dict), confidence.
    """
    use_openai = os.environ.get("EXTRACTION_LLM", "gemini").lower() == "openai"
    prompt = (
        "Looking at the high-res crop provided, identify the specific model or value the contractor has highlighted. "
        "Then, using the full page text below, extract the technical specs for ONLY that model.\n\n"
        "Full page text:\n" + (full_page_text or "(no text)")
        + "\n\nRespond with a single JSON object only (no markdown), with exactly these keys: "
        '"highlighted_model_or_value" (string), "technical_specs" (object or array of key-value pairs), "confidence" (number 0-1).'
    )
    if use_openai:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set for visual extraction.")
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        model = os.environ.get("OPENAI_EXTRACTION_MODEL", "gpt-4o")
        import base64
        b64 = base64.standard_b64encode(crop_png_bytes).decode("ascii")
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt,
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{b64}"},
                        },
                    ],
                },
            ],
            temperature=0.1,
            max_tokens=4096,
        )
        raw = (resp.choices[0].message.content or "").strip()
    else:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set for visual extraction.")
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model_name = os.environ.get("GEMINI_EXTRACTION_MODEL", "gemini-1.5-pro")
        model = genai.GenerativeModel(model_name)
        img_part = {"mime_type": "image/png", "data": crop_png_bytes}
        response = model.generate_content(
            [prompt, img_part],
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                max_output_tokens=4096,
                response_mime_type="application/json",
            ),
        )
        if not response or not response.text:
            return {"highlighted_model_or_value": "", "technical_specs": {}, "confidence": 0.0, "error": "No response"}
        raw = response.text.strip()

    # Parse JSON from response
    start = raw.find("{")
    if start >= 0:
        raw = raw[start:]
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        try:
            import json_repair
            data = json_repair.loads(raw)
        except Exception:
            data = {}
    # Normalize to our expected keys
    return {
        "page_number": page_num,
        "highlighted_model_or_value": data.get("highlighted_model_or_value") or data.get("model") or data.get("value") or "",
        "technical_specs": data.get("technical_specs") or data.get("specs") or {},
        "confidence": float(data.get("confidence", 0.9)),
        "raw_response": data,
    }


def zoom_and_extract(pdf_bytes: bytes, page_num: int) -> dict[str, Any]:
    """
    For a single marked page: find highlight bbox, create 500x500 crop, send crop + full page text
    to multimodal LLM. Returns extraction result for that page.
    """
    result: dict[str, Any] = {
        "page_number": page_num,
        "highlighted_model_or_value": "",
        "technical_specs": {},
        "confidence": 0.0,
        "skipped": False,
        "error": None,
    }
    if not pdf_bytes:
        result["error"] = "No PDF data"
        return result

    try:
        stream = io.BytesIO(pdf_bytes)
        doc = fitz.open(stream=stream, filetype="pdf")
    except Exception as e:
        result["error"] = str(e)
        return result

    try:
        page_index = page_num - 1
        if page_index < 0 or page_index >= len(doc):
            result["error"] = f"Invalid page number {page_num}"
            return result

        # Full page text
        page_texts = extract_text_by_page(pdf_bytes)
        full_page_text = ""
        for pn, text in page_texts:
            if pn == page_num:
                full_page_text = text
                break

        # High-res page image
        img = _page_to_highres_image(doc, page_index)
        if img is None:
            result["error"] = "Could not render page image"
            return result

        bbox = _get_annotation_bbox(img)
        if bbox is None:
            result["skipped"] = True
            result["error"] = "No annotation bounding box found"
            return result

        crop = _center_crop_500(img, bbox)
        crop_png = _crop_to_png_bytes(crop)

        llm_out = _call_multimodal_llm(crop_png, full_page_text, page_num)
        result["highlighted_model_or_value"] = llm_out.get("highlighted_model_or_value", "")
        result["technical_specs"] = llm_out.get("technical_specs", {})
        result["confidence"] = llm_out.get("confidence", 0.0)
        if "error" in llm_out:
            result["error"] = llm_out["error"]
    finally:
        doc.close()

    return result


# --- State Merger: append into final_selection (no overwrite) ---


def merge_into_final_selection(
    final_selection: dict[str, Any],
    page_num: int,
    extraction: dict[str, Any],
) -> None:
    """
    Append this page's extraction to final_selection. Uses page key so we never overwrite
    previous pages (e.g. page 5, 12, 40 each get their own key).
    """
    key = f"page_{page_num}"
    # Append: if key already exists, we still replace for that page (one extraction per page);
    # the requirement is "don't overwrite previous *pages*" — so we add/update only this page's key.
    final_selection[key] = {
        "page_number": page_num,
        "highlighted_model_or_value": extraction.get("highlighted_model_or_value", ""),
        "technical_specs": extraction.get("technical_specs", {}),
        "confidence": extraction.get("confidence", 0.0),
        "skipped": extraction.get("skipped", False),
        "error": extraction.get("error"),
    }


# --- Orchestrator: scout → zoom/extract each marked page → merge; safety flags ---


def run_visual_extraction(pdf_bytes: bytes) -> dict[str, Any]:
    """
    Full pipeline:
    1. Scout: get marked_pages and manual_review_pages.
    2. For each marked_page: zoom_and_extract, then merge into final_selection.
    3. Return final_selection (accumulated) + marked_pages + manual_review_pages.

    Returns:
        {
            "final_selection": { "page_5": {...}, "page_12": {...}, ... },
            "marked_pages": [5, 12, 40],
            "manual_review_pages": [7, 23],
        }
    """
    final_selection: dict[str, Any] = {}
    marked_pages, manual_review_pages = scout_marked_pages(pdf_bytes)

    for page_num in marked_pages:
        extraction = zoom_and_extract(pdf_bytes, page_num)
        merge_into_final_selection(final_selection, page_num, extraction)

    return {
        "final_selection": final_selection,
        "marked_pages": marked_pages,
        "manual_review_pages": manual_review_pages,
    }
