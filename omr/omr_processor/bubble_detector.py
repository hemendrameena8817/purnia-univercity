"""
bubble_detector.py
==================
Step 2 of the OMR pipeline.

Given a normalised grayscale image and a section definition:
  • Crops the Region of Interest (ROI)
  • Divides it into a rows × cols grid
  • Measures fill level of each cell using Otsu + density
  • Returns which bubble is filled per column

Algorithm: per-cell Otsu binarisation + dark-pixel ratio.
This handles any ink colour (blue, black, pencil) reliably.
"""

import cv2
import numpy as np
import logging
from typing import Any

from .section_config import NORM_W, NORM_H, SECTION_MAP
from .roi_utils import crop_roi

logger = logging.getLogger(__name__)

# A column is considered "filled" if its best cell has dark-pixel density >= this
FILL_THRESHOLD = 0.09

# Min ratio: best cell density / mean cell density of the column
# Prevents picking a bubble when the whole column is uniformly light
RATIO_THRESHOLD = 1.55
MIN_FILL_DENSITY = 0.025
MIN_CORE_FILL_DENSITY = 0.040
MIN_SCORE_GAP = 0.012


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────


def read_section(gray: np.ndarray, section_name: str, section_def: dict) -> Any:
    """
    Read a single section from the normalised grayscale image.

    Returns:
        • bubble_grid  → dict  {col_index: value_string}
        • radio        → str   (selected option label) or None
        • barcode      → handled by barcode_reader, not here
    """
    stype = section_def["type"]
    if stype == "barcode":
        return None  # delegated to barcode_reader.py

    roi_img = crop_roi(gray, section_def["roi"])
    if not section_def.get("skip_refine"):
        roi_img = _refine_roi(roi_img, stype)
    # NOTE: do NOT apply CLAHE — it also boosts the pink printed circle
    # outlines to the same darkness as filled ink, making them indistinguishable.

    if stype == "bubble_grid":
        return _read_bubble_grid(roi_img, section_def)
    elif stype == "radio":
        return _read_radio(roi_img, section_def)
    else:
        logger.warning("Unknown section type '%s' for '%s'", stype, section_name)
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Bubble grid
# ──────────────────────────────────────────────────────────────────────────────


def _read_bubble_grid(roi_img: np.ndarray, section_def: dict) -> dict:
    """
    Divide the ROI into a rows×cols grid, measure density, return selected value
    per column.

    Returns: {col_index (int): selected_value (str) or None}
    """
    rows = section_def["rows"]
    cols = section_def["cols"]
    values = section_def.get("values", [str(i) for i in range(rows)])
    col_values = section_def.get("col_values")  # per-column value lists
    select_mode = section_def.get("select", "one_per_col")
    prefix_col = section_def.get("prefix_col")

    h, w = roi_img.shape
    cell_h = h / rows
    cell_w = w / cols

    # ── Build density matrix (rows × cols) ──────────────────────────────────
    score = np.zeros((rows, cols), dtype=np.float32)
    select_density = np.zeros((rows, cols), dtype=np.float32)
    fill_density = np.zeros((rows, cols), dtype=np.float32)
    core_fill_density = np.zeros((rows, cols), dtype=np.float32)
    for r in range(rows):
        for c in range(cols):
            y1 = int(r * cell_h)
            y2 = int((r + 1) * cell_h)
            x1 = int(c * cell_w)
            x2 = int((c + 1) * cell_w)
            cell = roi_img[y1:y2, x1:x2]
            metrics = _cell_metrics(cell)
            score[r, c] = metrics["score"]
            select_density[r, c] = metrics["select_density"]
            fill_density[r, c] = metrics["fill_density"]
            core_fill_density[r, c] = metrics["core_fill_density"]

    result = {}

    # ── Handle prefix column (e.g. "U" or "P") ──────────────────────────────
    start_col = 0
    if prefix_col:
        pi = prefix_col["col_index"]
        poptions = prefix_col["options"]
        n_opts = len(poptions)
        prefix_scores = score[:n_opts, pi]
        best = int(np.argmax(prefix_scores))
        second_best = float(np.partition(prefix_scores, -2)[-2]) if n_opts > 1 else 0.0
        if _is_marked(
            prefix_scores[best],
            float(np.mean(prefix_scores)),
            float(fill_density[best, pi]),
            float(core_fill_density[best, pi]),
            second_best,
        ):
            result[pi] = poptions[best]
        else:
            result[pi] = None
        start_col = pi + 1

    # ── Regular digit columns ────────────────────────────────────────────────
    for c in range(start_col, cols):
        col_score = score[:, c]

        if select_mode == "one_per_col":
            best_row = int(np.argmax(col_score))
            best_score = float(col_score[best_row])
            second_best = float(np.partition(col_score, -2)[-2]) if rows > 1 else 0.0
            mean_score = float(np.mean(col_score))

            if not _is_marked(
                best_score,
                mean_score,
                float(fill_density[best_row, c]),
                float(core_fill_density[best_row, c]),
                second_best,
            ):
                result[c] = None
                continue

            col_vals = col_values[c] if col_values and c in col_values else values
            result[c] = col_vals[best_row] if best_row < len(col_vals) else str(best_row)

        elif select_mode == "multi":
            col_vals = col_values[c] if col_values and c in col_values else values
            selected = [
                col_vals[r] if r < len(col_vals) else str(r)
                for r in range(rows)
                if _is_marked(
                    float(col_score[r]),
                    float(np.mean(col_score)),
                    float(fill_density[r, c]),
                    float(core_fill_density[r, c]),
                    0.0,
                )
            ]
            result[c] = selected or None

    return result


# ──────────────────────────────────────────────────────────────────────────────
# Radio buttons
# ──────────────────────────────────────────────────────────────────────────────


def _read_radio(roi_img: np.ndarray, section_def: dict) -> str | None:
    """
    For a set of radio buttons (one answer), divide the ROI by direction,
    measure density per option zone, return the selected label.

    Supports direction: "vertical", "horizontal", or "grid" (2D grid layout).
    """
    options = section_def["options"]
    direction = section_def.get("direction", "vertical")
    n = len(options)
    h, w = roi_img.shape

    scores = []
    fills = []
    core_fills = []

    if direction == "grid":
        grid_rows = section_def.get("grid_rows", 2)
        grid_cols = section_def.get("grid_cols", 2)
        idx = 0
        for r in range(grid_rows):
            for c in range(grid_cols):
                if idx >= n:
                    break
                y1 = int(r * h / grid_rows)
                y2 = int((r + 1) * h / grid_rows)
                x1 = int(c * w / grid_cols)
                x2 = int((c + 1) * w / grid_cols)
                cell = roi_img[y1:y2, x1:x2]
                metrics = _cell_metrics(cell)
                scores.append(metrics["score"])
                fills.append(metrics["fill_density"])
                core_fills.append(metrics["core_fill_density"])
                idx += 1
    else:
        for i in range(n):
            if direction == "vertical":
                y1 = int(i * h / n)
                y2 = int((i + 1) * h / n)
                cell = roi_img[y1:y2, :]
            else:
                x1 = int(i * w / n)
                x2 = int((i + 1) * w / n)
                cell = roi_img[:, x1:x2]

            metrics = _cell_metrics(cell)
            scores.append(metrics["score"])
            fills.append(metrics["fill_density"])
            core_fills.append(metrics["core_fill_density"])

    best_idx = int(np.argmax(scores))
    second_best = float(np.partition(np.asarray(scores), -2)[-2]) if len(scores) > 1 else 0.0
    if not _is_marked(
        float(scores[best_idx]),
        float(np.mean(scores)),
        float(fills[best_idx]),
        float(core_fills[best_idx]),
        second_best,
    ):
        return None

    return options[best_idx]


# ──────────────────────────────────────────────────────────────────────────────
# Utilities
# ──────────────────────────────────────────────────────────────────────────────


def _enhance(gray: np.ndarray) -> np.ndarray:
    """Kept for reference but NOT called in the main pipeline."""
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    return clahe.apply(gray)


def _crop_roi(gray: np.ndarray, roi_rel: tuple) -> np.ndarray:
    """Crop using relative 0–1 coordinates."""
    return crop_roi(gray, roi_rel)


def _refine_roi(roi_img: np.ndarray, stype: str) -> np.ndarray:
    if roi_img.size == 0:
        return roi_img

    binary = cv2.adaptiveThreshold(
        cv2.GaussianBlur(roi_img, (5, 5), 0),
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        31,
        8,
    )
    col_density = np.count_nonzero(binary, axis=0) / max(binary.shape[0], 1)
    row_density = np.count_nonzero(binary, axis=1) / max(binary.shape[1], 1)
    col_threshold = max(float(np.percentile(col_density, 85)) * 0.40, 0.01)
    row_threshold = max(float(np.percentile(row_density, 85)) * 0.40, 0.01)
    active_x = np.where(col_density >= col_threshold)[0]
    active_y = np.where(row_density >= row_threshold)[0]
    if active_x.size == 0 or active_y.size == 0:
        return roi_img

    x1 = int(active_x[0])
    x2 = int(active_x[-1]) + 1
    y1 = int(active_y[0])
    y2 = int(active_y[-1]) + 1
    min_width = roi_img.shape[1] * (0.55 if stype == "bubble_grid" else 0.45)
    min_height = roi_img.shape[0] * (0.45 if stype == "bubble_grid" else 0.35)
    if (x2 - x1) < min_width or (y2 - y1) < min_height:
        return roi_img

    pad_x = max(2, int((x2 - x1) * 0.02))
    pad_y = max(2, int((y2 - y1) * 0.03))
    x1 = max(0, x1 - pad_x)
    x2 = min(roi_img.shape[1], x2 + pad_x)
    y1 = max(0, y1 - pad_y)
    y2 = min(roi_img.shape[0], y2 + pad_y)
    return roi_img[y1:y2, x1:x2]


def _cell_metrics(cell: np.ndarray, inner_margin: float = 0.06) -> dict[str, float]:
    if cell.size == 0:
        return {
            "score": 0.0,
            "select_density": 0.0,
            "fill_density": 0.0,
            "core_fill_density": 0.0,
        }

    h, w = cell.shape
    my = max(1, int(h * inner_margin))
    mx = max(1, int(w * inner_margin))
    inner = cell[my: h - my, mx: w - mx]
    if inner.size == 0:
        inner = cell

    core_margin_y = max(1, int(inner.shape[0] * 0.18))
    core_margin_x = max(1, int(inner.shape[1] * 0.18))
    core = inner[
        core_margin_y: inner.shape[0] - core_margin_y,
        core_margin_x: inner.shape[1] - core_margin_x,
    ]
    if core.size == 0:
        core = inner

    select_density = float(np.mean(inner < 165))
    fill_density = float(np.mean(inner < 130))
    core_fill_density = float(np.mean(core < 145))
    darkness = float((255.0 - np.mean(core)) / 255.0)
    score = (select_density * 0.35) + (fill_density * 0.40) + (core_fill_density * 0.20) + (darkness * 0.05)
    return {
        "score": score,
        "select_density": select_density,
        "fill_density": fill_density,
        "core_fill_density": core_fill_density,
    }


def _is_marked(
    best_score: float,
    mean_score: float,
    fill_density: float,
    core_fill_density: float,
    second_best: float,
) -> bool:
    if best_score < FILL_THRESHOLD:
        return False
    if fill_density < MIN_FILL_DENSITY and core_fill_density < MIN_CORE_FILL_DENSITY:
        return False
    if mean_score > 0 and best_score / mean_score < RATIO_THRESHOLD:
        return False
    if second_best > 0 and (best_score - second_best) < MIN_SCORE_GAP:
        return False
    return True

