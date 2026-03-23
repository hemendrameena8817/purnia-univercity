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
import json
import re
from pathlib import Path
from typing import Dict, Literal, Optional

import numpy as np
from google import genai
from google.genai import types
from google.genai.errors import ClientError
from pydantic import BaseModel, Field, ValidationError
from PIL import Image, ImageEnhance, ImageOps
from decouple import config

from .barcode_reader import read_barcode
from .preprocessor import load_original_gray
from .roi_utils import crop_roi as crop_section_roi, locate_content_frame, resolve_roi_bounds
from .section_config import SECTION_MAP

logger = logging.getLogger(__name__)

GEMINI_3_MODEL_CANDIDATES = [
    "gemini-2.0-flash",
]


class TruncatedGeminiJSONError(ValueError):
    pass


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
    barcode: Optional[BarcodeField] = None


class PartDRollCenter(BaseModel):
    roll_number: Optional[GridField] = None
    center_code: Optional[GridField] = None
    registration_no: Optional[str] = None


class PartDCourseSession(BaseModel):
    year_sem: Optional[YearSemField] = None
    course_code: Optional[GridField] = None
    session: Optional[GridField] = None


class PartDExamDetails(BaseModel):
    exam_type: Optional[RadioField] = None
    sitting: Optional[RadioField] = None
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
- For EVERY section that has a bubble grid, read BOTH the handwritten text/numbers AND the filled bubbles. Report them separately. Handwritten text must go only in the handwritten field. Filled bubbles must go only in the bubble/value field.
- Read bubble grids COLUMN BY COLUMN from left to right. Do not guess missing columns.
- Always report the ACTUAL LABEL written for the filled bubble, never the visual row index.
- If NO bubble is clearly filled in a field/column, return null for that field/column instead of guessing from handwriting.
- If MORE THAN ONE bubble is COMPLETELY FILLED in any single column, set multiple_filled=true and REPLACE that column's digit with * in bubble_value.
- Be very precise - do not guess.

SECTIONS TO READ:

1. BARCODE: Decode the barcode bars/lines pattern to get the numeric value. Also read any printed digits near it.

2. ROLL NUMBER: Grid of 10 columns, digits 0-9 per column (0 at top, 9 at bottom). Read HANDWRITTEN number AND filled bubbles separately.

3. CENTER CODE: Grid of 4 columns, digits 0-9. Read HANDWRITTEN AND filled bubbles.

4. Year/Sem: Read HANDWRITTEN number AND filled bubble.
    - YEAR and SEM are separate fields. Do not merge them into one combined value.
    - YEAR bubble has only 3 options labeled 1, 2, 3 from top to bottom.
    - SEM bubble has options labeled 0, 1, 2, 3, 4, 5, 6, 7, 8, 9 from top to bottom.
    - Report the actual bubble labels, not the row index.
    - If handwriting says one thing and bubbles show another, keep both separately. Do not copy handwritten text into bubble_value.

5. COURSE CODE: EXACTLY 7 columns:
   - Column 0 (leftmost): ONLY 2 bubbles — "U" at top, "P" below. No other bubbles.
   - Columns 1-6: digits 0-9 (0 at top, 9 at bottom).
   - Read each column independently from left to right.
   - Result is ALWAYS exactly 7 characters from bubbles: 1 letter + 6 digits, like "U216880" or "P246890". Do NOT output more than 7 characters.
   - Do not invent extra digits. Do not copy handwritten text into bubble_value.
   - Read HANDWRITTEN code AND filled bubbles separately.

6. SESSION: Grid of 4 columns, digits 0-9.
   - Read each column left to right.
   - Report the label of the filled bubble in each column.
   - Do not guess digits from handwriting if a bubble is unclear.
   - Read HANDWRITTEN AND filled bubbles separately.

7. EXAM TYPE: Options - Regular, Back Paper, Ex., Improvement.
   - Return ONLY one of these exact labels: Regular, Back Paper, Ex., Improvement.
   - If none is clearly filled, return null.
   - Do not paraphrase or rename the option.

8. Sitting: Options - First, Second.
   - Return ONLY one of these exact labels: First, Second.
   - If none is clearly filled, return null.

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
   - Read column by column from left to right.
   - Report the actual digit label, not the row index.
   - Do not copy handwritten digits into bubble_value.
2. CENTER CODE — Handwritten digits at top of smaller grid (typically 4 digits). Then read filled bubbles.
   - Read column by column from left to right.
   - Report the actual digit label, not the row index.
   - Keep handwritten and bubble values separate.
3. REGISTRATION NO — Read handwritten text only from this same cropped section. Do not infer it from any other section.""",

        "course_session": """Read this cropped section of an OMR sheet. Read BOTH handwritten AND filled bubbles.

1. YEAR — Read handwritten year and the YEAR bubble separately.
    - YEAR has only 3 bubble options labeled 1, 2, 3 from top to bottom.
    - Return the actual label of the filled bubble, not the row index.
    - Do not merge YEAR with SEM.
2. SEM — Read handwritten semester and the SEM bubble separately.
    - SEM has 10 bubble options labeled 0 through 9 from top to bottom.
    - Return the actual label of the filled bubble, not the row index.
    - Do not copy handwritten text into bubble_value.
3. COURSE CODE — EXACTLY 7 columns.
    - Column 0 has ONLY "U" at top and "P" below. No other bubbles are valid in this column.
    - Columns 1-6 each have digits 0-9 from top to bottom.
    - Read each column independently from left to right.
    - Bubble result must be exactly 7 characters: 1 letter + 6 digits.
    - Do not invent extra digits and do not use handwriting to fill unclear bubble columns.
    - Read handwritten code AND filled bubbles separately.
4. SESSION — 4-column grid, digits 0-9.
    - Read each column left to right.
    - Return actual bubble labels, not row indexes.
    - Do not use handwriting to guess unclear bubble digits.
    - Read handwritten AND filled bubbles separately.""",

        "exam_details": """Read this cropped section of an OMR sheet:
1. EXAM TYPE — Four options: Regular, Back Paper, Ex., Improvement.
   - Return ONLY one exact value from this list: Regular, Back Paper, Ex., Improvement.
   - Do not paraphrase the option name.
   - If none is clearly filled, return null.
2. Sitting — Two options: First, Second.
   - Return ONLY one exact value from this list: First, Second.
   - If none is clearly filled, return null.
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

SECTION_FIELD_GROUPS = {
    "C": {
        "semester_info": ["ug_old", "ug_new", "pg_sem"],
        "faculty_codes": ["faculty", "course_code", "center_code"],
        "marks": ["marks_obtained", "total_marks"],
    },
    "D": {
        "barcode_only": [],
        "roll_center": ["roll_number", "center_code"],
        "course_session": ["year", "sem", "course_code", "session"],
        "exam_details": ["exam_type", "sitting"],
    },
}

# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def _response_text_variants(response) -> list[str]:
    variants = []

    text = getattr(response, "text", None)
    if isinstance(text, str) and text.strip():
        variants.append(text.strip())

    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) or []
        part_texts = []
        for part in parts:
            part_text = getattr(part, "text", None)
            if isinstance(part_text, str) and part_text.strip():
                part_texts.append(part_text.strip())
        if part_texts:
            variants.append("".join(part_texts))

    cleaned_variants = []
    seen = set()
    for text in variants:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            cleaned_variants.append(cleaned)
    return cleaned_variants


def _load_json_payload(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        if exc.msg.startswith("EOF while parsing") or exc.msg.startswith("Unterminated string"):
            raise TruncatedGeminiJSONError(str(exc)) from exc
        raise


def _parse_structured_response(response, schema_model: type[BaseModel]) -> BaseModel:
    parsed = getattr(response, "parsed", None)
    if parsed is not None:
        if isinstance(parsed, schema_model):
            return parsed
        if isinstance(parsed, BaseModel):
            return schema_model.model_validate(parsed.model_dump())
        return schema_model.model_validate(parsed)

    last_schema_error = None
    last_truncated_error = None
    for text in _response_text_variants(response):
        try:
            payload = _load_json_payload(text)
            return schema_model.model_validate(payload)
        except TruncatedGeminiJSONError as exc:
            last_truncated_error = exc
        except ValidationError as exc:
            last_schema_error = exc
        except json.JSONDecodeError as exc:
            last_schema_error = exc

    if last_schema_error is not None:
        raise last_schema_error

    if last_truncated_error is not None:
        raise last_truncated_error

    raise TruncatedGeminiJSONError("Gemini returned no parseable JSON content")


def _generate_structured_content(client, model_name, contents, schema_model: type[BaseModel], max_output_tokens: int) -> tuple[BaseModel, str]:
    model_names = [model_name] if isinstance(model_name, str) else list(model_name)
    last_error = None
 
    for candidate_model in model_names:
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=candidate_model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        temperature=0.0,
                        max_output_tokens=max_output_tokens,
                        response_mime_type="application/json",
                        response_schema=schema_model,
                    ),
                )
                return _parse_structured_response(response, schema_model), candidate_model
            except ClientError as exc:
                last_error = exc
                status_code = getattr(exc, "status_code", None)
                if status_code is None:
                    response = getattr(exc, "response", None)
                    status_code = getattr(response, "status_code", None)
                if status_code is None:
                    status_code = getattr(exc, "code", None)
                if status_code == 404:
                    logger.warning("Gemini model %s is unavailable, trying next candidate", candidate_model)
                    break
                if attempt == 2:
                    raise
                logger.warning("Gemini API request failed, retrying: %s", exc)
            except TruncatedGeminiJSONError as exc:
                last_error = exc
                if attempt == 2:
                    raise
                logger.warning("Gemini returned truncated JSON, retrying: %s", exc)
            except Exception as exc:
                last_error = exc
                if attempt == 2:
                    raise
                logger.warning("Gemini structured response parse failed, retrying: %s", exc)

    raise last_error


def process_omr_ai(image_path: str, part: Literal["C", "D"]) -> dict:
    """
    Read an OMR sheet using Gemini Vision API with Pydantic structured output.

    Returns the same dict format as omr_reader.process_omr().
    """
    api_key = config("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    model_name = GEMINI_3_MODEL_CANDIDATES

    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    img = _load_image(str(image_path))
    part_key = "part_c" if part == "C" else "part_d"

    logger.info("Calling Gemini Vision API for Part %s: %s", part, image_path.name)

    resolved_model_name = model_name
    crops = _crop_sections(img, part_key)
    section_models = SECTION_MODELS.get(part_key, {})
    section_results: dict[str, BaseModel] = {}

    for section_name, crop_img in crops.items():
        section_prompt = SECTION_PROMPTS.get(part_key, {}).get(section_name)
        sec_model = section_models.get(section_name)
        if not section_prompt or not sec_model:
            continue
        if part == "D" and section_name == "barcode_only":
            continue
        try:
            section_result, _ = _generate_structured_content(
                client,
                resolved_model_name,
                [section_prompt, crop_img],
                sec_model,
                1536,
            )
            section_results[section_name] = section_result
        except Exception as exc:
            logger.warning("Section %s failed: %s", section_name, exc)

    if not section_results:
        raise RuntimeError("Gemini could not produce usable section output")

    merged = {}
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
            barcode_only_crop = crops.get("barcode_only")
            if barcode_only_crop is not None:
                barcode_only_gray = np.array(barcode_only_crop.convert("L"))
                decoded_barcode = read_barcode(
                    barcode_only_gray,
                    roi_rel=(0.0, 0.0, 1.0, 1.0),
                    orientation=barcode_def.get("orientation", "horizontal"),
                )
                if decoded_barcode:
                    logger.info("Barcode decoded (barcode_only crop): %s", decoded_barcode)

        if decoded_barcode:
            logger.info("Barcode decoded (pyzbar/zxing fallback): %s", decoded_barcode)
            if isinstance(merged.get("barcode"), dict):
                merged["barcode"]["decoded_value"] = decoded_barcode
            else:
                merged["barcode"] = {"decoded_value": decoded_barcode, "printed_digits": None}
        elif ai_barcode_value:
            logger.info("Using AI barcode because local decoder returned nothing: %s", ai_barcode_value)
            if isinstance(merged.get("barcode"), dict):
                merged["barcode"]["decoded_value"] = ai_barcode_value
            else:
                merged["barcode"] = {"decoded_value": ai_barcode_value, "printed_digits": None}
        else:
            logger.warning("Barcode could not be decoded by pyzbar/zxing fallback")
    except Exception as exc:
        logger.error("Barcode decoding failed: %s", exc)

    # ── Build flags ──────────────────────────────────────────────────────────
    flags = _check_multi_bubble_flags(merged)
    verification = _build_verification_report(merged, part)

    # ── Convert to pipeline-compatible format ────────────────────────────────
    result = _normalize_result(merged, part)
    result["mode"] = "ai"
    result["flags"] = flags
    result["verification"] = verification
    result["ai_raw"] = merged

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
            fallback=(0, 0, w, int(h * 0.30)),
            expand=(0.08, 0.02, 0.35, 0.22),
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
        crops["exam_details"] = crops["course_session"]
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


def _clean_compare_value(value) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = re.sub(r"\s+", "", text.upper())
    return text or None


def _split_year_sem_value(value) -> tuple[Optional[str], Optional[str]]:
    if value is None:
        return None, None

    text = str(value).strip()
    if not text:
        return None, None

    cleaned = re.sub(r"\s+", " ", text.upper()).strip()

    match = re.search(r"YEAR\s*[:\-/ ]*([A-Z0-9]+).*?SEM(?:ESTER)?\s*[:\-/ ]*([A-Z0-9]+)", cleaned)
    if match:
        return match.group(1).strip(), match.group(2).strip()

    match = re.search(r"SEM(?:ESTER)?\s*[:\-/ ]*([A-Z0-9]+).*?YEAR\s*[:\-/ ]*([A-Z0-9]+)", cleaned)
    if match:
        return match.group(2).strip(), match.group(1).strip()

    parts = [part.strip() for part in re.split(r"\s*[/,\-]\s*", cleaned) if part.strip()]
    if len(parts) >= 2:
        return parts[0], parts[1]

    tokens = re.findall(r"[A-Z0-9]+", cleaned)
    if len(tokens) >= 2:
        return tokens[0], tokens[1]

    compact = re.sub(r"\s+", "", cleaned)
    if compact.isdigit() and len(compact) == 2:
        return compact[0], compact[1]

    return cleaned, None


def _normalize_year_component(value, reference: Optional[str] = None) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if not text.isdigit():
        return text

    number = int(text)
    if number == 0:
        return "1"

    if reference and str(reference).isdigit():
        ref_number = int(str(reference))
        if 1 <= ref_number <= 3 and number + 1 == ref_number:
            return str(ref_number)

    if 1 <= number <= 3:
        return str(number)
    if 0 <= number <= 2:
        return str(number + 1)
    return str(number)


def _normalize_sem_component(value) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text


def _normalize_exam_type_value(value) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None

    compact = re.sub(r"[^a-z]", "", text.lower())
    if compact == "regular":
        return "Regular"
    if compact == "backpaper":
        return "Back Paper"
    if compact in {"ex", "exam", "external"}:
        return "Ex."
    if compact == "improvement":
        return "Improvement"
    return text


def _expand_year_sem_fields(data: dict, part: str) -> dict:
    if part != "D":
        return data

    year_sem = data.get("year_sem")
    if not isinstance(year_sem, dict):
        return data

    expanded = dict(data)
    handwritten_year, handwritten_sem = _split_year_sem_value(year_sem.get("handwritten"))
    filled_bubbles = year_sem.get("filled_bubbles") or []
    bubble_year = filled_bubbles[0] if len(filled_bubbles) > 0 else None
    bubble_sem = filled_bubbles[1] if len(filled_bubbles) > 1 else None
    if bubble_year is None and bubble_sem is None:
        bubble_year, bubble_sem = _split_year_sem_value(year_sem.get("bubble_value") or year_sem.get("bubble"))
    handwritten_year = _normalize_year_component(handwritten_year)
    handwritten_sem = _normalize_sem_component(handwritten_sem)
    bubble_year = _normalize_year_component(bubble_year, reference=handwritten_year)
    bubble_sem = _normalize_sem_component(bubble_sem)

    expanded["year"] = {
        "handwritten": handwritten_year,
        "bubble_value": bubble_year,
        "filled_bubbles": filled_bubbles,
        "multiple_filled": year_sem.get("multiple_filled", False),
    }
    expanded["sem"] = {
        "handwritten": handwritten_sem,
        "bubble_value": bubble_sem,
        "filled_bubbles": filled_bubbles,
        "multiple_filled": year_sem.get("multiple_filled", False),
    }
    return expanded


def _field_verification(field_name: str, field_data: dict) -> Optional[dict]:
    if not isinstance(field_data, dict):
        return None

    handwritten = field_data.get("handwritten")
    bubble = field_data.get("bubble_value")
    if field_name == "year_sem":
        bubble = field_data.get("bubble_value") or field_data.get("bubble")
    if field_name in ["year", "sem"]:
        bubble = field_data.get("bubble_value")

    normalized_handwritten = _clean_compare_value(handwritten)
    normalized_bubble = _clean_compare_value(bubble)

    if normalized_handwritten is None and normalized_bubble is None:
        return None

    if normalized_handwritten is None or normalized_bubble is None:
        status = "missing"
        remark = "Missing handwritten or bubble value"
    elif normalized_handwritten == normalized_bubble:
        status = "match"
        remark = "Handwritten and bubble values match"
    else:
        status = "mismatch"
        remark = "Handwritten and bubble values do not match"

    verification = {
        "field": field_name,
        "handwritten": handwritten,
        "bubble": bubble,
        "status": status,
        "remark": remark,
    }
    if field_data.get("multiple_filled"):
        verification["multiple_filled"] = True
        verification["columns_with_multiple"] = field_data.get("columns_with_multiple", [])
    return verification


def _build_verification_report(data: dict, part: str) -> dict:
    data = _expand_year_sem_fields(data, part)
    field_checks = []

    for section_name, field_names in SECTION_FIELD_GROUPS.get(part, {}).items():
        for field_name in field_names:
            verification = _field_verification(field_name, data.get(field_name, {}))
            if verification is None:
                continue
            field_checks.append({"section": section_name, **verification})

    mismatch_fields = [
        check["field"]
        for check in field_checks
        if check.get("status") == "mismatch"
    ]
    has_mismatch = any(check["status"] != "match" for check in field_checks)

    return {
        "field_checks": field_checks,
        "mismatch_fields": mismatch_fields,
        "has_mismatch": has_mismatch,
    }


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
    data = _expand_year_sem_fields(data, part)
    result = {"part": part}
    readings = {}

    if part == "D":
        bc = data.get("barcode", {})
        result["barcode"] = _val(bc, "decoded_value", "printed_digits")

        result["roll_number"] = _val(data.get("roll_number"), "handwritten", "bubble_value")
        result["center_code"] = _val(data.get("center_code"), "handwritten", "bubble_value")
        result["course_code"] = _val(data.get("course_code"), "handwritten", "bubble_value")
        result["session"] = _val(data.get("session"), "handwritten", "bubble_value")
        result["exam_type"] = _normalize_exam_type_value(_val(data.get("exam_type"), "value"))
        result["sitting"] = _val(data.get("sitting"), "value")

        result["year"] = _val(data.get("year"), "handwritten", "bubble_value")
        result["sem"] = _val(data.get("sem"), "handwritten", "bubble_value")

        # Extra handwritten fields
        result["registration_no"] = data.get("registration_no") or None
        result["name"] = data.get("name") or None
        result["father_name"] = data.get("father_name") or None
        result["paper_name"] = data.get("paper_name") or None
        result["date_of_exam"] = data.get("date_of_exam") or None

        # Readings
        for f in ("roll_number", "center_code", "course_code", "session"):
            fd = data.get(f, {})
            readings[f] = {"handwritten": fd.get("handwritten"), "bubble": fd.get("bubble_value")}
        readings["year"] = {"handwritten": data.get("year", {}).get("handwritten"), "bubble": data.get("year", {}).get("bubble_value")}
        readings["sem"] = {"handwritten": data.get("sem", {}).get("handwritten"), "bubble": data.get("sem", {}).get("bubble_value")}
        readings["year_sem"] = {"handwritten": data.get("year_sem", {}).get("handwritten"), "bubble": data.get("year_sem", {}).get("bubble_value")}
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