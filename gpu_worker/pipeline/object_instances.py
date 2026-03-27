from __future__ import annotations

import numpy as np


def _bbox_to_mask(bbox: list[float], h: int, w: int) -> np.ndarray:
    x1, y1, x2, y2 = [int(round(v)) for v in bbox]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    mask = np.zeros((h, w), dtype=bool)
    if x2 > x1 and y2 > y1:
        mask[y1:y2, x1:x2] = True
    return mask


def _percentile_clip(values: np.ndarray, low: float = 5.0, high: float = 95.0) -> tuple[float, float]:
    if values.size == 0:
        return 0.1, 12.0
    lo = float(np.percentile(values, low))
    hi = float(np.percentile(values, high))
    if hi <= lo:
        hi = lo + 1e-3
    return lo, hi

def lift_detections_to_3d(detections: list[dict], depth_metric, camera_pose: dict, frame_name: str) -> list[dict]:
    depth = np.asarray(depth_metric, dtype=np.float32)
    if depth.ndim != 2:
        return []

    h, w = depth.shape
    K = camera_pose["intrinsics"]
    fx, fy = float(K["fx"]), float(K["fy"])
    cx, cy = float(K["cx"]), float(K["cy"])
    R = np.asarray(camera_pose["R"], dtype=np.float64)
    t = np.asarray(camera_pose["t"], dtype=np.float64)

    u_coords, v_coords = np.meshgrid(np.arange(w), np.arange(h))
    candidates: list[dict] = []

    for idx, det in enumerate(detections):
        mask = det.get("mask")
        if mask is None:
            mask = _bbox_to_mask(det.get("bbox", [0, 0, 0, 0]), h, w)
        else:
            mask = np.asarray(mask, dtype=bool)
            if mask.shape != (h, w):
                mask = _bbox_to_mask(det.get("bbox", [0, 0, 0, 0]), h, w)

        valid = mask & np.isfinite(depth) & (depth > 0.1) & (depth < 12.0)
        if valid.sum() < 25:
            continue

        dvals = depth[valid]
        lo, hi = _percentile_clip(dvals)
        valid &= (depth >= lo) & (depth <= hi)
        if valid.sum() < 20:
            continue

        # Subsample for speed and stability.
        sel = np.flatnonzero(valid)
        if sel.size > 3500:
            step = max(1, sel.size // 3500)
            sel = sel[::step]

        z = depth.reshape(-1)[sel]
        u = u_coords.reshape(-1)[sel]
        v = v_coords.reshape(-1)[sel]

        x_cam = (u - cx) * z / fx
        y_cam = (v - cy) * z / fy
        pts_cam = np.stack([x_cam, y_cam, z], axis=1)

        # COLMAP world conversion: X_world = R^T * (X_cam - t)
        pts_world = (R.T @ (pts_cam - t).T).T
        pts_world[:, 1] *= -1.0  # convert to y-up world

        min_b = pts_world.min(axis=0)
        max_b = pts_world.max(axis=0)
        size_w = float(max_b[0] - min_b[0])
        size_h = float(max_b[1] - min_b[1])
        size_d = float(max_b[2] - min_b[2])

        if size_w <= 0.05 or size_d <= 0.05 or size_h <= 0.05:
            continue

        center_x = float((min_b[0] + max_b[0]) * 0.5)
        center_z = float((min_b[2] + max_b[2]) * 0.5)

        candidates.append(
            {
                "candidate_id": f"cand_{frame_name}_{idx:03d}",
                "label": str(det.get("label", "unknown_furniture")),
                "confidence": float(det.get("confidence", 0.4)),
                "frame": frame_name,
                "sam_mask_id": det.get("mask_id", f"mask_{idx:03d}"),
                "position": {"x": center_x, "y": 0.0, "z": center_z},
                "size": {"w": size_w, "h": size_h, "d": size_d},
                "num_points": int(pts_world.shape[0]),
                "points_world": pts_world,
            }
        )

    return candidates
