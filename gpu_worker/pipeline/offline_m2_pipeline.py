from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from depth_estimator import DepthEstimator
from geometry_fusion import fuse_geometry
from object_detector import detect_objects
from object_fusion import fuse_per_frame_objects
from object_instances import lift_detections_to_3d
from opening_extractor import extract_openings


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _resolve_frame_path(frame_meta: dict, frames_dir: Path) -> Path | None:
    name = frame_meta.get("name")
    if name:
        p = frames_dir / str(name)
        if p.exists():
            return p

    path_from_meta = frame_meta.get("path")
    if path_from_meta:
        p = Path(str(path_from_meta))
        if p.exists():
            return p
        # Try remapping old absolute path to local frames dir by basename.
        p2 = frames_dir / p.name
        if p2.exists():
            return p2

    return None


def run_m2_pipeline(
    m1_output_dir: str,
    summary_path: str | None = None,
    aligned_payload_path: str | None = None,
    output_path: str | None = None,
) -> dict:
    base_dir = Path(m1_output_dir)
    if not base_dir.exists() or not base_dir.is_dir():
        raise FileNotFoundError(f"m1_output_dir not found: {m1_output_dir}")

    summary_file = Path(summary_path) if summary_path else base_dir / "m1_summary.json"
    aligned_file = Path(aligned_payload_path) if aligned_payload_path else base_dir / "m1_aligned_payload.json"
    if not summary_file.exists():
        raise FileNotFoundError(f"m1_summary file not found: {summary_file}")
    if not aligned_file.exists():
        raise FileNotFoundError(f"m1_aligned_payload file not found: {aligned_file}")

    summary = _load_json(summary_file)
    aligned = _load_json(aligned_file)

    frames_dir = base_dir / "frames"
    camera_poses = aligned.get("camera_poses", {})
    sparse_points = np.asarray(aligned.get("aligned_sparse_points", []), dtype=np.float64)

    estimator = DepthEstimator()

    per_frame_candidates: list[list[dict]] = []
    detections_by_frame: dict[str, list[dict]] = {}
    used_points_clouds: list[np.ndarray] = []
    processed_frames = 0

    for frame_meta in summary.get("frames", []):
        frame_name = str(frame_meta.get("name", ""))
        if not frame_name or frame_name not in camera_poses:
            continue

        frame_path = _resolve_frame_path(frame_meta, frames_dir)
        if frame_path is None:
            continue

        detections = detect_objects(str(frame_path))
        detections_by_frame[frame_name] = detections

        if not detections:
            continue

        pose = camera_poses[frame_name]
        depth_relative = estimator.predict_relative(str(frame_path))
        depth_metric, _, _ = estimator.align_to_metric(depth_relative, sparse_points, pose)

        candidates = lift_detections_to_3d(
            detections=detections,
            depth_metric=depth_metric,
            camera_pose=pose,
            frame_name=frame_name,
        )
        if candidates:
            per_frame_candidates.append(candidates)
            for c in candidates:
                pts = c.get("points_world")
                if isinstance(pts, np.ndarray) and pts.ndim == 2 and pts.shape[1] >= 3:
                    used_points_clouds.append(pts[:, :3])
        processed_frames += 1

    fused_objects = fuse_per_frame_objects(per_frame_candidates)

    geometry_input = []
    if sparse_points.size > 0:
        geometry_input.append(sparse_points[:, :3])
    geometry_input.extend(used_points_clouds)
    geometry = fuse_geometry(geometry_input)

    windows = extract_openings(detections_by_frame, "window")
    doors = extract_openings(detections_by_frame, "door")

    result = {
        "stage": "m2_complete",
        "source": "m2_minimal",
        "m1_summary_path": str(summary_file),
        "m1_aligned_payload_path": str(aligned_file),
        "processed_frames": processed_frames,
        "num_detection_frames": len([v for v in detections_by_frame.values() if v]),
        "objects": fused_objects,
        "windows": windows,
        "doors": doors,
        "geometry": geometry,
        "diagnostics": {
            "input_frame_count": int(summary.get("frame_count", 0)),
            "camera_poses": len(camera_poses),
            "sparse_points": int(sparse_points.shape[0]) if sparse_points.ndim == 2 else 0,
            "object_candidates": int(sum(len(x) for x in per_frame_candidates)),
            "fused_objects": len(fused_objects),
        },
    }

    output_file = Path(output_path) if output_path else base_dir / "m2_result.json"
    _write_json(output_file, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Milestone 2 minimal offline object extraction pipeline")
    parser.add_argument("--m1-output-dir", required=True, help="Directory containing M1 artifacts (frames + m1_summary + m1_aligned_payload)")
    parser.add_argument("--summary-path", default=None, help="Optional explicit path to m1_summary.json")
    parser.add_argument("--aligned-payload-path", default=None, help="Optional explicit path to m1_aligned_payload.json")
    parser.add_argument("--output-path", default=None, help="Optional output path for m2_result.json")
    args = parser.parse_args()

    result = run_m2_pipeline(
        m1_output_dir=args.m1_output_dir,
        summary_path=args.summary_path,
        aligned_payload_path=args.aligned_payload_path,
        output_path=args.output_path,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
