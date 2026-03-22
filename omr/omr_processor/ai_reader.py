"""
ai_reader.py
============
AI Vision mode: uses Gemini 2 Flash to read OMR sheets.

Reads barcodes, bubble grids, radio buttons, and handwritten text
directly from the scanned image. Uses Pydantic models for structured
output from Gemini — no manual JSON parsing.

Uses section-by-section cropping for higher accuracy, then merges results.

Returns the same dict format as omr_reader.process_omr() so the
rest of the pipeline (models, views, serialisation) works unchanged.
"""

import logging
import re
import shutil
from pathlib import Path
from typing import Dict, Literal, Optional

import numpy as np
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from PIL import Image, ImageEnhance, ImageOps
from decouple import config

from .barcode_reader import read_barcode
from .preprocessor import load_original_gray
from .roi_utils import crop_roi as crop_section_roi, locate_content_frame, resolve_roi_bounds
from .section_config import SECTION_MAP

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Pydantic response models
# ──────────────────────────────────────────────────────────────────────────────


class BarcodeField(BaseModel):
    decoded_value: Optional[str] = Field(None, description="Numeric value decoded from the barcode bars/lines pattern")
    printed_digits: Optional[str] = Field(None, description="Printed digits near the barcode")


class RadioField(BaseModel):
    value: Optional[str] = Field(None, description="The selected option, or null if none filled")
    filled_bubbles: list[str] = Field(default_factory=list, description="List of all completely filled bubbles")
    multiple_filled: bool = Field(False, description="True if more than one bubble is completely filled")


class GridField(BaseModel):
    handwritten: Optional[str] = Field(None, description="Handwritten text/digits above or near the bubble grid")
    bubble_value: Optional[str] = Field(None, description="Value read from filled bubbles, * for columns with multiple filled")
    column_values: list[str] = Field(default_factory=list, description="Value read from each column left to right")
    multiple_filled: bool = Field(False, description="True if any column has more than one filled bubble")
    columns_with_multiple: list[int] = Field(default_factory=list, description="Column indices that have multiple filled bubbles")


class YearSemField(BaseModel):
    handwritten: Optional[str] = Field(None, description="Handwritten year/sem number in the box")
    bubble_value: Optional[str] = Field(None, description="Value from filled bubble")
    filled_bubbles: list[str] = Field(default_factory=list, description="All filled bubbles")
    multiple_filled: bool = Field(False, description="True if multiple filled")


# ── Part C full response ─────────────────────────────────────────────────────

class PartCResponse(BaseModel):
    barcode: BarcodeField
    ug_old: RadioField
    ug_new: RadioField
    pg_sem: RadioField
    faculty: RadioField
    course_code: GridField
    center_code: GridField
    marks_obtained: GridField
    total_marks: GridField
    subject_text: Optional[str] = Field(None, description="Handwritten subject text")
    marks_in_words: Optional[str] = Field(None, description="Handwritten marks in words")


# ── Part D full response ─────────────────────────────────────────────────────

class PartDResponse(BaseModel):
    barcode: BarcodeField
    roll_number: GridField
    center_code: GridField
    year_sem: YearSemField
    course_code: GridField
    session: GridField
    exam_type: RadioField
    sitting: RadioField
    name: Optional[str] = Field(None, description="Handwritten name")
    father_name: Optional[str] = Field(None, description="Handwritten father name")
    paper_name: Optional[str] = Field(None, description="Handwritten paper name")
    date_of_exam: Optional[str] = Field(None, description="Handwritten date of exam")


# ── Section crop response models ─────────────────────────────────────────────

class PartCSemesterInfo(BaseModel):
    barcode: BarcodeField
    ug_old: RadioField
    ug_new: RadioField
    pg_sem: RadioField


class PartCFacultyCodes(BaseModel):
    faculty: RadioField
    course_code: GridField
    center_code: GridField


class PartCMarks(BaseModel):
    marks_obtained: GridField
    total_marks: GridField
    subject_text: Optional[str] = None
    marks_in_words: Optional[str] = None


class PartDBarcodeOnly(BaseModel):
    barcode: BarcodeField


class PartDRollCenter(BaseModel):
    roll_number: GridField
    center_code: GridField


class PartDCourseSession(BaseModel):
    year_sem: YearSemField
    course_code: GridField
    session: GridField


class PartDExamDetails(BaseModel):
    exam_type: RadioField
    sitting: RadioField
    name: Optional[str] = None
    father_name: Optional[str] = None
    paper_name: Optional[str] = None
    date_of_exam: Optional[str] = None


# ──────────────────────────────────────────────────────────────────────────────
# Prompts (instructions only — no JSON format examples needed with Pydantic)
# ──────────────────────────────────────────────────────────────────────────────

PART_C_PROMPT = """You are an expert OMR sheet reader. Analyze this Part-C OMR sheet from Purnea University with extreme precision.

IMPORTANT: The image may be rotated or upside-down. First orient yourself - the Purnea University header/logo should be at the TOP. The text "PART-C" should be visible near the top-right. Read everything relative to the correct orientation.

INSTRUCTIONS:
- A FILLED bubble is ONLY a circle that is COMPLETELY DARKENED / FULLY SHADED / entirely covered with pen ink. The entire circle must be filled solid.
- A bubble with just a TICK MARK (✓) or CROSS MARK (✗) inside is NOT considered filled. IGNORE tick marks and crosses.
- For EVERY section that has a bubble grid, read BOTH the handwritten text/numbers written near or above the grid AND the filled bubbles. Report both separately.
- If MORE THAN ONE bubble is COMPLETELY FILLED in any single column, set multiple_filled=true, list ALL filled values, and REPLACE that column's digit with * in bubble_value.
- Be very precise - do not guess.

SECTIONS TO READ:

1. BARCODE: Decode the barcode bars/lines pattern to get the numeric value. Also read any printed digits near it.

2. UG OLD (top-left): Three options - Part-I, Part-II, Part-III. Which is completely filled?

3. UG NEW (top-center): Eight options - Sem-I to Sem-VIII. Which is completely filled?

4. PG SEM (top-right): Four options - Sem-I to Sem-IV. Which is completely filled?

5. FACULTY: Options are Arts, Science, Commerce, Education, Vocational, Law, Other. Which is completely filled?

6. COURSE CODE: This grid has EXACTLY 7 columns:
   - Column 0 (leftmost): has ONLY 2 bubbles — "U" at the top and "P" below it. No other bubbles exist in this column.
   - Columns 1 through 6: each has 10 bubbles for digits 0-9 (0 at top, 9 at bottom).
   - CRITICAL: The result is ALWAYS exactly 7 characters (1 letter + 6 digits), e.g. "P246890" or "U216880". Do NOT output more than 7 characters.
   - Read the HANDWRITTEN code above the grid AND the filled bubbles. Report both.

7. CENTER CODE: Grid of 4 columns, each with digits 0-9. Read HANDWRITTEN code AND filled bubbles.

8. MARKS OBTAINED: 2-column bubble grid at bottom-left under "TO BE FILLED BY EXAMINER". Each column has 10 bubbles: 0 at top, 9 at bottom. Column 0 = tens digit, Column 1 = units digit. Example: row 7 filled in col 0 + row 4 filled in col 1 = "74". Read HANDWRITTEN number AND filled bubbles.

9. TOTAL MARKS: Same layout as MARKS OBTAINED — 2-column grid right next to it. Column 0 = tens, Column 1 = units. Read HANDWRITTEN AND filled bubbles.

10. Subject: Read any handwritten text.
11. Marks Obtained in Words: Read any handwritten text."""

PART_D_PROMPT = """You are an expert OMR sheet reader. Analyze this Part-D OMR sheet from Purnea University with extreme precision.

IMPORTANT: The image may be rotated or upside-down. First orient yourself - the Purnea University header/logo should be at the TOP. The text "PART-D" should be visible near the top-right. Read everything relative to the correct orientation.

INSTRUCTIONS:
- A FILLED bubble is ONLY a circle that is COMPLETELY DARKENED / FULLY SHADED / entirely covered with pen ink.
- A bubble with just a TICK MARK (✓) or CROSS MARK (✗) inside is NOT considered filled. IGNORE tick marks and crosses.
- For EVERY section that has a bubble grid, read BOTH the handwritten text/numbers AND the filled bubbles. Report both separately.
- If MORE THAN ONE bubble is COMPLETELY FILLED in any single column, set multiple_filled=true and REPLACE that column's digit with * in bubble_value.
- Be very precise - do not guess.

SECTIONS TO READ:

1. BARCODE: Decode the barcode bars/lines pattern to get the numeric value. Also read any printed digits near it.

2. ROLL NUMBER: Grid of 10 columns, digits 0-9 per column (0 at top, 9 at bottom). Read HANDWRITTEN number AND filled bubbles separately.

3. CENTER CODE: Grid of 4 columns, digits 0-9. Read HANDWRITTEN AND filled bubbles.

4. Year/Sem: Read HANDWRITTEN number AND filled bubble.

5. COURSE CODE: EXACTLY 7 columns:
   - Column 0 (leftmost): ONLY 2 bubbles — "U" at top, "P" below. No other bubbles.
   - Columns 1-6: digits 0-9 (0 at top, 9 at bottom).
   - Result is ALWAYS exactly 7 characters (1 letter + 6 digits) like "U216880" or "P246890". Do NOT output more than 7.
   - Read HANDWRITTEN code AND filled bubbles.

6. SESSION: Grid of 4 columns, digits 0-9. Read HANDWRITTEN AND filled bubbles.

7. EXAM TYPE: Options - Regular, Back Paper, Ex., Improvement. Which is completely filled?

8. Sitting: Options - First, Second. Which is completely filled?

9. Name: Read handwritten text.
10. Father Name: Read handwritten text.
11. Paper Name: Read handwritten text.
12. Date of Exam: Read handwritten text."""

# ── Section crop prompts ──────────────────────────────────────────────────────

SECTION_PROMPTS = {
    "part_d": {
        "barcode_only": """Read this cropped section of an OMR sheet:
1. BARCODE — Decode the barcode bars/lines to get the numeric value. Also read printed digits near it.""",

        "roll_center": """Read this cropped section of an OMR sheet. Read BOTH handwritten AND filled bubbles.

1. ROLL NUMBER — Handwritten digits in boxes at top of bubble grid (typically 10 digits). Then read the bubble grid below — each column has digits 0-9 (0 at top), one filled per column.
2. CENTER CODE — Handwritten digits at top of smaller grid (typically 4 digits). Then read filled bubbles.""",

        "course_session": """Read this cropped section of an OMR sheet. Read BOTH handwritten AND filled bubbles.

1. Year/Sem — Handwritten number in box AND filled bubble.
2. COURSE CODE — EXACTLY 7 columns. Column 0 has ONLY "U" at top and "P" below (no other bubbles). Columns 1-6 have digits 0-9. Result is ALWAYS 7 characters like "U216880" or "P246890". Read handwritten code AND filled bubbles.
3. SESSION — 4-column grid, digits 0-9. Read handwritten AND filled bubbles.""",

        "exam_details": """Read this cropped section of an OMR sheet:
1. EXAM TYPE — Four options: Regular, Back Paper, Ex., Improvement. Which is completely filled/darkened?
2. Sitting — Two options: First, Second. Which is completely filled?
3. Handwritten text: Name, Father Name, Paper Name, Date of Exam.""",
    },
    "part_c": {
        "semester_info": """Read this cropped section of a Part-C OMR sheet:
1. BARCODE — Decode the barcode bars/lines to get the numeric value. Read printed digits near it too.
2. UG OLD — Bubbles for Part-I, Part-II, Part-III. Which is completely filled?
3. UG NEW — Bubbles for Sem-I through Sem-VIII. Which is completely filled?
4. PG SEM — Bubbles for Sem-I through Sem-IV. Which is completely filled?""",

        "faculty_codes": """Read this cropped section of a Part-C OMR sheet. Read BOTH handwritten AND filled bubbles.

Three sections side by side:
- FACULTY — Arts, Science, Commerce, Education, Vocational, Law, Other. Which is completely filled?
- COURSE CODE — EXACTLY 7 columns. Column 0 has ONLY "U" at top and "P" below (no other bubbles). Columns 1-6 have digits 0-9 (0 at top, 9 at bottom). Result is ALWAYS 7 characters like "P246890". Read handwritten code AND filled bubbles.
- CENTER CODE — 4 columns, digits 0-9. Read handwritten AND filled bubbles.""",

        "marks": """Read this cropped section of a Part-C OMR sheet. Read BOTH handwritten AND filled bubbles.

1. MARKS OBTAINED — Under "TO BE FILLED BY EXAMINER". 2-column bubble grid, each column has digits 0-9 (0 at top, 9 at bottom). Column 0 = tens digit, Column 1 = units digit. Example: row 7 filled in col 0 + row 4 filled in col 1 = "74". Read handwritten number AND filled bubbles.
2. TOTAL MARKS — Same layout, right next to MARKS OBTAINED. Column 0 = tens, Column 1 = units.
3. Subject — handwritten text.
4. Marks Obtained in Words — handwritten text.""",
    },
}

# Map section names to their Pydantic response models
SECTION_MODELS = {
    "part_c": {
        "semester_info": PartCSemesterInfo,
        "faculty_codes": PartCFacultyCodes,
        "marks": PartCMarks,
    },
    "part_d": {
        "barcode_only": PartDBarcodeOnly,
        "roll_center": PartDRollCenter,
        "course_session": PartDCourseSession,
        "exam_details": PartDExamDetails,
    },
}


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────


def process_omr_ai(image_path: str, part: Literal["C", "D"]) -> dict:
    """
    Read an OMR sheet using Gemini Vision API with Pydantic structured output.

    Returns the same dict format as omr_reader.process_omr().
    """
    api_key = config("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    model_name = "gemini-2.0-flash"

    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    img = _load_image(str(image_path))
    part_key = "part_c" if part == "C" else "part_d"
    prompt = PART_C_PROMPT if part == "C" else PART_D_PROMPT
    response_model = PartCResponse if part == "C" else PartDResponse

    logger.info("Calling Gemini Vision API for Part %s: %s", part, image_path.name)

    # ── Full image analysis (Pydantic structured output) ─────────────────────
    full_response = client.models.generate_content(
        model=model_name,
        contents=[prompt, img],
        config=types.GenerateContentConfig(
            temperature=0.0,
            max_output_tokens=2048,
            response_mime_type="application/json",
            response_schema=response_model,
        ),
    )
    full_parsed: BaseModel = response_model.model_validate_json(full_response.text)
    logger.debug("Gemini full-image response: %s", full_parsed.model_dump())

    # ── Section-by-section for verification (Pydantic structured output) ─────
    crops = _crop_sections(img, part_key)
    # debug_dir = _export_debug_crops(image_path, img, part, crops)
    section_models = SECTION_MODELS.get(part_key, {})
    section_results: dict[str, BaseModel] = {}

    for section_name, crop_img in crops.items():
        section_prompt = SECTION_PROMPTS.get(part_key, {}).get(section_name)
        sec_model = section_models.get(section_name)
        if not section_prompt or not sec_model:
            continue
        try:
            sec_resp = client.models.generate_content(
                model=model_name,
                contents=[section_prompt, crop_img],
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    max_output_tokens=1024,
                    response_mime_type="application/json",
                    response_schema=sec_model,
                ),
            )
            section_results[section_name] = sec_model.model_validate_json(sec_resp.text)
        except Exception as exc:
            logger.warning("Section %s failed: %s", section_name, exc)

    # ── Merge: section results override full image per field ─────────────────
    merged = full_parsed.model_dump()
    for sec_parsed in section_results.values():
        sec_data = sec_parsed.model_dump()
        for key, val in sec_data.items():
            if _has_real_data(val):
                merged[key] = val

    # ── Decode barcode using pyzbar/zxing (not AI) ─────────────────────────
    try:
        sections = SECTION_MAP[part]
        barcode_def = sections.get("barcode", {})
        existing_barcode = merged.get("barcode") if isinstance(merged.get("barcode"), dict) else {}
        ai_barcode_value = None
        if isinstance(existing_barcode, dict):
            ai_barcode_value = existing_barcode.get("decoded_value") or existing_barcode.get("printed_digits")
        if ai_barcode_value:
            logger.info("AI barcode already present, skipping pyzbar/zxing override: %s", ai_barcode_value)
        else:
            decoded_barcode = None
            if part == "C":
                semester_info_crop = crops.get("semester_info")
                if semester_info_crop is not None:
                    semester_info_gray = np.array(semester_info_crop.convert("L"))
                    decoded_barcode = read_barcode(
                        semester_info_gray,
                        roi_rel=(0.0, 0.0, 1.0, 1.0),
                        orientation=barcode_def.get("orientation", "vertical"),
                    )
                    if decoded_barcode:
                        logger.info("Barcode decoded (semester_info crop): %s", decoded_barcode)
            else:
                original_gray = load_original_gray(str(image_path))
                decoded_barcode = read_barcode(
                    original_gray,
                    roi_rel=barcode_def.get("roi", (0, 0, 1, 1)),
                    orientation=barcode_def.get("orientation", "horizontal"),
                )
            if decoded_barcode:
                logger.info("Barcode decoded (pyzbar/zxing fallback): %s", decoded_barcode)
                if isinstance(merged.get("barcode"), dict):
                    merged["barcode"]["decoded_value"] = decoded_barcode
                else:
                    merged["barcode"] = {"decoded_value": decoded_barcode, "printed_digits": None}
            else:
                logger.warning("Barcode could not be decoded by pyzbar/zxing fallback")
    except Exception as exc:
        logger.error("Barcode decoding failed: %s", exc)

    # ── Build flags ──────────────────────────────────────────────────────────
    flags = _check_multi_bubble_flags(merged)

    # ── Convert to pipeline-compatible format ────────────────────────────────
    result = _normalize_result(merged, part)
    result["mode"] = "ai"
    result["flags"] = flags
    result["ai_raw"] = merged
    # result["debug_crops_dir"] = str(debug_dir)

    logger.info("AI Vision result for Part %s: %s", part, {
        k: v for k, v in result.items() if k not in ("ai_raw",)
    })
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Image loading & enhancement
# ──────────────────────────────────────────────────────────────────────────────


def _load_image(image_path: str) -> Image.Image:
    """Load, auto-rotate (EXIF), enhance contrast for better bubble reading."""
    img = Image.open(image_path)
    img = ImageOps.exif_transpose(img)

    # OMR sheets are portrait — rotate landscape images
    w, h = img.size
    if w > h:
        img = img.rotate(90, expand=True)

    if img.mode != "RGB":
        img = img.convert("RGB")

    img = ImageEnhance.Contrast(img).enhance(1.8)
    img = ImageEnhance.Sharpness(img).enhance(2.0)
    img = ImageOps.autocontrast(img, cutoff=1)

    return img


def _export_debug_crops(
    image_path: Path,
    img: Image.Image,
    part: str,
    crops: Dict[str, Image.Image],
) -> Path:
    debug_dir = Path(__file__).resolve().parents[2] / "omr_debug_crops" / "latest" / f"part_{part.lower()}"
    if debug_dir.exists():
        shutil.rmtree(debug_dir)
    debug_dir.mkdir(parents=True, exist_ok=True)

    img.save(debug_dir / "00_full_ai_input.png")

    for idx, (name, crop_img) in enumerate(crops.items(), start=1):
        crop_img.save(debug_dir / f"{idx:02d}_{name}.png")

    try:
        original_gray = load_original_gray(str(image_path))
        Image.fromarray(original_gray).save(debug_dir / "90_barcode_source_gray.png")
        barcode_def = SECTION_MAP[part].get("barcode", {})
        barcode_roi = crop_section_roi(original_gray, barcode_def.get("roi", (0, 0, 1, 1)))
        if barcode_roi.size:
            Image.fromarray(_pad_gray_crop(barcode_roi, pad_x_ratio=0.08, pad_y_ratio=0.05)).save(debug_dir / "91_barcode_roi_gray.png")
    except Exception as exc:
        logger.warning("Failed to export debug barcode crops: %s", exc)

    logger.info("Saved OMR debug crops to %s", debug_dir)
    return debug_dir


def _pad_gray_crop(crop: np.ndarray, pad_x_ratio: float, pad_y_ratio: float) -> np.ndarray:
    if crop.size == 0:
        return crop
    h, w = crop.shape[:2]
    pad_x = max(4, int(w * pad_x_ratio))
    pad_y = max(4, int(h * pad_y_ratio))
    return np.pad(crop, ((pad_y, pad_y), (pad_x, pad_x)), mode="constant", constant_values=255)


# ──────────────────────────────────────────────────────────────────────────────
# Section cropping
# ──────────────────────────────────────────────────────────────────────────────


def _crop_sections(img: Image.Image, part_type: str) -> Dict[str, Image.Image]:
    """Crop OMR sheet into grouped sections for more accurate AI reading."""
    w, h = img.size
    gray = np.array(img.convert("L"))
    content_frame = locate_content_frame(gray)
    crops = {}

    if part_type == "part_d":
        section_defs = SECTION_MAP["D"]
        crops["barcode_only"] = _crop_group(
            img,
            gray,
            section_defs,
            ["barcode"],
            content_frame,
            fallback=(0, 0, w, int(h * 0.22)),
            expand=(0.08, 0.02, 0.35, 0.10),
        )
        crops["roll_center"] = _crop_group(
            img,
            gray,
            section_defs,
            ["roll_number", "center_code"],
            content_frame,
            fallback=(0, int(h * 0.18), w, int(h * 0.52)),
            expand=(0.03, 0.06, 0.03, 0.04),
        )
        crops["course_session"] = _crop_group(
            img,
            gray,
            section_defs,
            ["year", "sem", "course_code", "session"],
            content_frame,
            fallback=(0, int(h * 0.48), w, int(h * 0.75)),
            expand=(0.03, 0.04, 0.03, 0.04),
        )
        crops["exam_details"] = _crop_group(
            img,
            gray,
            section_defs,
            ["exam_type", "sitting"],
            content_frame,
            fallback=(0, int(h * 0.72), w, h),
            expand=(0.05, 0.03, 0.05, 0.18),
        )
    elif part_type == "part_c":
        section_defs = SECTION_MAP["C"]
        crops["semester_info"] = _crop_group(
            img,
            gray,
            section_defs,
            ["barcode", "ug_old", "ug_new", "pg_sem"],
            content_frame,
            fallback=(0, 0, w, int(h * 0.28)),
            expand=(0.04, 0.03, 0.04, 0.05),
        )
        crops["faculty_codes"] = _crop_group(
            img,
            gray,
            section_defs,
            ["faculty", "course_code", "center_code"],
            content_frame,
            fallback=(0, int(h * 0.25), w, int(h * 0.58)),
            expand=(0.04, 0.04, 0.04, 0.04),
        )
        crops["marks"] = _crop_group(
            img,
            gray,
            section_defs,
            ["marks_obtained", "total_marks"],
            content_frame,
            fallback=(0, int(h * 0.55), w, h),
            expand=(0.04, 0.05, 0.45, 0.02),
        )

    return crops


def _crop_group(
    img: Image.Image,
    gray: np.ndarray,
    section_defs: dict,
    field_names: list[str],
    content_frame: tuple[int, int, int, int],
    fallback: tuple[int, int, int, int],
    expand: tuple[float, float, float, float],
) -> Image.Image:
    bounds = []
    for field_name in field_names:
        section_def = section_defs.get(field_name)
        if not section_def or "roi" not in section_def:
            continue
        bounds.append(resolve_roi_bounds(gray, section_def["roi"], content_frame))

    if not bounds:
        return img.crop(fallback)

    x1 = min(b[0] for b in bounds)
    y1 = min(b[1] for b in bounds)
    x2 = max(b[2] for b in bounds)
    y2 = max(b[3] for b in bounds)
    return img.crop(_expand_bounds((x1, y1, x2, y2), img.size, expand))


def _expand_bounds(
    bounds: tuple[int, int, int, int],
    image_size: tuple[int, int],
    expand: tuple[float, float, float, float],
) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = bounds
    w, h = image_size
    pad_left = int(w * expand[0])
    pad_top = int(h * expand[1])
    pad_right = int(w * expand[2])
    pad_bottom = int(h * expand[3])
    return (
        max(0, x1 - pad_left),
        max(0, y1 - pad_top),
        min(w, x2 + pad_right),
        min(h, y2 + pad_bottom),
    )


# ──────────────────────────────────────────────────────────────────────────────
# Merge helpers
# ──────────────────────────────────────────────────────────────────────────────


def _has_real_data(val) -> bool:
    """Check if a Pydantic-serialised field has actual data (not all None/empty)."""
    if val is None:
        return False
    if isinstance(val, str):
        return bool(val.strip())
    if isinstance(val, dict):
        # For GridField: check if handwritten or bubble_value has data
        hw = val.get("handwritten")
        bv = val.get("bubble_value")
        v = val.get("value")
        dv = val.get("decoded_value")
        return any(
            x is not None and str(x).strip()
            for x in (hw, bv, v, dv)
        )
    return bool(val)


def _check_multi_bubble_flags(data: dict) -> list:
    """Check all fields for multiple filled bubbles."""
    flags = []
    for field_name, field_data in data.items():
        if isinstance(field_data, dict) and field_data.get("multiple_filled"):
            flags.append({
                "field": field_name,
                "issue": "MULTIPLE BUBBLES FILLED",
                "details": field_data.get("columns_with_multiple")
                           or field_data.get("filled_bubbles", []),
                "action": "MANUAL CHECK REQUIRED",
            })
    return flags


# ──────────────────────────────────────────────────────────────────────────────
# Normalize → pipeline dict format
# ──────────────────────────────────────────────────────────────────────────────


def _val(field: dict | None, *keys: str) -> Optional[str]:
    """Extract first non-empty string from a dict field by key priority."""
    if not isinstance(field, dict):
        return str(field) if field else None
    for k in keys:
        v = field.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()
    return None


def _normalize_result(data: dict, part: str) -> dict:
    """
    Convert merged Pydantic dict into the flat dict that
    models.OMRScan.apply_result() expects.
    """
    result = {"part": part}
    readings = {}

    if part == "D":
        bc = data.get("barcode", {})
        result["barcode"] = _val(bc, "decoded_value", "printed_digits")

        result["roll_number"] = _val(data.get("roll_number"), "handwritten", "bubble_value")
        result["center_code"] = _val(data.get("center_code"), "handwritten", "bubble_value")
        result["course_code"] = _val(data.get("course_code"), "handwritten", "bubble_value")
        result["session"] = _val(data.get("session"), "handwritten", "bubble_value")
        result["exam_type"] = _val(data.get("exam_type"), "value")
        result["sitting"] = _val(data.get("sitting"), "value")

        # year_sem split
        ys = data.get("year_sem", {})
        ys_val = _val(ys, "handwritten", "bubble_value")
        if ys_val and "/" in ys_val:
            parts_split = ys_val.split("/")
            result["year"] = parts_split[0].strip() if parts_split else None
            result["sem"] = parts_split[1].strip() if len(parts_split) > 1 else None
        else:
            result["year"] = ys_val
            result["sem"] = None

        # Extra handwritten fields
        result["name"] = data.get("name") or None
        result["father_name"] = data.get("father_name") or None
        result["paper_name"] = data.get("paper_name") or None
        result["date_of_exam"] = data.get("date_of_exam") or None

        # Readings
        for f in ("roll_number", "center_code", "course_code", "session"):
            fd = data.get(f, {})
            readings[f] = {"handwritten": fd.get("handwritten"), "bubble": fd.get("bubble_value")}
        readings["year_sem"] = {"handwritten": ys.get("handwritten"), "bubble": ys.get("bubble_value")}
        readings["barcode"] = {"decoded": bc.get("decoded_value"), "printed_digits": bc.get("printed_digits")}

    elif part == "C":
        bc = data.get("barcode", {})
        result["barcode"] = _val(bc, "decoded_value", "printed_digits")

        result["ug_old"] = _val(data.get("ug_old"), "value")
        result["ug_new"] = _val(data.get("ug_new"), "value")
        result["pg_sem"] = _val(data.get("pg_sem"), "value")

        faculty_val = _val(data.get("faculty"), "value")
        if faculty_val:
            faculty_val = re.sub(r"\(\d+\)$", "", faculty_val).strip()
        result["faculty"] = faculty_val

        result["course_code"] = _val(data.get("course_code"), "handwritten", "bubble_value")
        result["center_code"] = _val(data.get("center_code"), "handwritten", "bubble_value")
        result["marks_obtained"] = _val(data.get("marks_obtained"), "handwritten", "bubble_value")
        result["total_marks"] = _val(data.get("total_marks"), "handwritten", "bubble_value")

        result["subject_text"] = data.get("subject_text") or None
        result["marks_in_words"] = data.get("marks_in_words") or None

        # Readings
        for f in ("course_code", "center_code", "marks_obtained", "total_marks"):
            fd = data.get(f, {})
            readings[f] = {"handwritten": fd.get("handwritten"), "bubble": fd.get("bubble_value")}
        readings["barcode"] = {"decoded": bc.get("decoded_value"), "printed_digits": bc.get("printed_digits")}

    result["readings"] = readings
    return result
