from __future__ import annotations

import numpy as np


def _to_points_array(pointclouds: list) -> np.ndarray:
    arrays = []
    for p in pointclouds:
        arr = np.asarray(p, dtype=np.float64)
        if arr.ndim == 2 and arr.shape[1] >= 3:
            arrays.append(arr[:, :3])
    if not arrays:
        return np.empty((0, 3), dtype=np.float64)
    merged = np.concatenate(arrays, axis=0)
    return merged[np.isfinite(merged).all(axis=1)]


def fuse_geometry(pointclouds: list) -> dict:
    """Estimate room geometry from merged 3D points."""
    points = _to_points_array(pointclouds)
    if len(points) == 0:
        return {
            "floor_plane": [0.0, 1.0, 0.0, 0.0],
            "wall_planes": [],
            "room_dimensions": {"width": 4.5, "depth": 5.2, "height": 2.8},
            "num_points": 0,
        }

    x_min, y_min, z_min = np.percentile(points, [5, 5, 5], axis=0)
    x_max, y_max, z_max = np.percentile(points, [95, 95, 95], axis=0)
    width = float(max(2.0, x_max - x_min))
    depth = float(max(2.0, z_max - z_min))
    height = float(max(2.2, y_max - y_min))

    floor_plane = [0.0, 1.0, 0.0, float(-y_min)]
    wall_planes = [
        {"id": "wall_west", "equation": [1.0, 0.0, 0.0, float(-x_min)]},
        {"id": "wall_east", "equation": [-1.0, 0.0, 0.0, float(x_max)]},
        {"id": "wall_north", "equation": [0.0, 0.0, 1.0, float(-z_min)]},
        {"id": "wall_south", "equation": [0.0, 0.0, -1.0, float(z_max)]},
    ]

    return {
        "floor_plane": floor_plane,
        "wall_planes": wall_planes,
        "room_dimensions": {"width": width, "depth": depth, "height": height},
        "num_points": int(len(points)),
    }
