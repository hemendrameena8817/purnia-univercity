import cv2
import numpy as np


def locate_content_frame(gray: np.ndarray) -> tuple[int, int, int, int]:
    if gray.size == 0:
        return (0, 0, 0, 0)

    h, w = gray.shape
    binary = cv2.adaptiveThreshold(
        cv2.GaussianBlur(gray, (5, 5), 0),
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        31,
        8,
    )
    col_density = np.count_nonzero(binary, axis=0) / max(h, 1)
    row_density = np.count_nonzero(binary, axis=1) / max(w, 1)
    x1, x2 = _active_span(col_density, w, min_fraction=0.65)
    y1, y2 = _active_span(row_density, h, min_fraction=0.65)
    return (x1, y1, x2, y2)


def resolve_roi_bounds(
    gray: np.ndarray,
    roi_rel: tuple[float, float, float, float],
    content_frame: tuple[int, int, int, int] | None = None,
) -> tuple[int, int, int, int]:
    h, w = gray.shape
    if content_frame is None:
        fx1, fy1, fx2, fy2 = 0, 0, w, h
    else:
        fx1, fy1, fx2, fy2 = content_frame
        if fx2 <= fx1 or fy2 <= fy1:
            fx1, fy1, fx2, fy2 = 0, 0, w, h

    frame_w = fx2 - fx1
    frame_h = fy2 - fy1
    x1r, y1r, x2r, y2r = roi_rel
    x1 = max(0, min(w, fx1 + int(x1r * frame_w)))
    y1 = max(0, min(h, fy1 + int(y1r * frame_h)))
    x2 = max(x1, min(w, fx1 + int(x2r * frame_w)))
    y2 = max(y1, min(h, fy1 + int(y2r * frame_h)))
    return (x1, y1, x2, y2)


def crop_roi(
    gray: np.ndarray,
    roi_rel: tuple[float, float, float, float],
    content_frame: tuple[int, int, int, int] | None = None,
) -> np.ndarray:
    x1, y1, x2, y2 = resolve_roi_bounds(gray, roi_rel, content_frame)
    return gray[y1:y2, x1:x2]


def _active_span(density: np.ndarray, length: int, min_fraction: float) -> tuple[int, int]:
    if density.size == 0 or not np.any(density):
        return (0, length)

    window = max(5, density.size // 80)
    kernel = np.ones(window, dtype=np.float32) / window
    smooth = np.convolve(density.astype(np.float32), kernel, mode="same")
    threshold = max(float(np.percentile(smooth, 85)) * 0.35, 0.01)
    active = np.where(smooth >= threshold)[0]
    if active.size == 0:
        return (0, length)

    start = int(active[0])
    end = int(active[-1]) + 1
    pad = max(3, length // 100)
    start = max(0, start - pad)
    end = min(length, end + pad)
    if (end - start) < int(length * min_fraction):
        return (0, length)
    return (start, end)
