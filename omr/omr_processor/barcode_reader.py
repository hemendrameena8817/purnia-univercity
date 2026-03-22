"""
barcode_reader.py
=================
Reads the linear barcode printed on the OMR sheet.

Primary:  pyzbar (fast, Python-native)
Fallback: zxing-cpp (handles more barcode types)

The barcode ROI from section_config is cropped, enhanced, and decoded.
Vertical barcodes (Part D) are rotated 90° before decoding.
"""

import cv2
import numpy as np
import logging
from typing import Optional

from .roi_utils import crop_roi as crop_section_roi

logger = logging.getLogger(__name__)


def normalize_barcode_value(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None

    compact = str(value).strip().replace(" ", "").replace("-", "")
    if not compact or not compact.isdigit():
        return None
    if len(compact) < 6 or len(compact) > 12:
        return None
    return compact


def is_valid_barcode_value(value: Optional[str]) -> bool:
    return normalize_barcode_value(value) is not None


def read_barcode(
    gray: np.ndarray, roi_rel: tuple, orientation: str = "horizontal"
) -> Optional[str]:
    """
    Decode barcode from the original (unwarped) grayscale image.

    Strategy: try ROI crop first, then fall back to full image rotations.
    """
    roi = crop_section_roi(gray, roi_rel)
    for roi_variant in _barcode_roi_variants(roi, orientation):
        for candidate in _barcode_candidates(roi_variant, orientation):
            result = _try_pyzbar(candidate)
            if result:
                logger.info("Barcode decoded (pyzbar, ROI): %s", result)
                return result

            result = _try_zxing(candidate)
            if result:
                logger.info("Barcode decoded (zxing, ROI): %s", result)
                return result

    for img in [gray,
                cv2.rotate(gray, cv2.ROTATE_90_CLOCKWISE),
                cv2.rotate(gray, cv2.ROTATE_90_COUNTERCLOCKWISE)]:
        result = _try_pyzbar(img)
        if result:
            logger.info("Barcode decoded (pyzbar, full image): %s", result)
            return result

        result = _try_zxing(img)
        if result:
            logger.info("Barcode decoded (zxing, full image): %s", result)
            return result

    logger.warning("Barcode could not be decoded.")
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Decoders
# ──────────────────────────────────────────────────────────────────────────────


def _try_pyzbar(img: np.ndarray) -> Optional[str]:
    try:
        from pyzbar.pyzbar import decode

        codes = decode(img)
        for code in codes:
            normalized = normalize_barcode_value(code.data.decode("utf-8", errors="replace"))
            if normalized:
                return normalized
    except ImportError:
        logger.debug("pyzbar not installed — skipping.")
    except Exception as exc:
        logger.debug("pyzbar error: %s", exc)
    return None


def _try_zxing(img: np.ndarray) -> Optional[str]:
    try:
        import zxingcpp

        result = zxingcpp.read_barcode(img)
        if result and result.valid:
            return normalize_barcode_value(result.text)
    except ImportError:
        logger.debug("zxingcpp not installed — skipping.")
    except Exception as exc:
        logger.debug("zxingcpp error: %s", exc)
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Image utilities
# ──────────────────────────────────────────────────────────────────────────────


def _crop_roi(gray: np.ndarray, roi_rel: tuple) -> np.ndarray:
    return crop_section_roi(gray, roi_rel)


def _barcode_roi_variants(roi: np.ndarray, orientation: str) -> list[np.ndarray]:
    if roi.size == 0:
        return [roi]

    variants = [roi]
    trims = [
        (0.03, 0.03, 0.03, 0.03),
        (0.06, 0.05, 0.08, 0.05),
    ]
    if orientation == "vertical":
        trims.extend([
            (0.08, 0.06, 0.14, 0.08),
            (0.12, 0.08, 0.18, 0.10),
        ])

    for trim in trims:
        cropped = _trim_roi(roi, trim)
        if cropped.size:
            variants.append(cropped)

    focused = _focused_barcode_roi(roi)
    if focused.size:
        variants.append(focused)
        tighter = _trim_roi(focused, (0.03, 0.03, 0.03, 0.03))
        if tighter.size:
            variants.append(tighter)

    unique = []
    seen = set()
    for variant in variants:
        key = (variant.shape, int(np.mean(variant)), int(np.std(variant)))
        if key in seen:
            continue
        seen.add(key)
        unique.append(variant)
    return unique


def _trim_roi(roi: np.ndarray, trim: tuple[float, float, float, float]) -> np.ndarray:
    if roi.size == 0:
        return roi
    h, w = roi.shape[:2]
    x1 = min(w - 1, max(0, int(w * trim[0])))
    y1 = min(h - 1, max(0, int(h * trim[1])))
    x2 = max(x1 + 1, min(w, int(w * (1.0 - trim[2]))))
    y2 = max(y1 + 1, min(h, int(h * (1.0 - trim[3]))))
    return roi[y1:y2, x1:x2]


def _focused_barcode_roi(roi: np.ndarray) -> np.ndarray:
    if roi.size == 0:
        return roi

    h, w = roi.shape[:2]
    gx = cv2.Sobel(roi, cv2.CV_32F, 1, 0, ksize=3)
    col_score = np.mean(np.abs(gx), axis=0)
    row_score = np.mean(255 - roi, axis=1)

    x1, x2 = _active_score_span(col_score, min_width=max(12, w // 6))
    y1, y2 = _active_score_span(row_score, min_width=max(20, h // 3))

    pad_x = max(4, w // 30)
    pad_y = max(4, h // 30)
    x1 = max(0, x1 - pad_x)
    y1 = max(0, y1 - pad_y)
    x2 = min(w, x2 + pad_x)
    y2 = min(h, y2 + pad_y)
    return roi[y1:y2, x1:x2]


def _active_score_span(score: np.ndarray, min_width: int) -> tuple[int, int]:
    if score.size == 0 or not np.any(score > 0):
        return (0, score.size)

    threshold = max(float(np.percentile(score, 85)) * 0.6, float(np.max(score)) * 0.35)
    active = np.where(score >= threshold)[0]
    if active.size == 0:
        center = score.size // 2
        half = max(1, min_width // 2)
        return (max(0, center - half), min(score.size, center + half))

    groups = np.split(active, np.where(np.diff(active) > 2)[0] + 1)
    best_group = max(groups, key=lambda group: (group.size, float(np.mean(score[group]))))
    start = int(best_group[0])
    end = int(best_group[-1]) + 1
    if (end - start) < min_width:
        extra = min_width - (end - start)
        start = max(0, start - extra // 2)
        end = min(score.size, end + extra - extra // 2)
    return (start, end)


def _barcode_candidates(roi: np.ndarray, orientation: str) -> list[np.ndarray]:
    if roi.size == 0:
        return [roi]

    # Always try original + both 90° rotations to handle any orientation
    base_images = [
        roi,
        cv2.rotate(roi, cv2.ROTATE_90_CLOCKWISE),
        cv2.rotate(roi, cv2.ROTATE_90_COUNTERCLOCKWISE),
    ]

    candidates = []
    seen = set()
    scales = (1.0, 1.5, 2.0, 3.0)
    for base in base_images:
        variants = [
            base,
            _enhance(base),
            _adaptive_binary(base),
            cv2.bitwise_not(_adaptive_binary(base)),
            _morph_clean(base),
        ] + _morph_barcode_variants(base, orientation)
        for variant in variants:
            for scale in scales:
                candidate = _scale_image(variant, scale)
                key = (candidate.shape, int(np.mean(candidate)), int(np.std(candidate)))
                if key in seen:
                    continue
                seen.add(key)
                candidates.append(candidate)
    return candidates


def _morph_barcode_variants(img: np.ndarray, orientation: str) -> list[np.ndarray]:
    if img.size == 0:
        return []

    h, w = img.shape[:2]
    blur = cv2.GaussianBlur(img, (3, 3), 0)
    binary = _adaptive_binary(blur)
    inv_binary = cv2.bitwise_not(binary)

    long_x = max(9, w // 10)
    long_y = max(9, h // 10)
    kernels = []
    if orientation == "vertical":
        kernels.extend([
            cv2.getStructuringElement(cv2.MORPH_RECT, (1, long_y)),
            cv2.getStructuringElement(cv2.MORPH_RECT, (max(3, w // 30), long_y)),
            cv2.getStructuringElement(cv2.MORPH_RECT, (long_x, 1)),
        ])
    else:
        kernels.extend([
            cv2.getStructuringElement(cv2.MORPH_RECT, (long_x, 1)),
            cv2.getStructuringElement(cv2.MORPH_RECT, (long_x, max(3, h // 30))),
            cv2.getStructuringElement(cv2.MORPH_RECT, (1, long_y)),
        ])

    variants = []
    for kernel in kernels:
        closed = cv2.morphologyEx(inv_binary, cv2.MORPH_CLOSE, kernel)
        opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel)
        variants.append(cv2.bitwise_not(closed))
        variants.append(cv2.bitwise_not(opened))

    blackhat_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (max(9, w // 8), max(3, h // 24)),
    )
    blackhat = cv2.morphologyEx(blur, cv2.MORPH_BLACKHAT, blackhat_kernel)
    _, blackhat_bin = cv2.threshold(blackhat, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants.append(blackhat_bin)
    variants.append(cv2.bitwise_not(blackhat_bin))

    unique = []
    seen = set()
    for variant in variants:
        key = (variant.shape, int(np.mean(variant)), int(np.std(variant)))
        if key in seen:
            continue
        seen.add(key)
        unique.append(variant)
    return unique


def _enhance(img: np.ndarray) -> np.ndarray:
    """
    Sharpen + binarise for better barcode detection.
    """
    # Upscale if too small (barcodes need ≥ 1 px per bar module)
    min_dim = 200
    h, w = img.shape
    if min(h, w) < min_dim:
        scale = min_dim / min(h, w)
        img = cv2.resize(
            img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC
        )

    # CLAHE for contrast normalisation (handles over/under-exposed scans)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    img = clahe.apply(img)

    # Sharpen
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    img = cv2.filter2D(img, -1, kernel)

    # Binarise (Otsu)
    _, binary = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary


def _adaptive_binary(img: np.ndarray) -> np.ndarray:
    if img.size == 0:
        return img
    blur = cv2.GaussianBlur(img, (5, 5), 0)
    return cv2.adaptiveThreshold(
        blur,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        5,
    )


def _morph_clean(img: np.ndarray) -> np.ndarray:
    """Morphological cleanup to repair broken barcode bars."""
    if img.size == 0:
        return img
    # Upscale first for better morphology
    h, w = img.shape[:2]
    if min(h, w) < 300:
        scale = 300 / min(h, w)
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)
    # Binarize
    _, binary = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    binary = cv2.bitwise_not(binary)  # bars become white
    # Close gaps along horizontal bars
    kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (max(15, binary.shape[1] // 10), 1))
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_h)
    # Also try vertical bars (for rotated barcode)
    kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(15, binary.shape[0] // 10)))
    closed_v = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_v)
    # Return the one with more structure
    if np.std(closed) > np.std(closed_v):
        return cv2.bitwise_not(closed)
    return cv2.bitwise_not(closed_v)


def _scale_image(img: np.ndarray, scale: float) -> np.ndarray:
    if img.size == 0 or scale == 1.0:
        return img
    h, w = img.shape[:2]
    return cv2.resize(
        img,
        (max(1, int(w * scale)), max(1, int(h * scale))),
        interpolation=cv2.INTER_CUBIC,
    )
