from __future__ import annotations

import numpy as np


def _euclidean_2d(a: dict, b: dict) -> float:
    ax, az = a["position"]["x"], a["position"]["z"]
    bx, bz = b["position"]["x"], b["position"]["z"]
    return float(np.hypot(ax - bx, az - bz))


def _size_similarity(a: dict, b: dict) -> float:
    aw, ad = a["size"]["w"], a["size"]["d"]
    bw, bd = b["size"]["w"], b["size"]["d"]
    sw = min(aw, bw) / max(aw, bw, 1e-6)
    sd = min(ad, bd) / max(ad, bd, 1e-6)
    return float((sw + sd) * 0.5)


def _can_merge(a: dict, b: dict) -> bool:
    dist = _euclidean_2d(a, b)
    sim = _size_similarity(a, b)
    label_match = a.get("label") == b.get("label")
    return dist < 0.9 and (label_match or sim > 0.55)


def _merge_group(group: list[dict], object_idx: int) -> dict:
    weights = np.array([max(0.1, g.get("confidence", 0.3)) * max(1, g.get("num_points", 1)) for g in group], dtype=np.float64)
    weights /= weights.sum()

    pos_x = float(np.sum([w * g["position"]["x"] for w, g in zip(weights, group)]))
    pos_z = float(np.sum([w * g["position"]["z"] for w, g in zip(weights, group)]))
    size_w = float(np.sum([w * g["size"]["w"] for w, g in zip(weights, group)]))
    size_h = float(max(g["size"]["h"] for g in group))
    size_d = float(np.sum([w * g["size"]["d"] for w, g in zip(weights, group)]))

    labels = [g.get("label", "unknown_furniture") for g in group]
    best_label = max(set(labels), key=labels.count)

    if len(group) == 1:
        pos_conf = 0.45
    else:
        std_x = np.std([g["position"]["x"] for g in group])
        std_z = np.std([g["position"]["z"] for g in group])
        pos_conf = float(np.clip(1.0 - (std_x + std_z) / 0.6, 0.3, 0.9))

    type_conf = float(np.clip(np.mean([g.get("confidence", 0.3) for g in group]), 0.2, 0.95))
    size_conf = float(np.clip(min(0.9, 0.35 + len(group) * 0.1), 0.35, 0.9))

    return {
        "id": f"obj_{object_idx:03d}",
        "type": best_label,
        "type_confidence": type_conf,
        "position_confidence": pos_conf,
        "size_confidence": size_conf,
        "rotation_confidence": 0.35,
        "label_confirmed": False,
        "position": {"x": pos_x, "y": 0.0, "z": pos_z},
        "size": {"w": max(0.2, size_w), "h": max(0.2, size_h), "d": max(0.2, size_d)},
        "rotation_y": 0.0,
        "color": None,
        "product_url": None,
        "product_name": None,
        "source_frames": sorted({g.get("frame", "") for g in group if g.get("frame")}),
        "num_observations": len(group),
    }


def fuse_per_frame_objects(per_frame_objects: list[list[dict]]) -> list[dict]:
    all_candidates: list[dict] = []
    for frame_set in per_frame_objects:
        all_candidates.extend(frame_set)

    if not all_candidates:
        return []

    groups: list[list[dict]] = []
    for cand in all_candidates:
        merged = False
        for group in groups:
            if any(_can_merge(cand, existing) for existing in group):
                group.append(cand)
                merged = True
                break
        if not merged:
            groups.append([cand])

    objects: list[dict] = []
    for i, group in enumerate(groups, start=1):
        obj = _merge_group(group, object_idx=i)
        objects.append(obj)

    return objects
