"""
omr_reader.py
=============
Main orchestrator for the OMR processing pipeline.

Usage:
    from omr_app.omr_processor.omr_reader import process_omr

    result = process_omr("path/to/scan.jpg", part="D")
    # returns a structured dict with all section values

Part D example output:
    {
        "part": "D",
        "barcode": "3082993",
        "roll_number": "04235997214",
        "center_code": "2546",
        "year": "2",
        "sem": "1",
        "course_code": "U216880",
        "session": "6420",
        "exam_type": "Ex.",
        "sitting": "First",
        "raw": { ... }   # per-section raw grid data
    }

Part C example output:
    {
        "part": "C",
        "barcode": "3082993",
        "ug_old": None,
        "ug_new": "Sem-IV",
        "pg_sem": None,
        "faculty": "Education",
        "course_code": "P01234",
        "center_code": "9876",
        "marks_obtained": "74",
        "total_marks": "86",
        "raw": { ... }
    }
"""

import logging
from typing import Literal

from .preprocessor import preprocess, load_original_gray
from .bubble_detector import read_section
from .barcode_reader import read_barcode
from .section_config import SECTION_MAP, NORM_W, NORM_H

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────


def process_omr(image_path: str, part: Literal["C", "D"]) -> dict:
    """
    Full pipeline: load → correct → read bubbles → assemble result.

    Args:
        image_path : absolute path to the scanned OMR image
        part       : "C" (evaluator sheet) or "D" (student info sheet)

    Returns:
        Structured dictionary (see module docstring for format).
    """
    # ── Step 1: Pre-process ──────────────────────────────────────────────────
    gray = preprocess(image_path)
    original_gray = load_original_gray(image_path)
    sections = SECTION_MAP[part]

    raw = {}
    result = {"part": part, "raw": raw}

    # ── Step 2: Read each section ────────────────────────────────────────────
    for section_name, section_def in sections.items():
        stype = section_def["type"]

        if stype == "barcode":
            # Barcode from ORIGINAL image (warping distorts bars)
            value = read_barcode(
                original_gray,
                roi_rel=section_def["roi"],
                orientation=section_def.get("orientation", "horizontal"),
            )
            raw[section_name] = value
            result[section_name] = value

        elif stype == "bubble_grid":
            grid = read_section(gray, section_name, section_def)
            raw[section_name] = grid
            result[section_name] = _collapse_grid(grid, section_def)

        elif stype == "radio":
            value = read_section(gray, section_name, section_def)
            raw[section_name] = value
            result[section_name] = value

    # ── Step 3: Post-process into friendly fields ────────────────────────────
    if part == "D":
        result = _postprocess_d(result)
    else:
        result = _postprocess_c(result)

    logger.info("OMR result for Part %s: %s", part, _summary(result))
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Grid → string helpers
# ──────────────────────────────────────────────────────────────────────────────


def _collapse_grid(grid: dict | None, section_def: dict) -> str | None:
    """
    Convert a {col_index: value_str} dict into a single concatenated string.
    None columns become '' (blank / unread digit).
    Prefix column (index 0 for course_code) is included as the first char.
    """
    if not grid:
        return None
    cols = section_def.get("cols", 0)
    parts = []
    for c in range(cols):
        v = grid.get(c)
        parts.append(v if v is not None else "?")
    return "".join(parts)


# ──────────────────────────────────────────────────────────────────────────────
# Part-specific post-processing
# ──────────────────────────────────────────────────────────────────────────────


def _postprocess_d(result: dict) -> dict:
    """
    For Part D: extract year/sem from their single-column grids.
    """
    raw_year = result.get("raw", {}).get("year", {})
    raw_sem = result.get("raw", {}).get("sem", {})
    result["year"] = raw_year.get(0)
    result["sem"] = raw_sem.get(0)
    return result


def _postprocess_c(result: dict) -> dict:
    """
    For Part C: convert marks_obtained / total_marks from "tens|units" format
    to an integer string ("74" not "7|4").
    """
    for field in ("marks_obtained", "total_marks"):
        raw_grid = result.get("raw", {}).get(field, {})
        if raw_grid:
            tens = raw_grid.get(0, "?")
            units = raw_grid.get(1, "?")
            result[field] = f"{tens}{units}"
        else:
            result[field] = None
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Logging helper
# ──────────────────────────────────────────────────────────────────────────────


def _summary(result: dict) -> str:
    skip = {"raw"}
    return ", ".join(
        f"{k}={v}" for k, v in result.items() if k not in skip and v is not None
    )
