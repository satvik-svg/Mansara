# AI-Powered 3D Room Design System
## Corrected Implementation Plan — All 10 Issues Fixed

> **What this version fixes:** Ten specific technical and architectural issues found
> in the previous plan. Each issue is documented, the flaw is explained, and the
> corrected approach is given. Do not use the previous plan — this supersedes it.

---

## What Was Wrong — Issue Summary

| # | Issue | Severity | Status |
|---|---|---|---|
| 1 | COLMAP scale alignment via X/Z point range is fragile and wrong | Critical | Fixed |
| 2 | `scale_factor / depth_raw` for metric depth is too naive | Critical | Fixed |
| 3 | Code bug: `y_vals` undefined + coordinate convention mismatch | Critical | Fixed |
| 4 | DBSCAN alone cannot reliably segment object instances | Major | Fixed |
| 5 | Matching clusters to detections via centre projection only is fragile | Major | Fixed |
| 6 | Window/door extraction is overspecified and will be noisy | Moderate | Fixed |
| 7 | Colab + pyngrok as dev loop causes constant friction | Moderate | Fixed |
| 8 | COLMAP failure rate indoors is underestimated | Moderate | Fixed |
| 9 | Too many product features before geometry is stable | Structural | Fixed |
| 10 | Confidence system is too shallow | Moderate | Fixed |

---

## Table of Contents

1.  [Architecture — Unchanged](#1-architecture--unchanged)
2.  [The SceneScript — Extended with Confidence](#2-the-scenescript--extended-with-confidence)
3.  [Coordinate Convention Contract](#3-coordinate-convention-contract)
4.  [Fix 1 — COLMAP Scale Alignment](#4-fix-1--colmap-scale-alignment)
5.  [Fix 2 — Metric Depth Alignment](#5-fix-2--metric-depth-alignment)
6.  [Fix 3 — Corrected depth_to_pointcloud with Proper Conventions](#6-fix-3--corrected-depth_to_pointcloud-with-proper-conventions)
7.  [Fix 4 — Object Instances: 2D-First Approach](#7-fix-4--object-instances-2d-first-approach)
8.  [Fix 5 — Robust Cluster-to-Detection Matching](#8-fix-5--robust-cluster-to-detection-matching)
9.  [Fix 6 — Windows and Doors as Optional and Confidence-Scored](#9-fix-6--windows-and-doors-as-optional-and-confidence-scored)
10. [Fix 7 — Offline Processing Mode First](#10-fix-7--offline-processing-mode-first)
11. [Fix 8 — Realistic COLMAP Failure Expectations](#11-fix-8--realistic-colmap-failure-expectations)
12. [Fix 9 — Correct Milestone Priority Order](#12-fix-9--correct-milestone-priority-order)
13. [Fix 10 — Deep Confidence System](#13-fix-10--deep-confidence-system)
14. [Complete Corrected Pipeline](#14-complete-corrected-pipeline)
15. [Full Tech Stack](#15-full-tech-stack)
16. [Environment Setup](#16-environment-setup)
17. [Project Folder Structure](#17-project-folder-structure)
18. [Complete API Contract](#18-complete-api-contract)
19. [Build Order by Milestone](#19-build-order-by-milestone)
20. [Demo Fallback SceneScript](#20-demo-fallback-scenescript)
21. [Final Summary](#21-final-summary)

---

## 1. Architecture — Unchanged

The three-layer separation is correct and stays:

```
UNDERSTANDING  →  REPRESENTATION  →  RENDERING
  (CV Stack)       (SceneScript)      (Three.js)
      ↑                  ↕                 ↑
   Video              AI Agent          User
   Frames             Edits             Interaction
```

What changes is how the Understanding layer works internally — every broken
assumption in the CV pipeline is replaced with a more robust approach.

---

## 2. The SceneScript — Extended with Confidence

Every measurement in the SceneScript now carries its own confidence score.
This is critical for the correction UI, for debugging, and for deciding what the
user must confirm before the design session begins.

```json
{
  "version": 2,
  "session_id": "uuid-here",
  "source": "colmap_pipeline",
  "pipeline_mode": "colmap_full",

  "room": {
    "width": 4.52,
    "width_confidence": 0.78,
    "depth": 5.18,
    "depth_confidence": 0.74,
    "height": 2.76,
    "height_confidence": 0.61,
    "floor_plane": [0.01, 0.999, -0.003, 0.002],
    "floor_plane_inlier_ratio": 0.84
  },

  "walls": [
    {
      "id": "wall_north",
      "x1": 0, "z1": 0, "x2": 4.52, "z2": 0,
      "plane_equation": [0.002, -0.01, 1.0, 0.01],
      "confidence": 0.81
    }
  ],

  "windows": [
    {
      "id": "win_001",
      "wall": "wall_north",
      "x": 1.4, "width": 1.2, "height": 1.1, "sill_height": 0.9,
      "confidence": 0.55,
      "user_confirmed": false,
      "detected_by": "grounding_dino"
    }
  ],

  "doors": [
    {
      "id": "door_001",
      "wall": "wall_west",
      "x": 0.5, "width": 0.9, "height": 2.1,
      "confidence": 0.62,
      "user_confirmed": false,
      "detected_by": "grounding_dino"
    }
  ],

  "objects": [
    {
      "id": "obj_001",
      "type": "sofa",
      "type_confidence": 0.91,
      "position": { "x": 1.18, "y": 0.0, "z": 0.52 },
      "position_confidence": 0.82,
      "size": { "w": 2.21, "h": 0.84, "d": 0.91 },
      "size_confidence": 0.76,
      "rotation_y": 0.0,
      "rotation_confidence": 0.42,
      "color": "grey",
      "style": null,
      "label_source": "grounding_dino",
      "label_confirmed": false,
      "source_frames": ["frame_0007", "frame_0012", "frame_0019"],
      "sam_mask_ids": ["mask_007_f07", "mask_003_f12"],
      "cluster_id": 3,
      "product_url": null,
      "product_name": null
    }
  ],

  "metadata": {
    "room_type": "living_room",
    "room_type_confidence": 0.88,
    "style": null,
    "pipeline_version": "colmap_v2",
    "colmap_registered_frames": 38,
    "colmap_total_frames": 52,
    "colmap_registration_ratio": 0.73,
    "scale_method": "floor_plane_gravity_alignment",
    "confidence": "metric",
    "processing_time_seconds": 94,
    "created_at": "2025-01-01T00:00:00Z",
    "last_edited": "2025-01-01T00:00:00Z"
  }
}
```

**How confidence drives the UI:**
- `type_confidence < 0.6` → object flagged in correction UI with warning colour
- `position_confidence < 0.5` → position shown as dashed outline in 3D
- `size_confidence < 0.5` → size shown as approximate, user prompted to confirm
- `rotation_confidence < 0.5` → rotation not applied, object shown axis-aligned
- `window/door confidence < 0.6` → not rendered, only shown in correction panel
- `floor_plane_inlier_ratio < 0.6` → room height marked as estimated

---

## 3. Coordinate Convention Contract

This section did not exist in the previous plan. It must exist because coordinate
convention mismatches are how 3D pipelines silently break.

Every tool uses a different convention. These must be explicitly defined and all
conversions written out before any code is written.

### Convention table

| System | X | Y | Z | Notes |
|---|---|---|---|---|
| OpenCV camera | right | down | forward (into scene) | Standard camera convention |
| COLMAP world | varies | varies | varies | Determined by reconstruction, not fixed |
| Open3D | right | up | out of screen | Same as OpenGL |
| Three.js | right | up | out of screen (toward viewer) | Same as OpenGL |
| Our SceneScript | right (room width) | up | depth (into room) | Y-up, Z-into-room |

### Required transformations

**COLMAP to SceneScript world:**
COLMAP outputs cameras in its own arbitrary world frame. After reconstruction, we
align the COLMAP world so that:
- The floor plane becomes Y=0
- The up direction becomes +Y
- The room entry is at Z=0

This alignment is done using the fitted floor plane normal (see Fix 1).

**OpenCV camera to 3D point:**
```
# OpenCV convention: +X right, +Y down, +Z forward
# Point at pixel (u, v) with depth d:
x_cam =  (u - cx) * d / fx   # right
y_cam =  (v - cy) * d / fy   # DOWN in camera space
z_cam =  d                    # forward

# To convert to Y-up world: flip Y
x_world_cam =  x_cam
y_world_cam = -y_cam          # Y-up
z_world_cam =  z_cam
```

**Three.js rendering:**
Three.js uses Y-up, Z toward viewer. SceneScript uses Y-up, Z into room (away from
viewer entry point). The Three.js scene origin is placed at the room's front-left
floor corner. All SceneScript positions map directly to Three.js positions with no
further transformation needed — but camera must face -Z initially.

---

## 4. Fix 1 — COLMAP Scale Alignment

### What was wrong

The old plan aligned COLMAP scale using the X/Z range of sparse 3D points:
```python
# WRONG — do not use this
x_range = points3d[:, 0].max() - points3d[:, 0].min()
scale_x = room_width / x_range
```

This fails because:
- COLMAP world axes are not aligned with room axes
- Sparse points include furniture, partial walls, noisy outliers
- Point range is not the room boundary
- X and Z axes may not correspond to room width and depth

### The correct approach: floor-plane-based scale and alignment

The robust method uses the floor plane to:
1. Rotate the COLMAP world so floor becomes Y=0 and gravity is -Y
2. Use the wall planes (not point ranges) to determine room extents
3. Use the user-provided dimensions only to resolve the final scale ambiguity

```python
# pipeline/colmap_aligner.py

import numpy as np
import open3d as o3d
import pycolmap

def align_colmap_reconstruction(reconstruction, room_width: float,
                                  room_depth: float) -> dict:
    """
    Align COLMAP reconstruction to a Y-up, floor-at-zero world frame.
    Use floor plane as the ground truth, not point ranges.
    Returns: aligned poses, scale factor, world-to-colmap transform.
    """

    # 1. Extract all 3D points from COLMAP sparse reconstruction
    points = np.array([p.xyz for p in reconstruction.points3D.values()])

    # 2. Fit floor plane to the lowest-lying points using RANSAC
    #    Use Open3D for robust plane fitting
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points)

    plane_model, inliers = pcd.segment_plane(
        distance_threshold=0.05,
        ransac_n=3,
        num_iterations=1000
    )
    [a, b, c, d] = plane_model  # ax + by + cz + d = 0

    # 3. The floor plane normal should point upward
    #    If b < 0, flip the normal
    floor_normal = np.array([a, b, c])
    if floor_normal[1] < 0:
        floor_normal = -floor_normal
        d = -d

    # 4. Build rotation matrix that maps floor_normal → [0, 1, 0] (Y-up)
    up = np.array([0.0, 1.0, 0.0])
    rotation_axis = np.cross(floor_normal, up)
    axis_norm = np.linalg.norm(rotation_axis)

    if axis_norm < 1e-6:
        # Already aligned
        R_align = np.eye(3)
    else:
        rotation_axis /= axis_norm
        cos_angle = np.clip(np.dot(floor_normal, up), -1, 1)
        angle = np.arccos(cos_angle)
        # Rodrigues rotation
        K = np.array([
            [0, -rotation_axis[2], rotation_axis[1]],
            [rotation_axis[2], 0, -rotation_axis[0]],
            [-rotation_axis[1], rotation_axis[0], 0]
        ])
        R_align = np.eye(3) + np.sin(angle)*K + (1-np.cos(angle))*(K @ K)

    # 5. Apply rotation to all points
    points_aligned = (R_align @ points.T).T

    # 6. Translate so floor is at Y=0
    floor_height = np.percentile(points_aligned[:, 1], 5)  # 5th percentile = floor
    points_aligned[:, 1] -= floor_height

    # 7. Now estimate scale using floor-plane-projected wall extents
    #    Project all points onto the floor (Y=0 plane)
    floor_points = points_aligned[points_aligned[:, 1] < 0.3]  # near-floor points
    if len(floor_points) < 10:
        floor_points = points_aligned

    x_span = np.percentile(floor_points[:, 0], 95) - np.percentile(floor_points[:, 0], 5)
    z_span = np.percentile(floor_points[:, 2], 95) - np.percentile(floor_points[:, 2], 5)

    # Use the LARGER of the two user dimensions for the LARGER span
    dims = sorted([(x_span, 'x'), (z_span, 'z')])
    user_dims = sorted([room_width, room_depth])

    # Map smaller span → smaller user dim, larger → larger
    scales = []
    for (span, axis), user_dim in zip(dims, user_dims):
        if span > 0.1:
            scales.append(user_dim / span)
    scale = float(np.median(scales)) if scales else 1.0

    # 8. Build the full transformation: T_world = scale * R_align * T_colmap - offset
    t_offset = np.array([
        np.percentile(floor_points[:, 0], 5) * scale,
        0.0,
        np.percentile(floor_points[:, 2], 5) * scale
    ])

    # 9. Transform all camera poses
    camera_poses_aligned = {}
    for img_id, image in reconstruction.images.items():
        R_cam = image.rotation_matrix()
        t_cam = image.tvec

        # Apply world alignment: rotate then scale
        R_new = R_align @ R_cam
        t_new = (R_align @ t_cam) * scale - floor_height * scale
        t_new -= t_offset

        cam_id = image.camera_id
        cam = reconstruction.cameras[cam_id]
        camera_poses_aligned[image.name] = {
            "R": R_new.tolist(),
            "t": t_new.tolist(),
            "camera_id": cam_id,
            "intrinsics": {
                "fx": float(cam.focal_length),
                "fy": float(cam.focal_length),
                "cx": float(cam.principal_point_x),
                "cy": float(cam.principal_point_y),
                "width": int(cam.width),
                "height": int(cam.height)
            }
        }

    inlier_ratio = len(inliers) / len(points)
    return {
        "camera_poses": camera_poses_aligned,
        "scale_factor": scale,
        "R_align": R_align.tolist(),
        "floor_offset": float(floor_height * scale),
        "floor_plane_inlier_ratio": float(inlier_ratio),
        "num_images_registered": len(reconstruction.images),
        "num_sparse_points": len(points)
    }
```

**Why this is better:**
- Alignment is driven by the actual floor geometry, not arbitrary point extents
- Scale estimation uses 5th–95th percentile (outlier-robust) not min/max
- The two user dimensions are matched to the two spans by size, handling any
  COLMAP world orientation correctly
- The inlier ratio is saved as `floor_plane_inlier_ratio` in SceneScript metadata

---

## 5. Fix 2 — Metric Depth Alignment

### What was wrong

The old plan used:
```python
# WRONG — do not use this
depth_metric = scale_factor / (depth_raw + 1e-6)
```

This treats depth as inversely proportional to the raw output, which is neither
correct for Depth Anything V2 nor generally true for monocular depth models.

### What Depth Anything V2 actually outputs

Depth Anything V2 outputs a relative affine-invariant depth map. The relationship
between the network output `d_pred` and the real depth `d_real` is:

```
d_real ≈ s * d_pred + t
```

Where `s` (scale) and `t` (shift) are unknown constants that vary per image.
A single global reciprocal does not recover this correctly.

### The correct approach: scale-and-shift alignment per frame

For each frame, use the COLMAP sparse 3D points that project into that frame as
known ground-truth depth anchors. Fit the linear relationship between predicted
depth and COLMAP depth at those anchor points using least squares.

```python
# pipeline/depth_estimator.py

import torch
import numpy as np
import cv2
from transformers import AutoImageProcessor, AutoModelForDepthEstimation
from PIL import Image

class DepthEstimator:
    def __init__(self):
        model_name = "depth-anything/Depth-Anything-V2-Large-hf"
        self.processor = AutoImageProcessor.from_pretrained(model_name)
        self.model = AutoModelForDepthEstimation.from_pretrained(model_name)
        self.model = self.model.cuda().eval()

    @torch.no_grad()
    def predict_relative(self, image_path: str) -> np.ndarray:
        """Returns relative depth map, same HxW as input. Values are arbitrary scale."""
        image = Image.open(image_path).convert("RGB")
        inputs = self.processor(images=image, return_tensors="pt")
        inputs = {k: v.cuda() for k, v in inputs.items()}
        outputs = self.model(**inputs)
        depth = outputs.predicted_depth.squeeze().cpu().numpy()
        # Upsample to original image size
        h_orig, w_orig = np.array(image).shape[:2]
        depth = cv2.resize(depth, (w_orig, h_orig), interpolation=cv2.INTER_LINEAR)
        return depth   # shape: (H, W), relative values only

    def align_to_metric(self, depth_relative: np.ndarray,
                         sparse_points_3d: np.ndarray,
                         camera_pose: dict) -> tuple[np.ndarray, float, float]:
        """
        Align relative depth to metric depth using COLMAP sparse points
        as ground truth anchors.

        Solves:  d_metric = s * d_relative + t
        using least squares on the sparse anchor points.

        Returns: (depth_metric, scale s, shift t)
        """
        R = np.array(camera_pose["R"])
        t = np.array(camera_pose["t"])
        K = camera_pose["intrinsics"]
        fx, fy = K["fx"], K["fy"]
        cx, cy = K["cx"], K["cy"]
        H, W = depth_relative.shape

        # Project COLMAP 3D points into this camera
        # COLMAP pose: X_cam = R * X_world + t
        pts_cam = (R @ sparse_points_3d.T).T + t  # shape: (N, 3)

        # Only use points in front of camera
        valid = pts_cam[:, 2] > 0.1
        pts_cam = pts_cam[valid]

        if len(pts_cam) < 4:
            # Not enough anchors — fall back to global scale only (no shift)
            median_colmap_depth = float(np.median(pts_cam[:, 2])) if len(pts_cam) > 0 else 2.0
            median_pred = float(np.median(depth_relative))
            s = median_colmap_depth / (median_pred + 1e-6)
            t_shift = 0.0
            return (depth_relative * s).clip(0.1, 15.0), s, t_shift

        # Project to pixel coordinates
        u = pts_cam[:, 0] * fx / pts_cam[:, 2] + cx
        v = pts_cam[:, 1] * fy / pts_cam[:, 2] + cy

        # Only keep projections that fall inside the image
        in_bounds = (u >= 0) & (u < W) & (v >= 0) & (v < H)
        u = u[in_bounds].astype(int)
        v = v[in_bounds].astype(int)
        d_colmap = pts_cam[in_bounds, 2]  # true metric depth from COLMAP

        if len(d_colmap) < 4:
            s = float(np.median(d_colmap)) / (float(np.median(depth_relative)) + 1e-6)
            return (depth_relative * s).clip(0.1, 15.0), s, 0.0

        # Sample predicted depth at anchor pixel locations
        d_pred = depth_relative[v, u]

        # Solve d_metric = s * d_pred + t using least squares
        # A @ [s, t]^T = d_colmap
        A = np.stack([d_pred, np.ones_like(d_pred)], axis=1)
        result = np.linalg.lstsq(A, d_colmap, rcond=None)
        s, t_shift = result[0]

        # Clamp to physically reasonable values
        s = max(s, 0.1)

        depth_metric = (s * depth_relative + t_shift).clip(0.1, 15.0)

        return depth_metric, float(s), float(t_shift)
```

**Why this is correct:**
- Solves the actual linear model `d_metric = s * d_pred + t`
- Uses COLMAP's metric measurements as anchors — they are already in metres
- Falls back gracefully when fewer than 4 anchor points are visible
- The `clip(0.1, 15.0)` prevents physically impossible depths

---

## 6. Fix 3 — Corrected depth_to_pointcloud with Proper Conventions

### What was wrong

The old code had `y_vals` used without being defined — a direct variable bug.
More importantly, the coordinate conventions were never explicitly handled:
OpenCV uses Y-down cameras; Open3D and Three.js use Y-up worlds.

### The corrected function

```python
# pipeline/geometry_fusion.py  — corrected version

import open3d as o3d
import numpy as np
import cv2

def depth_to_pointcloud(
    depth_metric: np.ndarray,          # (H, W) — metres, already scale-aligned
    color_image: np.ndarray,           # (H, W, 3) — uint8 RGB
    camera_pose: dict,                 # {"R": 3x3, "t": 3, "intrinsics": {...}}
    max_depth: float = 8.0,
    min_depth: float = 0.1
) -> o3d.geometry.PointCloud:
    """
    Back-project a metric depth map to a 3D point cloud in WORLD coordinates.

    Coordinate conventions (explicit):
      Camera frame:  +X right, +Y DOWN, +Z forward  (OpenCV convention)
      World frame:   +X right, +Y UP,   +Z into room (Y-up, SceneScript convention)
      Transformation: y_world = -y_cam  (flip Y to go from camera to world)

    COLMAP rotation R and translation t transform points as:
      X_cam = R @ X_world + t
    So:
      X_world = R^T @ (X_cam - t)
    """
    H, W = depth_metric.shape
    K = camera_pose["intrinsics"]
    fx, fy = K["fx"], K["fy"]
    cx, cy = K["cx"], K["cy"]

    R = np.array(camera_pose["R"])   # shape (3, 3)
    t = np.array(camera_pose["t"])   # shape (3,)

    # --- 1. Build pixel grid ---
    u_coords, v_coords = np.meshgrid(np.arange(W), np.arange(H))
    d = depth_metric  # (H, W)

    # --- 2. Valid depth mask ---
    valid = (d > min_depth) & (d < max_depth)

    # --- 3. Back-project to CAMERA frame (OpenCV convention: Y-down) ---
    x_cam =  (u_coords[valid] - cx) * d[valid] / fx   # right
    y_cam =  (v_coords[valid] - cy) * d[valid] / fy   # DOWN (OpenCV)
    z_cam =  d[valid]                                  # forward

    pts_cam = np.stack([x_cam, y_cam, z_cam], axis=1)  # (N, 3)

    # --- 4. Transform to WORLD frame ---
    # COLMAP: X_cam = R @ X_world + t  =>  X_world = R^T @ (X_cam - t)
    pts_world = (R.T @ (pts_cam - t).T).T  # (N, 3), still Y-down

    # --- 5. Flip Y to get Y-up world ---
    pts_world[:, 1] *= -1  # now Y is up

    # --- 6. Build Open3D PointCloud ---
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(pts_world)

    if color_image is not None:
        colors = color_image[valid].astype(np.float64) / 255.0
        pcd.colors = o3d.utility.Vector3dVector(colors)

    return pcd
```

**Every assumption is now explicit:**
- OpenCV camera convention: Y is DOWN in camera frame
- Y flip converts to Y-up world
- COLMAP pose convention: `X_cam = R @ X_world + t`, so inverse is `R^T @ (X_cam - t)`
- This is documented in the function docstring so the next developer cannot miss it

---

## 7. Fix 4 — Object Instances: 2D-First Approach

### What was wrong

The old plan relied on DBSCAN clustering of the 3D point cloud to segment objects,
then matched the resulting clusters back to 2D detections. This fails because
indoor point clouds commonly merge adjacent furniture into one cluster or split
one object into several clusters.

### The correct approach: 2D-first, lift to 3D

Instead of detecting objects in 3D and then labelling them, detect objects in 2D
first (GroundingDINO + SAM give you labelled pixel masks), then use the depth map
to lift each 2D mask into a 3D bounding volume. The result is a labelled 3D object
from the start, with no ambiguous matching step.

```python
# pipeline/object_instances.py

import numpy as np
import open3d as o3d
from typing import Optional

def lift_2d_detections_to_3d(
    detections: list[dict],             # from GroundingDINO + SAM per frame
    depth_metric: np.ndarray,           # (H, W) metric depth for this frame
    camera_pose: dict,
    frame_name: str
) -> list[dict]:
    """
    For each 2D detection (label + SAM mask), back-project the masked pixels
    using the metric depth map to get a 3D point cloud for that object only.

    Returns list of 3D object candidates, each with:
      - label, confidence
      - 3D point cloud (Open3D PointCloud)
      - 3D bounding box
      - source frame
    """
    H, W = depth_metric.shape
    K = camera_pose["intrinsics"]
    fx, fy = K["fx"], K["fy"]
    cx, cy = K["cx"], K["cy"]
    R = np.array(camera_pose["R"])
    t = np.array(camera_pose["t"])

    results = []

    for det in detections:
        mask = det["mask"]           # (H, W) bool — from SAM
        if mask.sum() < 50:          # too few pixels, skip
            continue

        # Get depth values only inside SAM mask
        d = depth_metric[mask]

        # Reject depth outliers within the mask using IQR
        q25, q75 = np.percentile(d, 25), np.percentile(d, 75)
        iqr = q75 - q25
        d_filtered_mask = mask.copy()
        depth_valid = depth_metric.copy()
        depth_valid[mask] = np.where(
            (depth_metric[mask] >= q25 - 1.5*iqr) &
            (depth_metric[mask] <= q75 + 1.5*iqr),
            depth_metric[mask],
            0
        )
        combined_mask = mask & (depth_valid > 0.1) & (depth_valid < 8.0)

        if combined_mask.sum() < 30:
            continue

        # Back-project masked pixels to camera frame (OpenCV: Y-down)
        u_coords, v_coords = np.meshgrid(np.arange(W), np.arange(H))
        x_cam =  (u_coords[combined_mask] - cx) * depth_valid[combined_mask] / fx
        y_cam =  (v_coords[combined_mask] - cy) * depth_valid[combined_mask] / fy
        z_cam =  depth_valid[combined_mask]
        pts_cam = np.stack([x_cam, y_cam, z_cam], axis=1)

        # Transform to world frame, flip Y for Y-up
        pts_world = (R.T @ (pts_cam - t).T).T
        pts_world[:, 1] *= -1  # Y-up

        # Build per-object point cloud
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(pts_world)

        # Compute 3D bounding box
        bbox = pcd.get_axis_aligned_bounding_box()
        min_b = np.asarray(bbox.min_bound)
        max_b = np.asarray(bbox.max_bound)

        # Object position = centre of base on floor
        cx_obj = (min_b[0] + max_b[0]) / 2
        cz_obj = (min_b[2] + max_b[2]) / 2

        results.append({
            "label": det["label"],
            "confidence": det["confidence"],
            "sam_mask_id": det["mask_id"],
            "frame": frame_name,
            "pcd": pcd,
            "position": {
                "x": float(cx_obj),
                "y": 0.0,             # always floor-anchored
                "z": float(cz_obj)
            },
            "size": {
                "w": float(max_b[0] - min_b[0]),
                "h": float(max_b[1] - min_b[1]),
                "d": float(max_b[2] - min_b[2])
            },
            "num_points": len(pcd.points)
        })

    return results
```

**Why this is better than 3D-first clustering:**
- The label is attached to the 3D object from the start — no matching problem
- SAM mask boundaries prevent bleed between adjacent objects
- Depth outlier rejection (IQR) removes depth noise within each mask
- Each object's 3D bounding box comes from its own pixel-masked points only

---

## 8. Fix 5 — Robust Cluster-to-Detection Matching Across Frames

### What was wrong

The old plan projected only the cluster's 3D centre into each frame and checked
if it landed inside a GroundingDINO bounding box. This fails when:
- The centre is occluded
- The object is partially visible
- The projection angle is oblique

### The new approach: use multi-frame 2D-first results and merge by overlap

Since we now use the 2D-first approach (Fix 4), we get per-frame 3D object
candidates with labels. The fusion step merges these into final scene objects.

```python
# pipeline/object_fusion.py

import numpy as np
from collections import defaultdict

def fuse_per_frame_objects(per_frame_objects: list[list[dict]],
                            iou_3d_threshold: float = 0.3) -> list[dict]:
    """
    Merge per-frame 3D object candidates into a single deduplicated object list.

    Strategy:
      1. Pool all candidates from all frames
      2. For each pair, compute 3D bounding box IoU
      3. Merge candidates with IoU > threshold (same object seen from different frames)
      4. Keep the candidate with the highest confidence as the representative
      5. Aggregate position/size as weighted mean across all merged candidates
      6. Collect all source frames for the merged object
    """
    all_candidates = []
    for frame_objs in per_frame_objects:
        all_candidates.extend(frame_objs)

    if not all_candidates:
        return []

    # Build union-find structure for merging
    n = len(all_candidates)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        parent[find(i)] = find(j)

    def bbox_3d_iou(a: dict, b: dict) -> float:
        """Compute 3D bounding box IoU between two object candidates."""
        def get_intervals(obj):
            cx, cz = obj["position"]["x"], obj["position"]["z"]
            w, d = obj["size"]["w"], obj["size"]["d"]
            h = obj["size"]["h"]
            return (cx - w/2, cx + w/2,  # X
                    0.0, h,               # Y (floor to top)
                    cz - d/2, cz + d/2)  # Z

        ax1, ax2, ay1, ay2, az1, az2 = get_intervals(a)
        bx1, bx2, by1, by2, bz1, bz2 = get_intervals(b)

        ix = max(0, min(ax2, bx2) - max(ax1, bx1))
        iy = max(0, min(ay2, by2) - max(ay1, by1))
        iz = max(0, min(az2, bz2) - max(az1, bz1))
        intersection = ix * iy * iz

        vol_a = (ax2-ax1) * (ay2-ay1) * (az2-az1)
        vol_b = (bx2-bx1) * (by2-by1) * (bz2-bz1)
        union_vol = vol_a + vol_b - intersection

        return intersection / union_vol if union_vol > 0 else 0.0

    # Merge candidates with high 3D IoU (same object, different frames)
    for i in range(n):
        for j in range(i+1, n):
            if all_candidates[i]["label"] == all_candidates[j]["label"]:
                iou = bbox_3d_iou(all_candidates[i], all_candidates[j])
                if iou > iou_3d_threshold:
                    union(i, j)

    # Group by root
    groups = defaultdict(list)
    for i in range(n):
        groups[find(i)].append(i)

    # For each group: compute final object as weighted average
    final_objects = []
    for group_indices in groups.values():
        group = [all_candidates[i] for i in group_indices]

        # Weight by confidence and number of points
        weights = np.array([g["confidence"] * g["num_points"] for g in group])
        weights /= weights.sum()

        # Weighted mean position
        pos_x = sum(w * g["position"]["x"] for w, g in zip(weights, group))
        pos_z = sum(w * g["position"]["z"] for w, g in zip(weights, group))

        # Weighted mean size
        size_w = sum(w * g["size"]["w"] for w, g in zip(weights, group))
        size_h = max(g["size"]["h"] for g in group)   # take max height
        size_d = sum(w * g["size"]["d"] for w, g in zip(weights, group))

        # Best label = highest confidence across group
        best = max(group, key=lambda g: g["confidence"])

        # Compute position confidence from agreement across frames
        if len(group) > 1:
            pos_std = np.std([g["position"]["x"] for g in group]) + \
                      np.std([g["position"]["z"] for g in group])
            pos_conf = float(np.clip(1.0 - pos_std / 0.5, 0.2, 1.0))
        else:
            pos_conf = 0.5   # only seen in one frame — lower confidence

        final_objects.append({
            "label": best["label"],
            "type_confidence": float(best["confidence"]),
            "position": {"x": float(pos_x), "y": 0.0, "z": float(pos_z)},
            "position_confidence": pos_conf,
            "size": {
                "w": float(size_w),
                "h": float(size_h),
                "d": float(size_d)
            },
            "size_confidence": float(min(w for w in weights) * len(group) * 0.5 + 0.3),
            "rotation_y": 0.0,
            "rotation_confidence": 0.4,   # rotation not reliably determined
            "source_frames": list({g["frame"] for g in group}),
            "sam_mask_ids": [g["sam_mask_id"] for g in group],
            "num_observations": len(group)
        })

    return final_objects
```

---

## 9. Fix 6 — Windows and Doors as Optional and Confidence-Scored

### What was wrong

The previous plan implied windows and doors would reliably come out of the pipeline.
In practice: windows are bright/reflective (depth models fail on them), doors may
be open/closed/occluded, and relying on them for room shell logic is risky.

### The correct approach

Windows and doors are:
- Detected by GroundingDINO on frames where they are clearly visible
- Given a confidence score
- Shown in the correction UI but NOT automatically rendered if confidence < 0.6
- Never used as constraints in the room boundary logic
- Always `user_confirmed: false` until the user explicitly confirms them

```python
# In scene_builder.py — window/door extraction

def extract_openings(detections_by_frame: dict,
                      opening_type: str,   # "window" or "door"
                      wall_planes: list,
                      camera_poses: dict,
                      depth_maps: dict) -> list[dict]:
    """
    Extract windows or doors from GroundingDINO detections.
    Returns a list with confidence scores. Low-confidence ones
    are included but flagged as unconfirmed.
    """
    opening_labels = {
        "window": ["window", "glass window", "window frame"],
        "door": ["door", "doorway", "entrance"]
    }
    valid_labels = opening_labels[opening_type]

    candidates = []
    for frame_name, detections in detections_by_frame.items():
        for det in detections:
            if any(label in det["label"].lower() for label in valid_labels):
                # Low depth confidence near windows/doors is expected and noted
                candidates.append({
                    "frame": frame_name,
                    "label": det["label"],
                    "confidence": det["confidence"],
                    "bbox": det["bbox"]
                })

    if not candidates:
        return []

    # Group nearby candidates (same opening seen from multiple frames)
    merged = merge_opening_candidates(candidates, camera_poses, depth_maps)

    # Mark everything below threshold as low-confidence
    result = []
    for i, m in enumerate(merged):
        result.append({
            "id": f"{opening_type}_{i+1:03d}",
            "type": opening_type,
            "wall": infer_wall(m, wall_planes),
            "x": m.get("x", 0.0),
            "width": m.get("width", 1.0),
            "height": m.get("height", 2.0 if opening_type == "door" else 1.0),
            "sill_height": 0.9 if opening_type == "window" else 0.0,
            "confidence": m["confidence"],
            "user_confirmed": False,
            "detected_by": "grounding_dino"
        })

    return result
```

**In Three.js:** Windows and doors with `confidence < 0.6` and `user_confirmed: false`
are NOT rendered in the 3D scene. They appear only in the correction panel with a
warning label. The user must explicitly confirm them to add them to the render.
The room shell logic (floor, walls) never depends on window or door positions.

---

## 10. Fix 7 — Offline Processing Mode First

### What was wrong

The previous plan tried to wire up Colab + Flask + pyngrok + FastAPI all at once from
day one. This creates constant friction: tunnel URLs change on restart, models reload
on every notebook restart, debugging across two systems is hard.

### The correct two-phase dev strategy

**Phase A — Offline mode (build and validate the CV pipeline first)**

Run the GPU pipeline as a standalone notebook or script. Save all outputs to disk.
Load them into the app manually. Do not attempt live integration yet.

```
video.mp4
    ↓ (run notebook manually)
/outputs/session_001/
    ├── frames/           # extracted frames
    ├── colmap/           # reconstruction output
    ├── depth_maps/       # per-frame .npy files
    ├── detections.json   # GroundingDINO + SAM results
    ├── pointcloud.ply    # fused Open3D cloud
    └── scene.json        # final SceneScript
```

The FastAPI backend in Phase A has a simple `POST /api/load_precomputed` endpoint
that loads a pre-generated `scene.json` and starts the session. All the UI, agent,
and shop code is built and tested against pre-generated scenes.

**Phase B — Live API mode (after the pipeline is validated)**

Only after the CV pipeline produces good SceneScripts offline, wrap it in the
Flask worker and integrate the live upload flow.

```python
# backend/routers/scan.py — Phase A endpoint

@router.post("/api/load_precomputed")
async def load_precomputed(
    session_id: str,
    scene_path: str = "/tmp/session_001/scene.json"
):
    """Load a pre-generated SceneScript without running the CV pipeline."""
    with open(scene_path) as f:
        scene = json.load(f)
    validate_scene(scene)
    session_store.create_from_scene(session_id, scene)
    return {"session_id": session_id, "scene": scene, "mode": "precomputed"}
```

**Phase B — Live worker (after Phase A is working):**

```python
# gpu_worker/worker.py — Phase B Flask server on Colab

from flask import Flask, request, jsonify
import threading

app = Flask(__name__)

# Models are loaded ONCE at startup, not on every request
print("Loading models...")
depth_estimator = DepthEstimator()
detector = ObjectDetectorAndSegmenter(...)
print("Models ready.")

@app.route("/process", methods=["POST"])
def process():
    data = request.json
    session_id = data["session_id"]
    video_url = data["video_url"]   # FastAPI backend serves the uploaded video
    room_width = data["room_width"]
    room_depth = data["room_depth"]

    # Run full pipeline synchronously (Colab handles one job at a time)
    result = run_full_pipeline(session_id, video_url, room_width, room_depth)
    return jsonify(result)

if __name__ == "__main__":
    from pyngrok import ngrok
    tunnel = ngrok.connect(5000)
    print(f"GPU worker URL: {tunnel.public_url}")
    app.run(port=5000)
```

**Models are loaded once at Flask startup, not on every request.**
This is the most important performance fix for the Colab dev loop.

---

## 11. Fix 8 — Realistic COLMAP Failure Expectations

### What was wrong

The old plan treated COLMAP failure as a rare edge case. In reality, COLMAP fails
or gives poor results frequently on indoor rooms.

### Realistic COLMAP success/failure rates indoors

| Room condition | Expected COLMAP outcome |
|---|---|
| Good texture, steady slow walk, good light | 70–90% frames register |
| Some blank walls, decent light | 40–70% frames register |
| Mostly white walls, fast walk | 10–40% — often partial |
| Dark room, fast movement | Usually fails |
| Mirror or glass wall visible | Severely confused |
| Camera shake / blur | Feature matching breaks down |

**The correct mental model:**

Do not think: "COLMAP will usually work, fallback is for rare failures."

Think: "COLMAP may partially work most of the time. Full metric accuracy is a bonus.
The system must be useful even when COLMAP gives 50% registration."

### Three pipeline tiers (not two)

```python
def determine_pipeline_quality(colmap_result: dict) -> str:
    ratio = colmap_result["num_images_registered"] / colmap_result["num_frames"]

    if ratio >= 0.7 and colmap_result["num_sparse_points"] >= 2000:
        return "metric"        # Full COLMAP — real metric coordinates

    elif ratio >= 0.3 and colmap_result["num_sparse_points"] >= 500:
        return "partial"       # Partial COLMAP — scale may be off,
                               # positions are still better than guessing
                               # Mark confidence as "partial_metric"

    else:
        return "approximate"   # COLMAP failed — use Claude Vision fallback
                               # Mark confidence as "approximate"
```

**Each tier is shown to the user in the UI:**

```
Metric accuracy  ●●●●●   Full COLMAP reconstruction
Partial accuracy ●●●○○   Partial COLMAP — some positions may be off
Approximate      ●●○○○   AI vision estimate — confirm all positions
```

---

## 12. Fix 9 — Correct Milestone Priority Order

### What was wrong

The previous plan tried to build room reconstruction + object detection + scene
editing + hover-to-shop + agent + product matching all at the same time.
This never stabilises the core geometry.

### The correct milestone order

Build each milestone completely before starting the next one.
Do not add shopping before geometry is reliable.

---

**Milestone 1 — Video to coherent point cloud with camera poses**

```
Input:  30-second room video
Output: Registered point cloud (.ply) + camera poses per frame

Success criteria:
  - COLMAP registers >= 70% of frames
  - Point cloud clearly shows room floor and walls
  - Camera trajectory makes spatial sense
  - Scale aligned to user-provided dimensions

Do NOT move to M2 until this produces good output on 3 different test rooms.
```

---

**Milestone 2 — Point cloud to room shell and object instances**

```
Input:  Point cloud + camera poses + depth maps + detections
Output: SceneScript with room geometry + object list

Success criteria:
  - Floor plane fits correctly (inlier ratio >= 0.7)
  - Room dimensions within 15% of actual dimensions
  - Objects detected in >= 80% of rooms
  - Each object has a plausible 3D bounding box
  - SceneScript passes full validation

Do NOT move to M3 until SceneScript is stable and correct.
```

---

**Milestone 3 — SceneScript to Three.js interactive render**

```
Input:  Validated SceneScript
Output: Navigable 3D room in browser

Success criteria:
  - Room geometry renders at correct proportions
  - All objects render at correct positions and sizes
  - GLTF models load for all common object types
  - Hover and click interaction works
  - Correction UI works and updates the scene

Do NOT move to M4 until the 3D scene looks correct.
```

---

**Milestone 4 — LLM design agent**

```
Input:  SceneScript + natural language instruction
Output: Updated SceneScript + re-render

Success criteria:
  - All action types work: replace, move, add, remove, restyle
  - Validation catches bad actions
  - Rollback works on failure
  - Undo works
  - Partial re-render works (only changed objects update)
```

---

**Milestone 5 — Hover-to-shop**

```
Input:  Selected 3D object + product search
Output: Real product listings + product placement in scene

Success criteria:
  - Hover tooltip appears on 500ms dwell
  - Product search returns results for common furniture types
  - Placed product renders at real dimensions
  - Buy link works
  - Product dimensions in SceneScript after placement
```

**This order is not optional.** Skipping to M5 before M2 is stable will produce
a shopping experience on top of wrong room geometry, which makes the whole system
feel broken.

---

## 13. Fix 10 — Deep Confidence System

### What was wrong

The previous SceneScript had a single `confidence` string field on the metadata
object. This did not carry enough information to drive the correction UI, debugging,
or trust decisions.

### The complete confidence system

Every measurement has its own confidence. The SceneScript schema from Section 2
of this document shows all fields. Here is how each confidence value is computed
and what it drives downstream.

```python
# How confidence values are computed

# Type confidence: comes directly from GroundingDINO detection score
type_confidence = detection["confidence"]   # 0.0 – 1.0

# Position confidence: based on agreement across multiple frames
#   High if object seen in 3+ frames and positions agree within 0.2m
#   Low if seen in only 1 frame or positions vary significantly
def compute_position_confidence(observations: list[dict]) -> float:
    if len(observations) <= 1:
        return 0.5
    positions = np.array([[o["position"]["x"], o["position"]["z"]]
                          for o in observations])
    std = np.std(positions, axis=0).mean()
    return float(np.clip(1.0 - std / 0.3, 0.2, 1.0))

# Size confidence: based on number of 3D points and frame consistency
def compute_size_confidence(observations: list[dict]) -> float:
    total_points = sum(o["num_points"] for o in observations)
    num_frames = len(observations)
    point_score = np.clip(total_points / 5000, 0, 0.6)
    frame_score = np.clip(num_frames / 4, 0, 0.4)
    return float(point_score + frame_score)

# Rotation confidence: always low unless explicitly computed from wall alignment
# Objects parallel to walls get higher rotation confidence
def compute_rotation_confidence(position: dict, wall_planes: list) -> float:
    # If object is within 0.3m of a wall, assume rotation aligns with wall
    # This gives moderate confidence
    # Otherwise rotation is unknown → low confidence
    for wall in wall_planes:
        dist = point_to_plane_distance(position, wall["plane_equation"])
        if dist < 0.3:
            return 0.65
    return 0.35

# Room dimension confidence: based on floor plane inlier ratio + wall plane quality
def compute_room_confidence(floor_inlier_ratio: float, num_wall_planes: int) -> float:
    base = floor_inlier_ratio * 0.7
    wall_bonus = min(num_wall_planes / 4, 1.0) * 0.3
    return float(base + wall_bonus)
```

**How confidence drives the correction UI:**

```typescript
// frontend/components/correction/ObjectRow.tsx

function getConfidenceDisplay(obj: SceneObject) {
  if (obj.type_confidence < 0.6) {
    return { color: "red", label: "Check label", icon: "⚠" }
  }
  if (obj.position_confidence < 0.5) {
    return { color: "orange", label: "Position uncertain", icon: "?" }
  }
  if (obj.size_confidence < 0.5) {
    return { color: "yellow", label: "Size estimated", icon: "~" }
  }
  return { color: "green", label: "Good", icon: "✓" }
}

// Objects with any red confidence are auto-selected in the correction panel
// Objects with all green confidence can be auto-confirmed if user chooses
// "Auto-confirm all green" button skips manual review for high-confidence objects
```

**How confidence drives the 3D render:**

```tsx
// Low rotation_confidence → render object axis-aligned (rotation = 0)
// Low position_confidence → render with dashed/translucent outline
// Low type_confidence → render with question mark label floating above
// windows/doors with confidence < 0.6 → not rendered, only in panel
```

---

## 14. Complete Corrected Pipeline

The complete pipeline with all 10 fixes applied:

```
Step 1: Video Upload + Room Dimensions
   User provides: video, room_width, room_depth
   Output: video at /tmp/session_id/video.mp4, dimensions in session

Step 2: Frame Extraction
   OpenCV — 1 frame/sec, sharpness filter, cap at 80 frames
   Output: 30-80 JPEG frames

Step 3: COLMAP Sparse Reconstruction
   Runs SfM on all frames
   Output: camera poses per frame, sparse 3D points, intrinsics

Step 4: COLMAP Alignment (FIX 1)
   Floor-plane-based gravity alignment
   Robust scale estimation using 5th-95th percentile, size-sorted matching
   Output: aligned metric camera poses, scale_factor, alignment quality

Step 5: Quality Gate
   registration_ratio = registered_frames / total_frames
   quality = "metric" / "partial" / "approximate"
   If "approximate": run Claude Vision fallback, continue from Step 9

Step 6: Depth Anything V2 — Dense Depth (FIX 2)
   For each registered frame: predict relative depth
   Align each frame using COLMAP anchor points (scale-and-shift per frame)
   Output: per-frame metric depth maps (.npy files)

Step 7: GroundingDINO + SAM Detection
   Run on every registered frame with furniture text prompt
   Output: per-frame list of {label, confidence, bbox, SAM mask}

Step 8: 2D-First Object Lifting (FIX 4 + FIX 3)
   For each frame: lift each SAM mask to 3D using metric depth + aligned pose
   Correct coordinate conventions: OpenCV camera → Y-up world
   Output: per-frame list of labelled 3D object candidates

Step 9: Multi-Frame Object Fusion (FIX 5)
   Merge per-frame candidates using 3D IoU + union-find
   Compute weighted mean position/size + confidence scores
   Output: deduplicated object list with full confidence fields

Step 10: Open3D Point Cloud Fusion + Geometry
   Fuse all frame point clouds into one dense cloud
   Fit floor plane (RANSAC) → confirm/refine room dimensions
   Fit wall planes → room shell geometry
   NOTE: DBSCAN is NOT used for object segmentation (FIX 4)
   It is used only for floor/wall plane quality checks
   Output: floor plane, wall planes, room dimensions (metric)

Step 11: Window/Door Extraction (FIX 6)
   Extract from GroundingDINO detections
   Confidence-scored, all set user_confirmed: false
   Not rendered below confidence threshold
   NOT used for room shell logic
   Output: optional openings list with confidence

Step 12: SceneScript Generation
   Fuse all outputs into SceneScript v2 schema
   Apply deep confidence system (FIX 10)
   Run SceneScript validator
   Output: validated SceneScript

Step 13: Claude Semantic Labelling
   Input: object type labels from DINO
   Claude normalises labels, infers room type, notes style
   NOT used for positions or sizes
   Output: corrected labels + room_type

Step 14: Correction UI
   Show SceneScript in correction panel
   Red/orange objects flagged automatically by confidence
   "Auto-confirm all green" available for high-confidence scenes
   User confirms → design session unlocks

Step 15: Three.js Render
   SceneScript → interactive 3D room
   Confidence-driven visual indicators for uncertain objects

Step 16: AI Design Agent
   Full SceneScript sent on every call (SceneScript IS the memory)
   Claude returns structured action JSON
   Validator + rollback on failure

Step 17: Hover-to-Shop
   Three.js raycasting → 500ms dwell → tooltip
   Product search using object type + color + size
   Size filter: ± 20% of SceneScript object size
   Product placement → real dimensions in SceneScript
```

---

## 15. Full Tech Stack

### Frontend

| Technology | Version | Purpose |
|---|---|---|
| Next.js | 14+ | Web framework, routing |
| React | 18+ | Components |
| Three.js | r160+ | 3D rendering |
| @react-three/fiber | latest | React-Three.js bridge |
| @react-three/drei | latest | OrbitControls, GLTF, Outline, Html |
| Zustand | latest | SceneScript state, selection, chat |
| Tailwind CSS | 3+ | Styling |

### Backend (CPU)

| Technology | Version | Purpose |
|---|---|---|
| FastAPI | 0.110+ | API server, session management |
| Python | 3.11+ | Backend language |
| httpx | 0.27+ | Async calls to GPU worker |
| pydantic | v2+ | SceneScript validation |
| python-multipart | latest | Video upload |
| jsonschema | 4.22+ | SceneScript JSON schema |
| anthropic | 0.25+ | Claude API |
| uvicorn | latest | ASGI server |

### GPU Worker (Colab / RunPod)

| Technology | Version | Purpose |
|---|---|---|
| Python | 3.11+ | Worker language |
| opencv-python | 4.9+ | Frame extraction |
| numpy | 1.26+ | Array operations |
| COLMAP | latest | SfM / sparse reconstruction |
| pycolmap | 0.6+ | Python COLMAP bindings |
| Depth-Anything-V2 | latest | Dense metric depth (via HuggingFace) |
| torch | 2.2+ | Model inference |
| transformers | 4.40+ | GroundingDINO loading |
| groundingdino | latest | Open-vocab object detection |
| segment-anything | latest | SAM pixel-level segmentation |
| open3d | 0.18+ | Point cloud fusion, plane fitting |
| flask | latest | Phase B worker HTTP server |
| pyngrok | latest | Phase B tunnel (after Phase A validated) |

---

## 16. Environment Setup

### Backend `.env`

```bash
ANTHROPIC_API_KEY=sk-ant-...

# GPU Worker (Phase B only — not needed in Phase A)
GPU_WORKER_URL=https://abc.ngrok.io
GPU_WORKER_SECRET=shared-secret

# Product Search
SERPAPI_KEY=...
GOOGLE_CSE_KEY=...
GOOGLE_CSE_CX=...

# Config
SESSION_TTL_SECONDS=7200
MAX_HISTORY_VERSIONS=20
MAX_VIDEO_SIZE_MB=200
FRAME_INTERVAL_SECONDS=1.0
MIN_FRAMES_COLMAP=30
MAX_FRAMES_COLMAP=80

# Pipeline quality thresholds
COLMAP_METRIC_THRESHOLD=0.70
COLMAP_PARTIAL_THRESHOLD=0.30
MIN_SPARSE_POINTS_METRIC=2000
MIN_SPARSE_POINTS_PARTIAL=500

ENV=development
CORS_ORIGINS=http://localhost:3000
```

### Backend `requirements.txt`

```
fastapi==0.110.0
uvicorn==0.29.0
python-multipart==0.0.9
httpx==0.27.0
anthropic==0.25.0
jsonschema==4.22.0
pydantic==2.7.0
python-dotenv==1.0.1
beautifulsoup4==4.12.3
aiofiles==23.2.1
numpy==1.26.4
```

---

## 17. Project Folder Structure

```
room-design-ai/
│
├── frontend/                         # Next.js app — unchanged
│   ├── components/
│   │   ├── correction/
│   │   │   ├── CorrectionPanel.tsx   # Shows confidence colours
│   │   │   └── ObjectRow.tsx         # Red/orange/green per confidence
│   │   ├── scene/
│   │   │   ├── SceneViewer.tsx
│   │   │   ├── ObjectMesh.tsx        # Dashed outline for low pos_confidence
│   │   │   └── ConfidenceBadge.tsx   # Floating label on uncertain objects
│   │   └── scan/
│   │       └── ScanProgress.tsx      # Shows pipeline tier: metric/partial/approx
│
├── backend/
│   ├── main.py
│   ├── routers/
│   │   ├── upload.py
│   │   ├── scan.py                   # Phase A: load_precomputed; Phase B: proxy
│   │   ├── scene.py
│   │   ├── agent.py
│   │   ├── undo.py
│   │   └── shop.py
│   ├── services/
│   │   ├── gpu_proxy.py              # Phase B: proxy to Colab worker
│   │   ├── scene_builder.py          # Fuse GPU outputs → SceneScript (all fixes)
│   │   ├── scene_validator.py        # Constraint checks
│   │   ├── design_agent.py           # Claude agent
│   │   └── product_search.py         # Search cascade
│   └── session/
│       └── store.py                  # Session dict + version history
│
├── gpu_worker/
│   ├── worker.py                     # Phase B Flask server (models load once)
│   ├── pipeline/
│   │   ├── frame_extractor.py        # Step 2
│   │   ├── colmap_runner.py          # Step 3
│   │   ├── colmap_aligner.py         # Step 4 (FIX 1) — floor-plane alignment
│   │   ├── depth_estimator.py        # Step 6 (FIX 2) — scale-shift per frame
│   │   ├── object_detector.py        # Step 7 — DINO + SAM
│   │   ├── object_instances.py       # Step 8 (FIX 4) — 2D-first lift to 3D
│   │   ├── object_fusion.py          # Step 9 (FIX 5) — 3D IoU merge
│   │   ├── geometry_fusion.py        # Step 10 (FIX 3) — correct conventions
│   │   └── opening_extractor.py      # Step 11 (FIX 6) — optional w/d
│   └── notebooks/
│       └── offline_pipeline.ipynb    # Phase A: run manually, save to disk
│
└── shared/
    └── scene_schema.json             # SceneScript v2 JSON schema
```

---

## 18. Complete API Contract

### POST /api/upload
Upload video + room dimensions.

**Request:** `multipart/form-data` — `file`, `room_width`, `room_depth`

**Response 200:**
```json
{ "session_id": "uuid", "status": "uploaded", "duration_seconds": 34 }
```

---

### POST /api/load_precomputed *(Phase A only)*
Load a pre-generated SceneScript without running the CV pipeline.

**Request:**
```json
{ "session_id": "uuid", "scene_path": "/outputs/session_001/scene.json" }
```

**Response 200:**
```json
{ "session_id": "uuid", "scene": {...SceneScript...}, "mode": "precomputed" }
```

---

### POST /api/scan *(Phase B)*
Trigger full CV pipeline on GPU worker.

**Response 200:**
```json
{
  "session_id": "uuid",
  "status": "complete",
  "pipeline_tier": "metric",
  "colmap_registration_ratio": 0.78,
  "scene": { ...SceneScript v2... },
  "warnings": []
}
```

**Fallback response:**
```json
{
  "session_id": "uuid",
  "status": "complete",
  "pipeline_tier": "approximate",
  "colmap_registration_ratio": 0.21,
  "scene": { ...SceneScript with confidence: approximate... },
  "warnings": ["colmap_failed: low_registration — using claude_vision_fallback"]
}
```

---

### GET /api/scan/status/{session_id}
Poll for pipeline progress.

**Response 200:**
```json
{
  "status": "processing",
  "stage": "depth_estimation",
  "stages_complete": ["frame_extraction", "colmap", "alignment"],
  "stages_remaining": ["depth_estimation", "detection", "fusion", "scenescript"],
  "pipeline_tier_so_far": "metric",
  "elapsed_seconds": 52
}
```

---

### POST /api/agent

**Request:**
```json
{
  "session_id": "uuid",
  "instruction": "Replace the sofa with a leather armchair",
  "selected_object_id": "obj_001"
}
```

**Response 200:**
```json
{
  "action": { "action": "replace", "object_id": "obj_001", ... },
  "scene": { ...updated SceneScript... },
  "message": "Replaced sofa with brown leather armchair."
}
```

---

### POST /api/scene/undo
**Request:** `{ "session_id": "uuid" }`
**Response 200:** `{ "scene": {...}, "version": 3 }`

---

### PUT /api/scene/correct
**Request:** `{ "session_id": "uuid", "scene": {...SceneScript v2...} }`
**Response 200:** `{ "scene": {...validated...}, "status": "confirmed" }`

---

### POST /api/shop/search
**Request:**
```json
{
  "object_type": "sofa",
  "color": "grey",
  "style": null,
  "max_width_m": 2.2,
  "max_depth_m": 0.9
}
```

**Response 200:**
```json
{
  "results": [...],
  "source": "serpapi",
  "size_filtered": true
}
```

---

### POST /api/shop/place
**Request:**
```json
{
  "session_id": "uuid",
  "object_id": "obj_001",
  "product": { "title": "...", "product_url": "...", "dimensions_parsed": {...} }
}
```

**Response 200:** `{ "scene": {...updated SceneScript...} }`

---

## 19. Build Order by Milestone

### Milestone 1 — Point Cloud (offline)

- [ ] Frame extraction (OpenCV, sharpness filter)
- [ ] COLMAP runner (`subprocess` + `pycolmap`)
- [ ] Floor-plane alignment (FIX 1)
- [ ] Quality gate: metric / partial / approximate classification
- [ ] Test on 3 real rooms — must register >= 70% frames on 2 of 3
- [ ] Save camera poses + sparse points to disk

**Do not proceed until Step above produces good output on real rooms.**

---

### Milestone 2 — SceneScript (offline)

- [ ] Depth Anything V2 inference + per-frame scale-shift alignment (FIX 2)
- [ ] Coordinate convention function (FIX 3) — document and test explicitly
- [ ] GroundingDINO + SAM detection per frame
- [ ] 2D-first object lifting to 3D (FIX 4)
- [ ] Multi-frame IoU fusion (FIX 5)
- [ ] Open3D floor + wall plane fitting (for room geometry only, not object segmentation)
- [ ] Window/door extraction as optional + confidence-scored (FIX 6)
- [ ] SceneScript v2 generation with deep confidence (FIX 10)
- [ ] SceneScript validator (floor anchor, bounds, overlap, version)
- [ ] Save scene.json to disk
- [ ] Test: SceneScript positions match visual inspection of point cloud

---

### Milestone 3 — 3D Interface

- [ ] POST /api/load_precomputed — load pre-generated scene.json
- [ ] Three.js canvas: room geometry, object meshes, GLTF + box fallback
- [ ] Confidence-driven visual indicators (FIX 10 UI)
- [ ] Correction UI with red/orange/green confidence colours
- [ ] Hover (500ms dwell) + click selection + ActionPanel
- [ ] Confirm Room → chat unlocks

---

### Milestone 4 — Agent

- [ ] Claude labelling prompt
- [ ] Claude design agent prompt + action schemas
- [ ] All action types: replace, move, add, remove, restyle, update
- [ ] SceneScript versioning + undo
- [ ] Partial re-render (only changed object IDs)

---

### Milestone 5 — Shop

- [ ] POST /api/shop/search with size filter
- [ ] Product results panel UI
- [ ] POST /api/shop/place
- [ ] Product dimensions in SceneScript after placement
- [ ] Buy Now link on hover for placed products

---

### Milestone 6 — Live Pipeline (Phase B)

- [ ] Flask worker on Colab — models load ONCE at startup (FIX 7)
- [ ] ngrok tunnel URL logged at startup
- [ ] POST /api/scan proxy to GPU worker
- [ ] ScanProgress UI with pipeline tier indicator
- [ ] Three-tier fallback working end-to-end

---

## 20. Demo Fallback SceneScript

Load this immediately if video scan fails during the live presentation.
All agent + shop features work identically on this scene.

```json
{
  "version": 2,
  "session_id": "demo",
  "source": "demo",
  "pipeline_mode": "demo",
  "room": {
    "width": 4.5, "width_confidence": 1.0,
    "depth": 5.5, "depth_confidence": 1.0,
    "height": 2.8, "height_confidence": 1.0,
    "floor_plane": [0, 1, 0, 0],
    "floor_plane_inlier_ratio": 1.0
  },
  "walls": [
    { "id": "wall_north", "x1": 0,   "z1": 0,   "x2": 4.5, "z2": 0,   "confidence": 1.0 },
    { "id": "wall_south", "x1": 0,   "z1": 5.5, "x2": 4.5, "z2": 5.5, "confidence": 1.0 },
    { "id": "wall_east",  "x1": 4.5, "z1": 0,   "x2": 4.5, "z2": 5.5, "confidence": 1.0 },
    { "id": "wall_west",  "x1": 0,   "z1": 0,   "x2": 0,   "z2": 5.5, "confidence": 1.0 }
  ],
  "windows": [
    { "id": "win_001", "wall": "wall_north", "x": 1.4, "width": 1.2,
      "height": 1.1, "sill_height": 0.9, "confidence": 1.0, "user_confirmed": true }
  ],
  "doors": [
    { "id": "door_001", "wall": "wall_west", "x": 0.5, "width": 0.9,
      "height": 2.1, "confidence": 1.0, "user_confirmed": true }
  ],
  "objects": [
    {
      "id": "obj_001", "type": "sofa",
      "type_confidence": 1.0, "position_confidence": 1.0,
      "size_confidence": 1.0, "rotation_confidence": 1.0,
      "label_confirmed": true,
      "position": { "x": 1.2, "y": 0.0, "z": 0.6 },
      "size": { "w": 2.2, "h": 0.85, "d": 0.9 },
      "rotation_y": 0, "color": "grey",
      "product_url": null, "product_name": null
    },
    {
      "id": "obj_002", "type": "coffee_table",
      "type_confidence": 1.0, "position_confidence": 1.0,
      "size_confidence": 1.0, "rotation_confidence": 1.0,
      "label_confirmed": true,
      "position": { "x": 1.5, "y": 0.0, "z": 1.8 },
      "size": { "w": 1.0, "h": 0.45, "d": 0.6 },
      "rotation_y": 0, "color": "brown",
      "product_url": null, "product_name": null
    },
    {
      "id": "obj_003", "type": "tv_unit",
      "type_confidence": 1.0, "position_confidence": 1.0,
      "size_confidence": 1.0, "rotation_confidence": 1.0,
      "label_confirmed": true,
      "position": { "x": 2.0, "y": 0.0, "z": 4.9 },
      "size": { "w": 1.6, "h": 0.5, "d": 0.45 },
      "rotation_y": 0, "color": "black",
      "product_url": null, "product_name": null
    },
    {
      "id": "obj_004", "type": "armchair",
      "type_confidence": 1.0, "position_confidence": 1.0,
      "size_confidence": 1.0, "rotation_confidence": 1.0,
      "label_confirmed": true,
      "position": { "x": 3.5, "y": 0.0, "z": 0.8 },
      "size": { "w": 0.8, "h": 0.85, "d": 0.8 },
      "rotation_y": 270, "color": "beige",
      "product_url": null, "product_name": null
    },
    {
      "id": "obj_005", "type": "plant",
      "type_confidence": 1.0, "position_confidence": 1.0,
      "size_confidence": 1.0, "rotation_confidence": 0.4,
      "label_confirmed": true,
      "position": { "x": 4.1, "y": 0.0, "z": 0.4 },
      "size": { "w": 0.4, "h": 1.0, "d": 0.4 },
      "rotation_y": 0, "color": "green",
      "product_url": null, "product_name": null
    }
  ],
  "metadata": {
    "room_type": "living_room", "room_type_confidence": 1.0,
    "pipeline_version": "demo", "confidence": "demo",
    "created_at": "2025-01-01T00:00:00Z",
    "last_edited": "2025-01-01T00:00:00Z"
  }
}
```

---

## 21. Final Summary

### The 10 fixes in one table

| # | Was | Now |
|---|---|---|
| 1 | Scale from point X/Z ranges | Scale from floor-plane-aligned wall extents using percentiles |
| 2 | `metric = constant / depth_raw` | Per-frame scale-shift solved by least squares using COLMAP anchors |
| 3 | `y_vals` undefined + no convention docs | All conventions explicit in docstring; Y-flip documented and applied |
| 4 | DBSCAN → then match to labels | 2D-first: SAM mask → lift to 3D using depth → label already attached |
| 5 | Project cluster centre to check DINO box | 3D IoU across per-frame candidates + union-find merge |
| 6 | Windows/doors assumed reliable | Optional, confidence-scored, not rendered below threshold, not used for room shell |
| 7 | Colab + ngrok from day one | Phase A: offline notebook first; Phase B: live API only after pipeline validated |
| 8 | COLMAP failure is rare | Three-tier quality system: metric / partial / approximate; failure is normal |
| 9 | Everything at once | Five milestones in strict order; no shopping before geometry is stable |
| 10 | Single confidence string | Per-field confidence on every measurement, drives UI and rendering |

### The one thing that stays the same

**The SceneScript is still the memory, the contract, and the heart of everything.**
Every fix improves how the SceneScript is produced. Once it exists, the rendering,
agent, and shopping layers work exactly as before.

> **Build the offline pipeline first. Make sure it produces a correct SceneScript
> on real rooms. Then build the UI. Then build the agent. Then build the shop.
> The geometry has to be right before anything else matters.**

---

*AI-Powered 3D Room Design System — Corrected Implementation Plan v3 — 2025*
