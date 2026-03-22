"""
preprocessor.py
===============
Step 1 of the OMR pipeline.

For Purnea University sheets, the scan already fills the frame cleanly.
We simply load, deskew if needed, and resize to the standard canvas.
No perspective transform is applied unless extreme skew is detected.
"""

import cv2
import numpy as np
import logging
from .section_config import NORM_W, NORM_H

logger = logging.getLogger(__name__)


def preprocess(image_path: str) -> np.ndarray:
    """
    Load the OMR scan and return a normalised grayscale image
    (NORM_W × NORM_H pixels).

    Strategy:
      1. Load the image and ensure portrait orientation
      2. Detect timing marks to find OMR section bounds
         (horizontally: between left/right timing mark columns,
          vertically: from first timing mark to last timing mark)
      3. Resize to NORM_W × NORM_H
    """
    img = _load(image_path)
    img = _ensure_portrait(img)
    _log_sheet_shape(img)
    img = _extract_omr_section(img)
    interpolation = cv2.INTER_AREA if img.shape[0] >= NORM_H else cv2.INTER_CUBIC
    normalised = cv2.resize(img, (NORM_W, NORM_H), interpolation=interpolation)
    gray = cv2.cvtColor(normalised, cv2.COLOR_BGR2GRAY)
    logger.info("Preprocessing complete. Output shape: %s", gray.shape)
    return gray


def load_original_gray(image_path: str) -> np.ndarray:
    """Original image as grayscale, portrait only. For barcode reading."""
    img = _load(image_path)
    img = _ensure_portrait(img)
    img = _extract_omr_section(img)
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def load_color(image_path: str) -> np.ndarray:
    """Same as preprocess() but returns a colour image (for debug overlays)."""
    img = _load(image_path)
    img = _ensure_portrait(img)
    _log_sheet_shape(img)
    img = _extract_omr_section(img)
    interpolation = cv2.INTER_AREA if img.shape[0] >= NORM_H else cv2.INTER_CUBIC
    return cv2.resize(img, (NORM_W, NORM_H), interpolation=interpolation)


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────


def _load(path: str) -> np.ndarray:
    img = cv2.imread(path)
    if img is None:
        raise FileNotFoundError(f"Cannot read image: {path}")
    return img


def _ensure_portrait(img: np.ndarray) -> np.ndarray:
    h, w = img.shape[:2]
    if w > h * 1.05:
        logger.info("Rotating landscape scan to portrait orientation")
        return cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    return img


def _log_sheet_shape(img: np.ndarray) -> None:
    h, w = img.shape[:2]
    if w == 0:
        return
    actual_ratio = h / w
    expected_ratio = NORM_H / NORM_W
    delta = abs(actual_ratio - expected_ratio)
    if delta > expected_ratio * 0.35:
        logger.warning(
            "Unexpected OMR aspect ratio before normalization: %.3f (expected %.3f)",
            actual_ratio,
            expected_ratio,
        )
    else:
        logger.info("Detected OMR image shape: %dx%d", w, h)


def _extract_omr_section(img: np.ndarray) -> np.ndarray:
    """
    Extract the OMR section using timing marks as boundaries.

    Timing marks are short horizontal dashes along the left and right edges.
    - Horizontal: crop to the inner (right) edge of left timing marks
      and inner (left) edge of right timing marks.
    - Vertical: crop from first timing mark top to last timing mark bottom.

    This removes the university header above the first timing mark and
    the text fields (Name, Father Name, etc.) below the last timing mark.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    binary = _binarize(gray)
    h, w = gray.shape

    # Detect timing marks on left and right edges
    left_marks, left_cols = _detect_timing_dashes(binary, side="left")
    right_marks, right_cols = _detect_timing_dashes(binary, side="right")

    if not left_marks and not right_marks:
        logger.warning("No timing marks detected, falling back to auto content crop")
        return _auto_crop_border(img)

    # Horizontal bounds: inner edges of timing mark columns
    left_edge = left_cols[1] if left_cols else 0
    right_edge = right_cols[0] if right_cols else w

    if right_edge <= left_edge:
        left_edge, right_edge = 0, w
    elif left_cols and right_cols and (right_edge - left_edge) < w * 0.18:
        logger.warning(
            "Detected timing columns produce unusually narrow crop (%d px of %d px); falling back to full width",
            right_edge - left_edge,
            w,
        )
        left_edge, right_edge = 0, w

    # Vertical bounds: first mark top to last mark bottom
    all_marks = sorted([*left_marks, *right_marks], key=lambda mark: mark[0])
    if all_marks:
        top_row = all_marks[0][0]
        bottom_row = all_marks[-1][1]
    else:
        return _auto_crop_border(img)

    if (bottom_row - top_row) < h * 0.4:
        logger.warning("Timing-mark crop produced unusually short image, falling back")
        return _auto_crop_border(img)

    logger.info(
        "OMR section: x=%d–%d, y=%d–%d (from %dx%d, %d timing marks)",
        left_edge, right_edge, top_row, bottom_row, w, h,
        len(all_marks) if all_marks else 0,
    )

    cropped = img[top_row:bottom_row, left_edge:right_edge]
    if cropped.size == 0:
        logger.warning("Timing-mark crop produced empty image, falling back")
        return _auto_crop_border(img)
    return cropped


def _detect_timing_dashes(
    binary: np.ndarray, side: str
) -> tuple[list[tuple[int, int]], tuple[int, int] | None]:
    """
    Detect individual timing mark dashes on the given side of the image.

    For the right side, first finds where content actually ends (to handle
    images with large white margins) and searches from there inward.

    Returns:
        marks: list of (row_start, row_end) for each detected dash,
               sorted top-to-bottom.
        col_range: (col_start, col_end) of the timing mark column, or None.
    """
    h, w = binary.shape

    strip_w = max(30, int(w * 0.06))

    content_span = _find_content_column_span(binary)
    if content_span is None:
        return [], None
    content_left, content_right = content_span

    if side == "left":
        left_content = content_left
        strip_end = min(w, left_content + strip_w)
        strip = binary[:, left_content:strip_end]
        offset = left_content
    else:
        right_content = content_right
        strip_start = max(0, right_content - strip_w)
        strip = binary[:, strip_start:right_content]
        offset = strip_start

    sw = strip.shape[1]
    if sw == 0:
        return [], None

    row_density = np.count_nonzero(strip, axis=1) / max(sw, 1)
    kernel = np.ones(5) / 5
    smoothed = np.convolve(row_density, kernel, mode="same")

    # Detect individual dash regions
    threshold = 0.35
    mask = smoothed >= threshold
    diffs = np.diff(mask.astype(np.int8))
    starts = np.where(diffs == 1)[0] + 1
    ends = np.where(diffs == -1)[0] + 1

    if mask[0]:
        starts = np.insert(starts, 0, 0)
    if mask[-1]:
        ends = np.append(ends, len(mask))

    # Real timing marks: thin dashes (5–60 px tall)
    marks = [(int(s), int(e)) for s, e in zip(starts, ends) if 5 <= (e - s) <= 60]

    if len(marks) < 5:
        return [], None

    # Find the column extent of these marks
    col_starts = []
    col_ends = []
    for rs, re in marks[:10]:
        row_slice = strip[rs:re, :]
        cols = np.where(np.any(row_slice > 0, axis=0))[0]
        if cols.size:
            col_starts.append(int(cols[0]))
            col_ends.append(int(cols[-1]) + 1)

    if col_starts:
        col_range = (
            int(np.median(col_starts)) + offset,
            int(np.median(col_ends)) + offset,
        )
    else:
        col_range = None

    logger.info(
        "Timing marks (%s): %d dashes, cols %s",
        side, len(marks), col_range,
    )
    return marks, col_range


def _find_content_column_span(binary: np.ndarray) -> tuple[int, int] | None:
    if binary.size == 0:
        return None

    h, w = binary.shape
    col_density = np.count_nonzero(binary, axis=0) / max(h, 1)
    if not np.any(col_density):
        return None

    window = max(7, w // 120)
    kernel = np.ones(window, dtype=np.float32) / window
    smooth = np.convolve(col_density.astype(np.float32), kernel, mode="same")
    threshold = max(float(np.percentile(smooth, 85)) * 0.35, 0.01)
    active = np.where(smooth >= threshold)[0]
    if active.size == 0:
        return None

    groups = np.split(active, np.where(np.diff(active) > max(2, window // 2))[0] + 1)
    best_group = max(groups, key=lambda group: (group.size, float(np.mean(smooth[group]))))
    start = int(best_group[0])
    end = int(best_group[-1]) + 1
    pad = max(3, w // 150)
    return (max(0, start - pad), min(w, end + pad))


def _find_timing_mark_extent(tm_strip: np.ndarray, img_h: int) -> tuple[int, int]:
    """
    Given a binary strip containing the left timing marks, find the
    row of the first mark's top and the last mark's bottom.

    Individual timing marks are short horizontal dashes (~15-20px tall)
    that repeat at regular intervals (~50px apart).
    """
    if tm_strip.size == 0:
        return 0, img_h

    h, w = tm_strip.shape
    row_density = np.count_nonzero(tm_strip, axis=1) / max(w, 1)

    # Smooth to reduce noise
    kernel = np.ones(5) / 5
    smoothed = np.convolve(row_density, kernel, mode="same")

    # Threshold to find mark regions
    threshold = 0.35
    marks = smoothed >= threshold
    diffs = np.diff(marks.astype(np.int8))
    starts = np.where(diffs == 1)[0] + 1
    ends = np.where(diffs == -1)[0] + 1

    if marks[0]:
        starts = np.insert(starts, 0, 0)
    if marks[-1]:
        ends = np.append(ends, len(marks))

    # Filter: real timing marks are thin dashes (5-60px tall)
    real_marks = [(s, e) for s, e in zip(starts, ends) if 5 <= (e - s) <= 60]

    if not real_marks:
        logger.warning("No individual timing marks found, using full height")
        return 0, img_h

    first_top = real_marks[0][0]
    last_bottom = real_marks[-1][1]
    logger.info(
        "Found %d timing marks: first at row %d, last at row %d",
        len(real_marks), first_top, last_bottom,
    )
    return first_top, last_bottom


def _auto_crop_border(img: np.ndarray) -> np.ndarray:
    """
    Detect and crop to the content area of the sheet, removing scanner
    margins/borders and timing marks. If no clean content rectangle is found,
    returns the original image unchanged.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    bright_blur = cv2.GaussianBlur(gray, (7, 7), 0)
    _, card_mask = cv2.threshold(bright_blur, 245, 255, cv2.THRESH_BINARY_INV)
    kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (max(15, w // 40), max(15, h // 40)))
    kernel_open = cv2.getStructuringElement(cv2.MORPH_RECT, (max(5, w // 200), max(5, h // 200)))
    card_mask = cv2.morphologyEx(card_mask, cv2.MORPH_CLOSE, kernel_close)
    card_mask = cv2.morphologyEx(card_mask, cv2.MORPH_OPEN, kernel_open)
    contours, _ = cv2.findContours(card_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if contours:
        best_cnt = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(best_cnt)
        if area > h * w * 0.08:
            x, y, bw, bh = cv2.boundingRect(best_cnt)
            pad_x = max(8, int(bw * 0.03))
            pad_y = max(8, int(bh * 0.03))
            x1 = max(0, x - pad_x)
            y1 = max(0, y - pad_y)
            x2 = min(w, x + bw + pad_x)
            y2 = min(h, y + bh + pad_y)
            if (x2 - x1) < w and (y2 - y1) < h:
                logger.info("Auto-cropped to sheet bbox: (%d,%d,%d,%d)", x1, y1, x2 - x1, y2 - y1)
                return img[y1:y2, x1:x2]

    binary = _binarize(gray)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best_rect = None
    best_area = 0
    for cnt in contours:
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if len(approx) == 4:
            area = cv2.contourArea(approx)
            if area > best_area and area > h * w * 0.45:
                best_area = area
                best_rect = approx

    if best_rect is not None:
        pts = best_rect.reshape(4, 2).astype(np.float32)
        ordered = _order_points(pts)
        warped = _perspective_transform(img, ordered)
        logger.info("Auto-cropped to content rect, area=%.0f", best_area)
        return warped

    coords = cv2.findNonZero(binary)
    if coords is not None:
        x, y, bw, bh = cv2.boundingRect(coords)
        pad_x = max(2, int(bw * 0.01))
        pad_y = max(2, int(bh * 0.01))
        x1 = max(0, x - pad_x)
        y1 = max(0, y - pad_y)
        x2 = min(w, x + bw + pad_x)
        y2 = min(h, y + bh + pad_y)
        if x1 > 0 or y1 > 0 or x2 < w or y2 < h:
            logger.info("Bounding-box crop: (%d,%d,%d,%d)", x1, y1, x2 - x1, y2 - y1)
            return img[y1:y2, x1:x2]

    logger.info("No crop applied — using full image")
    return img


def _detect_timing_marks(gray: np.ndarray, strip_width: int = 50) -> tuple | None:
    """
    Detect timing marks (dense black dashed bars) on left and right edges.
    Returns (x1, y1, x2, y2) crop bounds or None if not detected.

    Strategy: Look for vertical strips with high black pixel density (the
    timing marks are dense black patterns). The actual OMR card content
    sits between the inner edges of these timing mark strips.
    """
    h, w = gray.shape

    binary = _binarize(gray)
    band_width = max(strip_width, int(w * 0.18))

    left_band = _locate_timing_band(binary[:, :band_width], side="left", offset_x=0)
    right_band = _locate_timing_band(binary[:, w - band_width :], side="right", offset_x=w - band_width)

    if left_band is None or right_band is None:
        return None

    left_edge = left_band[1]
    right_edge = right_band[0]
    if right_edge <= left_edge or (right_edge - left_edge) < w * 0.45:
        return None

    top_edge, bottom_edge = _estimate_content_rows(binary, left_edge, right_edge)
    if (bottom_edge - top_edge) < h * 0.45:
        return None

    return (left_edge, top_edge, right_edge, bottom_edge)


def _binarize(gray: np.ndarray) -> np.ndarray:
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    return cv2.adaptiveThreshold(
        blur,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        31,
        11,
    )


def _locate_timing_band(binary: np.ndarray, side: str, offset_x: int) -> tuple[int, int] | None:
    if binary.size == 0:
        return None

    h, w = binary.shape
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, max(15, h // 24)))
    filtered = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    col_density = np.count_nonzero(filtered, axis=0) / max(h, 1)
    if not np.any(col_density):
        return None

    threshold = max(float(np.percentile(col_density, 90)) * 0.55, 0.03)
    active = np.where(col_density >= threshold)[0]
    if active.size == 0:
        return None

    groups = np.split(active, np.where(np.diff(active) > 2)[0] + 1)
    candidates = []
    min_group_width = max(4, w // 60)
    for group in groups:
        if group.size < min_group_width:
            continue
        x1 = int(group[0])
        x2 = int(group[-1]) + 1
        band = filtered[:, x1:x2]
        if band.size == 0:
            continue
        row_density = np.count_nonzero(band, axis=1) / max(x2 - x1, 1)
        coverage = np.count_nonzero(row_density > 0.10) / max(h, 1)
        if coverage < 0.12:
            continue
        area = float(np.count_nonzero(band))
        edge_bias = (w - x1) if side == "left" else x2
        candidates.append((coverage * area, edge_bias, x1 + offset_x, x2 + offset_x))

    if not candidates:
        return None

    candidates.sort(reverse=True)
    _, _, start, end = candidates[0]
    return start, end


def _estimate_content_rows(binary: np.ndarray, left_edge: int, right_edge: int) -> tuple[int, int]:
    inner = binary[:, left_edge:right_edge]
    if inner.size == 0:
        return 0, binary.shape[0]

    h, w = inner.shape
    x1 = int(w * 0.15)
    x2 = int(w * 0.85)
    central = inner[:, x1:x2]
    if central.size == 0:
        central = inner

    row_density = np.count_nonzero(central, axis=1) / max(central.shape[1], 1)
    if not np.any(row_density):
        return 0, h

    threshold = max(float(np.percentile(row_density, 85)) * 0.45, 0.01)
    active = np.where(row_density >= threshold)[0]
    if active.size == 0:
        return 0, h

    top = max(0, int(active[0]) - 8)
    bottom = min(h, int(active[-1]) + 9)
    return top, bottom


def _order_points(pts: np.ndarray) -> np.ndarray:
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]   # TL
    rect[2] = pts[np.argmax(s)]   # BR
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]  # TR
    rect[3] = pts[np.argmax(diff)]  # BL
    return rect


def _perspective_transform(img: np.ndarray, corners: np.ndarray) -> np.ndarray:
    tl, tr, br, bl = corners
    width_top = np.linalg.norm(tr - tl)
    width_bot = np.linalg.norm(br - bl)
    out_w = int(max(width_top, width_bot))

    height_left = np.linalg.norm(bl - tl)
    height_right = np.linalg.norm(br - tr)
    out_h = int(max(height_left, height_right))

    dst = np.array([
        [0, 0], [out_w - 1, 0],
        [out_w - 1, out_h - 1], [0, out_h - 1],
    ], dtype=np.float32)

    M = cv2.getPerspectiveTransform(corners, dst)
    return cv2.warpPerspective(img, M, (out_w, out_h),
                               flags=cv2.INTER_LINEAR,
                               borderMode=cv2.BORDER_REPLICATE)
