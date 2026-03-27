from __future__ import annotations

from datetime import datetime

import numpy as np


def _iso_now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _clamp_conf(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _tier_to_room_confidence(tier: str) -> float:
    if tier == "metric":
        return 0.85
    if tier == "partial":
        return 0.6
    return 0.35


def _make_rect_walls(width: float, depth: float, confidence: float) -> list[dict]:
    return [
        {"id": "wall_north", "x1": 0.0, "z1": 0.0, "x2": width, "z2": 0.0, "confidence": confidence},
        {"id": "wall_south", "x1": 0.0, "z1": depth, "x2": width, "z2": depth, "confidence": confidence},
        {"id": "wall_east", "x1": width, "z1": 0.0, "x2": width, "z2": depth, "confidence": confidence},
        {"id": "wall_west", "x1": 0.0, "z1": 0.0, "x2": 0.0, "z2": depth, "confidence": confidence},
    ]


def _safe_float(value: object, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_points(raw: object) -> np.ndarray:
    try:
        arr = np.asarray(raw, dtype=np.float64)
        if arr.ndim == 2 and arr.shape[1] >= 3:
            arr = arr[:, :3]
            return arr[np.isfinite(arr).all(axis=1)]
    except Exception:
        pass
    return np.empty((0, 3), dtype=np.float64)


def _normalize_scene_object(raw: dict, idx: int, room_w: float, room_d: float) -> dict | None:
    size = raw.get("size", {})
    position = raw.get("position", {})

    w = _safe_float(size.get("w"), 0.0)
    h = _safe_float(size.get("h"), 0.0)
    d = _safe_float(size.get("d"), 0.0)
    if w <= 0.0 or h <= 0.0 or d <= 0.0:
        return None

    x = _safe_float(position.get("x"), 0.0)
    y = _safe_float(position.get("y"), 0.0)
    z = _safe_float(position.get("z"), 0.0)

    return {
        "id": str(raw.get("id") or f"obj_{idx:03d}"),
        "type": str(raw.get("type") or "unknown_furniture"),
        "type_confidence": _clamp_conf(_safe_float(raw.get("type_confidence"), 0.5)),
        "position_confidence": _clamp_conf(_safe_float(raw.get("position_confidence"), 0.5)),
        "size_confidence": _clamp_conf(_safe_float(raw.get("size_confidence"), 0.5)),
        "rotation_confidence": _clamp_conf(_safe_float(raw.get("rotation_confidence"), 0.35)),
        "label_confirmed": bool(raw.get("label_confirmed", False)),
        "position": {
            "x": max(0.0, min(x, room_w)),
            "y": y,
            "z": max(0.0, min(z, room_d)),
        },
        "size": {
            "w": max(0.1, min(w, room_w)),
            "h": max(0.1, h),
            "d": max(0.1, min(d, room_d)),
        },
        "rotation_y": _safe_float(raw.get("rotation_y"), 0.0),
        "color": raw.get("color"),
        "product_url": raw.get("product_url"),
        "product_name": raw.get("product_name"),
    }


def _normalize_opening(raw: dict, idx: int, opening_prefix: str, room_w: float) -> dict | None:
    width = _safe_float(raw.get("width"), 0.0)
    height = _safe_float(raw.get("height"), 0.0)
    if width <= 0.0 or height <= 0.0:
        return None

    return {
        "id": str(raw.get("id") or f"{opening_prefix}_{idx:03d}"),
        "wall": str(raw.get("wall") or "wall_north"),
        "x": max(0.0, min(_safe_float(raw.get("x"), 0.0), room_w)),
        "width": max(0.1, width),
        "height": max(0.1, height),
        "sill_height": max(0.0, _safe_float(raw.get("sill_height"), 0.0)),
        "confidence": _clamp_conf(_safe_float(raw.get("confidence"), 0.5)),
        "user_confirmed": bool(raw.get("user_confirmed", False)),
    }


def collect_m2_warnings(m2_result: dict) -> list[str]:
    diagnostics = m2_result.get("diagnostics", {}) if isinstance(m2_result, dict) else {}
    fused_objects = _safe_int(diagnostics.get("fused_objects"), -1)
    num_detection_frames = _safe_int(m2_result.get("num_detection_frames"), 0)

    warnings: list[str] = []
    if num_detection_frames == 0:
        warnings.append("No object detections found in M2. Try brighter frames with more visible furniture.")
    if fused_objects == 0:
        warnings.append("M2 produced no fused objects. You can still add objects manually in Design.")
    return warnings


def _estimate_room_dims(
    estimated_spans: dict,
    tier: str,
    registration_ratio: float,
    num_sparse_points: int,
) -> tuple[float, float]:
    width = _safe_float(estimated_spans.get("x"), 0.0)
    depth = _safe_float(estimated_spans.get("z"), 0.0)

    # If scan quality is poor, treat spans as unreliable and fall back to pragmatic defaults.
    if tier == "approximate" and (registration_ratio < 0.2 or num_sparse_points < 120):
        return 4.5, 5.2

    if width <= 0.0 or depth <= 0.0:
        return 4.5, 5.2

    # Bound extreme values to realistic indoor room ranges.
    width = max(2.0, min(width, 9.0))
    depth = max(2.0, min(depth, 12.0))
    return width, depth


def _cluster_sparse_points_to_objects(points: np.ndarray, room_w: float, room_d: float) -> list[dict]:
    """Generate coarse object proposals from sparse aligned points.

    This is a stopgap for M1 so users can get non-empty scenes when sparse data is sufficient.
    """
    if len(points) < 120:
        return []

    y_floor = float(np.percentile(points[:, 1], 5))
    pts = points[(points[:, 1] > y_floor + 0.15) & (points[:, 1] < y_floor + 2.5)]
    if len(pts) < 60:
        return []

    # Keep points near inferred room bounds.
    pts = pts[(pts[:, 0] >= -0.5) & (pts[:, 0] <= room_w + 0.5) & (pts[:, 2] >= -0.5) & (pts[:, 2] <= room_d + 0.5)]
    if len(pts) < 60:
        return []

    voxel = 0.35
    gx = np.floor(pts[:, 0] / voxel).astype(int)
    gz = np.floor(pts[:, 2] / voxel).astype(int)
    grid = np.stack([gx, gz], axis=1)

    cell_to_indices: dict[tuple[int, int], list[int]] = {}
    for idx, (cx, cz) in enumerate(grid):
        key = (int(cx), int(cz))
        cell_to_indices.setdefault(key, []).append(idx)

    dense_cells = {k for k, idxs in cell_to_indices.items() if len(idxs) >= 4}
    if not dense_cells:
        return []

    # BFS cluster neighboring dense cells.
    visited: set[tuple[int, int]] = set()
    clusters: list[list[tuple[int, int]]] = []
    neighbors = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

    for cell in dense_cells:
        if cell in visited:
            continue
        queue = [cell]
        visited.add(cell)
        cluster_cells = []
        while queue:
            cur = queue.pop()
            cluster_cells.append(cur)
            for dx, dz in neighbors:
                nxt = (cur[0] + dx, cur[1] + dz)
                if nxt in dense_cells and nxt not in visited:
                    visited.add(nxt)
                    queue.append(nxt)
        clusters.append(cluster_cells)

    objects: list[dict] = []
    obj_counter = 1
    for cluster in clusters:
        cluster_indices: list[int] = []
        for cell in cluster:
            cluster_indices.extend(cell_to_indices.get(cell, []))

        if len(cluster_indices) < 12:
            continue
        p = pts[np.asarray(cluster_indices, dtype=int)]
        min_b = p.min(axis=0)
        max_b = p.max(axis=0)

        w = float(max_b[0] - min_b[0])
        h = float(max_b[1] - min_b[1])
        d = float(max_b[2] - min_b[2])

        if not (0.25 <= w <= 3.5 and 0.25 <= d <= 3.5 and 0.25 <= h <= 2.5):
            continue

        cx = float((min_b[0] + max_b[0]) * 0.5)
        cz = float((min_b[2] + max_b[2]) * 0.5)
        confidence = _clamp_conf(min(0.65, 0.25 + len(cluster_indices) / 120.0))

        objects.append(
            {
                "id": f"obj_{obj_counter:03d}",
                "type": "unknown_furniture",
                "type_confidence": confidence,
                "position_confidence": confidence,
                "size_confidence": confidence,
                "rotation_confidence": 0.35,
                "label_confirmed": False,
                "position": {
                    "x": max(0.0, min(cx, room_w)),
                    "y": 0.0,
                    "z": max(0.0, min(cz, room_d)),
                },
                "size": {
                    "w": max(0.2, min(w, room_w)),
                    "h": max(0.2, h),
                    "d": max(0.2, min(d, room_d)),
                },
                "rotation_y": 0.0,
                "color": None,
                "product_url": None,
                "product_name": None,
            }
        )
        obj_counter += 1

    return objects[:12]


def collect_m1_warnings(m1_summary: dict, m1_aligned_payload: dict) -> list[str]:
    alignment = m1_summary.get("alignment", {})
    quality = alignment.get("quality") or m1_aligned_payload.get("quality", {})

    ratio = _safe_float(quality.get("registration_ratio"), 0.0)
    sparse_points = int(_safe_float(quality.get("num_sparse_points"), 0.0))
    num_registered = int(_safe_float(quality.get("num_images_registered"), 0.0))

    warnings: list[str] = []
    if ratio < 0.1:
        warnings.append("Very low registration ratio (<10%). Re-scan slowly with better overlap and lighting.")
    elif ratio < 0.3:
        warnings.append("Partial registration quality. Room scale may be approximate.")

    if sparse_points < 100:
        warnings.append("Sparse reconstruction has too few points for object proposals.")

    if num_registered < 4:
        warnings.append("Too few camera poses registered. Try a longer, slower room walk.")

    return warnings


def determine_pipeline_tier(num_registered: int, total_frames: int, sparse_points: int) -> str:
    if total_frames <= 0:
        return "approximate"

    ratio = num_registered / total_frames
    if ratio >= 0.7 and sparse_points >= 2000:
        return "metric"
    if ratio >= 0.3 and sparse_points >= 500:
        return "partial"
    return "approximate"


def build_scene_from_precomputed(scene: dict) -> dict:
    # Reserved for enrichment and normalization of precomputed scene assets.
    return scene


def build_scene_from_m1(
    session_id: str,
    m1_summary: dict,
    m1_aligned_payload: dict,
) -> dict:
    """Create a valid SceneScript v2 from Milestone 1 reconstruction output.

    M1 does not include object detections yet, so `objects` is intentionally empty.
    """
    alignment = m1_summary.get("alignment", {})
    quality = alignment.get("quality", {})

    tier = alignment.get("pipeline_tier") or m1_aligned_payload.get("pipeline_tier") or "approximate"
    if tier not in {"metric", "partial", "approximate"}:
        tier = "approximate"

    estimated_spans = alignment.get("estimated_spans") or m1_aligned_payload.get("estimated_spans") or {}

    floor_inlier_ratio = float(
        alignment.get("floor_plane_inlier_ratio")
        or m1_aligned_payload.get("floor_plane_inlier_ratio")
        or 0.0
    )
    room_conf = _tier_to_room_confidence(tier)
    floor_conf = _clamp_conf((room_conf + floor_inlier_ratio) / 2.0)

    now = _iso_now()

    registration_ratio = float(
        quality.get("registration_ratio")
        or m1_aligned_payload.get("quality", {}).get("registration_ratio")
        or 0.0
    )
    num_sparse_points = int(
        quality.get("num_sparse_points")
        or m1_aligned_payload.get("quality", {}).get("num_sparse_points")
        or 0
    )

    width, depth = _estimate_room_dims(
        estimated_spans=estimated_spans,
        tier=tier,
        registration_ratio=registration_ratio,
        num_sparse_points=num_sparse_points,
    )

    sparse_points = _coerce_points(m1_aligned_payload.get("aligned_sparse_points", []))
    objects = _cluster_sparse_points_to_objects(sparse_points, width, depth)

    scene = {
        "version": 2,
        "session_id": session_id,
        "source": "m1_colmap",
        "pipeline_mode": "colmap_m1",
        "room": {
            "width": width,
            "width_confidence": room_conf,
            "depth": depth,
            "depth_confidence": room_conf,
            "height": 2.8,
            "height_confidence": 0.45,
            "floor_plane": [0.0, 1.0, 0.0, 0.0],
            "floor_plane_inlier_ratio": _clamp_conf(floor_inlier_ratio),
        },
        "walls": _make_rect_walls(width, depth, confidence=floor_conf),
        "windows": [],
        "doors": [],
        "objects": objects,
        "metadata": {
            "room_type": None,
            "room_type_confidence": 0.2,
            "pipeline_version": "m1_colmap_v1",
            "confidence": tier,
            "created_at": now,
            "last_edited": now,
            "m1_registration_ratio": registration_ratio,
            "m1_num_images_registered": int(quality.get("num_images_registered", 0)),
            "m1_num_frames": int(quality.get("num_frames", 0)),
            "m1_num_sparse_points": int(quality.get("num_sparse_points", 0)),
        },
    }
    return scene


def build_scene_from_m2(
    session_id: str,
    m1_summary: dict,
    m1_aligned_payload: dict,
    m2_result: dict,
) -> dict:
    """Create SceneScript using M1 geometry and M2 object/opening extraction outputs."""
    scene = build_scene_from_m1(
        session_id=session_id,
        m1_summary=m1_summary,
        m1_aligned_payload=m1_aligned_payload,
    )

    geometry = m2_result.get("geometry", {}) if isinstance(m2_result, dict) else {}
    room_dims = geometry.get("room_dimensions", {}) if isinstance(geometry, dict) else {}

    base_w = _safe_float(scene["room"].get("width"), 4.5)
    base_d = _safe_float(scene["room"].get("depth"), 5.2)
    base_h = _safe_float(scene["room"].get("height"), 2.8)

    m2_w = _safe_float(room_dims.get("width"), base_w)
    m2_d = _safe_float(room_dims.get("depth"), base_d)
    m2_h = _safe_float(room_dims.get("height"), base_h)

    room_w = max(2.0, min(m2_w, 12.0))
    room_d = max(2.0, min(m2_d, 16.0))
    room_h = max(2.2, min(m2_h, 5.0))

    scene["room"]["width"] = room_w
    scene["room"]["depth"] = room_d
    scene["room"]["height"] = room_h
    scene["room"]["width_confidence"] = _clamp_conf(max(_safe_float(scene["room"].get("width_confidence"), 0.35), 0.55))
    scene["room"]["depth_confidence"] = _clamp_conf(max(_safe_float(scene["room"].get("depth_confidence"), 0.35), 0.55))
    scene["room"]["height_confidence"] = _clamp_conf(max(_safe_float(scene["room"].get("height_confidence"), 0.35), 0.5))

    floor_plane = geometry.get("floor_plane") if isinstance(geometry, dict) else None
    if isinstance(floor_plane, list) and len(floor_plane) >= 4:
        scene["room"]["floor_plane"] = [
            _safe_float(floor_plane[0], 0.0),
            _safe_float(floor_plane[1], 1.0),
            _safe_float(floor_plane[2], 0.0),
            _safe_float(floor_plane[3], 0.0),
        ]

    scene["walls"] = _make_rect_walls(room_w, room_d, confidence=0.65)

    raw_objects = m2_result.get("objects", []) if isinstance(m2_result, dict) else []
    objects: list[dict] = []
    for idx, raw in enumerate(raw_objects, start=1):
        if not isinstance(raw, dict):
            continue
        obj = _normalize_scene_object(raw, idx=idx, room_w=room_w, room_d=room_d)
        if obj is not None:
            objects.append(obj)

    raw_windows = m2_result.get("windows", []) if isinstance(m2_result, dict) else []
    windows: list[dict] = []
    for idx, raw in enumerate(raw_windows, start=1):
        if not isinstance(raw, dict):
            continue
        opening = _normalize_opening(raw, idx=idx, opening_prefix="window", room_w=room_w)
        if opening is not None:
            windows.append(opening)

    raw_doors = m2_result.get("doors", []) if isinstance(m2_result, dict) else []
    doors: list[dict] = []
    for idx, raw in enumerate(raw_doors, start=1):
        if not isinstance(raw, dict):
            continue
        opening = _normalize_opening(raw, idx=idx, opening_prefix="door", room_w=room_w)
        if opening is not None:
            doors.append(opening)

    scene["objects"] = objects
    scene["windows"] = windows
    scene["doors"] = doors
    scene["source"] = "m2_offline"
    scene["pipeline_mode"] = "m2_offline_minimal"
    scene["metadata"]["pipeline_version"] = "m2_offline_minimal_v1"

    m1_tier = str(scene.get("metadata", {}).get("confidence", "approximate"))
    if objects:
        scene["metadata"]["confidence"] = "partial" if m1_tier == "approximate" else m1_tier

    diagnostics = m2_result.get("diagnostics", {}) if isinstance(m2_result, dict) else {}
    scene["metadata"]["m2_processed_frames"] = _safe_int(m2_result.get("processed_frames"), 0)
    scene["metadata"]["m2_detection_frames"] = _safe_int(m2_result.get("num_detection_frames"), 0)
    scene["metadata"]["m2_fused_objects"] = _safe_int(diagnostics.get("fused_objects"), len(objects))

    return scene
