from __future__ import annotations

import cv2
import numpy as np


def _label_from_shape(w: int, h: int, area_ratio: float) -> str:
    aspect = w / max(h, 1)
    if h > w * 1.6 and area_ratio < 0.08:
        return "plant"
    if aspect > 1.8 and h < 220:
        return "tv_unit"
    if 1.2 < aspect <= 2.4 and h >= 200:
        return "sofa"
    if 0.8 <= aspect <= 1.4 and area_ratio > 0.02:
        return "table"
    if aspect < 0.8 and h > 260:
        return "bookshelf"
    return "unknown_furniture"


def _confidence_from_area(area_ratio: float, solidity: float) -> float:
    conf = 0.35 + min(0.45, area_ratio * 3.0) + min(0.2, max(0.0, solidity - 0.6))
    return float(max(0.1, min(0.95, conf)))

def detect_objects(image_path: str) -> list[dict]:
    image = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(f"Image not found: {image_path}")

    h, w = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Combine edge and foreground-like segmentation from adaptive threshold.
    edges = cv2.Canny(gray, 65, 150)
    thresh = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        31,
        8,
    )
    mask = cv2.bitwise_or(edges, thresh)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    detections: list[dict] = []
    min_area = h * w * 0.005
    max_area = h * w * 0.60

    for contour in contours:
        area = float(cv2.contourArea(contour))
        if area < min_area or area > max_area:
            continue

        x, y, bw, bh = cv2.boundingRect(contour)
        if bw < 20 or bh < 20:
            continue

        hull = cv2.convexHull(contour)
        hull_area = float(cv2.contourArea(hull))
        solidity = area / max(hull_area, 1.0)
        area_ratio = area / float(h * w)

        label = _label_from_shape(bw, bh, area_ratio)
        confidence = _confidence_from_area(area_ratio, solidity)

        obj_mask = np.zeros((h, w), dtype=np.uint8)
        cv2.drawContours(obj_mask, [contour], contourIdx=-1, color=255, thickness=-1)

        detections.append(
            {
                "label": label,
                "confidence": confidence,
                "bbox": [float(x), float(y), float(x + bw), float(y + bh)],
                "mask": obj_mask.astype(bool),
                "mask_id": f"mask_{len(detections):03d}",
            }
        )

    detections.sort(key=lambda d: d["confidence"], reverse=True)
    return detections[:20]
