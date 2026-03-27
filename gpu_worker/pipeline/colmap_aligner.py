from __future__ import annotations

import math

import numpy as np


def _compute_rotation_to_up(normal: np.ndarray, up: np.ndarray) -> np.ndarray:
    normal = normal / (np.linalg.norm(normal) + 1e-12)
    up = up / (np.linalg.norm(up) + 1e-12)

    v = np.cross(normal, up)
    c = float(np.dot(normal, up))
    s = np.linalg.norm(v)

    if s < 1e-9:
        return np.eye(3)

    vx = np.array(
        [
            [0.0, -v[2], v[1]],
            [v[2], 0.0, -v[0]],
            [-v[1], v[0], 0.0],
        ],
        dtype=np.float64,
    )
    return np.eye(3) + vx + (vx @ vx) * ((1 - c) / (s * s))


def _estimate_floor_plane(points: np.ndarray) -> tuple[np.ndarray, float]:
    try:
        import open3d as o3d  # optional

        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points)
        plane, inliers = pcd.segment_plane(distance_threshold=0.05, ransac_n=3, num_iterations=1000)
        normal = np.array(plane[:3], dtype=np.float64)
        inlier_ratio = float(len(inliers) / max(1, len(points)))
        return normal, inlier_ratio
    except Exception:
        # Fallback: assume reconstruction is roughly gravity-aligned.
        return np.array([0.0, 1.0, 0.0], dtype=np.float64), 0.0


def classify_pipeline_tier(
    num_images_registered: int,
    num_frames: int,
    num_sparse_points: int,
    metric_ratio_threshold: float = 0.70,
    partial_ratio_threshold: float = 0.30,
    min_sparse_points_metric: int = 2000,
    min_sparse_points_partial: int = 500,
) -> str:
    if num_frames <= 0:
        return "approximate"
    ratio = num_images_registered / num_frames
    if ratio >= metric_ratio_threshold and num_sparse_points >= min_sparse_points_metric:
        return "metric"
    if ratio >= partial_ratio_threshold and num_sparse_points >= min_sparse_points_partial:
        return "partial"
    return "approximate"


def align_colmap_output(colmap_result: dict, room_width: float, room_depth: float) -> dict:
    """Align sparse reconstruction to SceneScript coordinates and metric scale.

    This alignment is percentile-based and robust to sparse outliers.
    """
    sparse_points_raw = colmap_result.get("sparse_points", [])
    if not sparse_points_raw:
        raise ValueError("colmap_result does not include sparse_points")

    points = np.asarray(sparse_points_raw, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError("sparse_points must be shape (N, 3)")

    floor_normal, floor_inlier_ratio = _estimate_floor_plane(points)
    if floor_normal[1] < 0:
        floor_normal = -floor_normal

    up = np.array([0.0, 1.0, 0.0], dtype=np.float64)
    R_align = _compute_rotation_to_up(floor_normal, up)
    points_aligned = (R_align @ points.T).T

    floor_height = float(np.percentile(points_aligned[:, 1], 5))
    points_aligned[:, 1] -= floor_height

    near_floor_mask = points_aligned[:, 1] < max(0.3, np.percentile(points_aligned[:, 1], 20))
    floor_points = points_aligned[near_floor_mask]
    if len(floor_points) < 50:
        floor_points = points_aligned

    x_span = float(np.percentile(floor_points[:, 0], 95) - np.percentile(floor_points[:, 0], 5))
    z_span = float(np.percentile(floor_points[:, 2], 95) - np.percentile(floor_points[:, 2], 5))

    spans = sorted([x_span, z_span])
    dims = sorted([float(room_width), float(room_depth)])

    scales = []
    for span, dim in zip(spans, dims):
        if span > 1e-3 and dim > 1e-3:
            scales.append(dim / span)
    scale = float(np.median(scales)) if scales else 1.0

    points_scaled = points_aligned * scale
    x0 = float(np.percentile(points_scaled[:, 0], 5))
    z0 = float(np.percentile(points_scaled[:, 2], 5))
    points_scaled[:, 0] -= x0
    points_scaled[:, 2] -= z0

    aligned_camera_poses: dict[str, dict] = {}
    for frame_name, pose in colmap_result.get("camera_poses", {}).items():
        R = np.asarray(pose["R"], dtype=np.float64)
        t = np.asarray(pose["t"], dtype=np.float64)

        # Keep world-to-camera representation and align camera translation to scaled world frame.
        R_new = R @ R_align.T
        t_new = t * scale
        t_new[1] -= floor_height * scale
        t_new[0] -= x0
        t_new[2] -= z0

        aligned_camera_poses[frame_name] = {
            **pose,
            "R": R_new.tolist(),
            "t": t_new.tolist(),
        }

    num_frames = int(colmap_result.get("num_frames", 0))
    num_images_registered = int(colmap_result.get("num_images_registered", 0))
    num_sparse_points = int(colmap_result.get("num_sparse_points", len(points)))
    pipeline_tier = classify_pipeline_tier(num_images_registered, num_frames, num_sparse_points)

    return {
        "aligned": True,
        "camera_poses": aligned_camera_poses,
        "scale_factor": scale,
        "rotation_align": R_align.tolist(),
        "floor_offset": floor_height,
        "origin_offset": {"x": x0, "z": z0},
        "floor_plane_inlier_ratio": floor_inlier_ratio,
        "aligned_sparse_points": points_scaled.tolist(),
        "estimated_spans": {"x": x_span * scale, "z": z_span * scale},
        "pipeline_tier": pipeline_tier,
        "quality": {
            "num_frames": num_frames,
            "num_images_registered": num_images_registered,
            "registration_ratio": (num_images_registered / num_frames) if num_frames else 0.0,
            "num_sparse_points": num_sparse_points,
        },
    }
