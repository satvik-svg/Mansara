from __future__ import annotations


def _matches_opening(label: str, opening_type: str) -> bool:
    ll = label.lower()
    if opening_type == "window":
        return "window" in ll
    if opening_type == "door":
        return "door" in ll or "doorway" in ll
    return False


def _merge_candidates(candidates: list[dict], conf_threshold: float = 0.45) -> list[dict]:
    selected: list[dict] = []
    for cand in sorted(candidates, key=lambda c: c["confidence"], reverse=True):
        if cand["confidence"] < conf_threshold:
            continue
        keep = True
        cx, cy = cand["center"]
        for s in selected:
            sx, sy = s["center"]
            if abs(cx - sx) < 40 and abs(cy - sy) < 40:
                keep = False
                break
        if keep:
            selected.append(cand)
    return selected


def extract_openings(detections_by_frame: dict, opening_type: str) -> list[dict]:
    candidates: list[dict] = []

    for frame_name, detections in detections_by_frame.items():
        for det in detections:
            label = str(det.get("label", ""))
            if not _matches_opening(label, opening_type):
                continue
            x1, y1, x2, y2 = [float(v) for v in det.get("bbox", [0, 0, 0, 0])]
            center = ((x1 + x2) * 0.5, (y1 + y2) * 0.5)
            candidates.append(
                {
                    "frame": frame_name,
                    "label": label,
                    "confidence": float(det.get("confidence", 0.3)),
                    "bbox": [x1, y1, x2, y2],
                    "center": center,
                }
            )

    merged = _merge_candidates(candidates)
    openings = []
    for i, cand in enumerate(merged, start=1):
        x1, y1, x2, y2 = cand["bbox"]
        openings.append(
            {
                "id": f"{opening_type}_{i:03d}",
                "wall": "wall_north",
                "x": 0.0,
                "width": max(0.3, (x2 - x1) / 300.0),
                "height": max(0.4, (y2 - y1) / 300.0),
                "sill_height": 0.9 if opening_type == "window" else 0.0,
                "confidence": cand["confidence"],
                "user_confirmed": False,
                "detected_by": "m2_minimal",
            }
        )

    return openings
