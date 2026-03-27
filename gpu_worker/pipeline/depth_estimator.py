from __future__ import annotations

import cv2
import numpy as np


class DepthEstimator:
    """Lightweight depth estimator for M2 minimal pipeline.

    This does not use a heavy model; it produces a stable relative depth prior and
    then aligns it to metric using sparse COLMAP points when available.
    """

    def predict_relative(self, image_path: str) -> np.ndarray:
        image = cv2.imread(image_path, cv2.IMREAD_COLOR)
        if image is None:
            raise FileNotFoundError(f"Image not found: {image_path}")

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
        h, w = gray.shape

        # Weak indoor prior: farther objects are often higher in image and less textured.
        y = np.linspace(0.0, 1.0, h, dtype=np.float32).reshape(h, 1)
        grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        edge_mag = cv2.magnitude(grad_x, grad_y)
        edge_mag = cv2.GaussianBlur(edge_mag, (0, 0), 1.2)

        edge_norm = edge_mag / (edge_mag.max() + 1e-6)
        brightness = cv2.GaussianBlur(gray, (0, 0), 1.2)

        relative = (0.52 * y + 0.28 * (1.0 - brightness) + 0.20 * (1.0 - edge_norm)).astype(np.float32)
        relative = cv2.GaussianBlur(relative, (0, 0), 1.2)
        relative -= float(relative.min())
        relative /= float(relative.max() + 1e-6)
        return relative + 1e-3

    def align_to_metric(self, depth_relative: np.ndarray, sparse_points_3d: np.ndarray, camera_pose: dict) -> tuple[np.ndarray, float, float]:
        R = np.asarray(camera_pose["R"], dtype=np.float64)
        t = np.asarray(camera_pose["t"], dtype=np.float64)
        K = camera_pose["intrinsics"]
        fx, fy = float(K["fx"]), float(K["fy"])
        cx, cy = float(K["cx"]), float(K["cy"])

        points_world = np.asarray(sparse_points_3d, dtype=np.float64)
        if points_world.ndim != 2 or points_world.shape[1] < 3:
            return np.clip(depth_relative * 2.5 + 0.2, 0.1, 12.0), 2.5, 0.2

        points_world = points_world[:, :3]
        H, W = depth_relative.shape

        # COLMAP convention: X_cam = R * X_world + t
        pts_cam = (R @ points_world.T).T + t
        valid = pts_cam[:, 2] > 0.05
        pts_cam = pts_cam[valid]
        if len(pts_cam) < 8:
            return np.clip(depth_relative * 2.5 + 0.2, 0.1, 12.0), 2.5, 0.2

        u = pts_cam[:, 0] * fx / pts_cam[:, 2] + cx
        v = pts_cam[:, 1] * fy / pts_cam[:, 2] + cy

        in_bounds = (u >= 0) & (u < W) & (v >= 0) & (v < H)
        if in_bounds.sum() < 8:
            return np.clip(depth_relative * 2.5 + 0.2, 0.1, 12.0), 2.5, 0.2

        u_i = u[in_bounds].astype(int)
        v_i = v[in_bounds].astype(int)
        d_true = pts_cam[in_bounds, 2]
        d_pred = depth_relative[v_i, u_i]

        A = np.stack([d_pred, np.ones_like(d_pred)], axis=1)
        try:
            solution, *_ = np.linalg.lstsq(A, d_true, rcond=None)
            scale, shift = float(solution[0]), float(solution[1])
        except Exception:
            scale, shift = 2.5, 0.2

        if not np.isfinite(scale) or scale <= 0.01:
            scale = 2.5
        if not np.isfinite(shift):
            shift = 0.2

        depth_metric = np.clip(scale * depth_relative + shift, 0.1, 12.0).astype(np.float32)
        return depth_metric, scale, shift
