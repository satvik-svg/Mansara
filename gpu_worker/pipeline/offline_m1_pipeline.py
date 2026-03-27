from __future__ import annotations

import argparse
import json
from pathlib import Path

from colmap_aligner import align_colmap_output
from colmap_runner import run_colmap
from frame_extractor import extract_frames


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _lightweight_colmap_summary(colmap_result: dict) -> dict:
    return {
        "success": colmap_result.get("success", False),
        "database_path": colmap_result.get("database_path"),
        "sparse_model_path": colmap_result.get("sparse_model_path"),
        "num_frames": colmap_result.get("num_frames", 0),
        "num_images_registered": colmap_result.get("num_images_registered", 0),
        "registration_ratio": colmap_result.get("registration_ratio", 0.0),
        "num_sparse_points": colmap_result.get("num_sparse_points", 0),
    }


def run_m1_pipeline(
    video_path: str,
    output_dir: str,
    room_width: float,
    room_depth: float,
    interval_sec: float,
    max_frames: int,
    min_sharpness: float,
    use_gpu: bool,
) -> dict:
    base = Path(output_dir)
    frames_dir = base / "frames"
    colmap_dir = base / "colmap"

    frames = extract_frames(
        video_path=video_path,
        output_dir=str(frames_dir),
        interval_sec=interval_sec,
        max_frames=max_frames,
        min_sharpness=min_sharpness,
    )

    colmap_result = run_colmap(
        frames_dir=str(frames_dir),
        output_dir=str(colmap_dir),
        use_gpu=use_gpu,
    )

    alignment = align_colmap_output(
        colmap_result=colmap_result,
        room_width=room_width,
        room_depth=room_depth,
    )

    summary = {
        "stage": "m1_complete",
        "video_path": video_path,
        "output_dir": str(base),
        "frame_count": len(frames),
        "frames": frames,
        "colmap": _lightweight_colmap_summary(colmap_result),
        "alignment": {
            "pipeline_tier": alignment.get("pipeline_tier"),
            "scale_factor": alignment.get("scale_factor"),
            "floor_plane_inlier_ratio": alignment.get("floor_plane_inlier_ratio"),
            "estimated_spans": alignment.get("estimated_spans"),
            "quality": alignment.get("quality"),
        },
    }

    _write_json(base / "m1_summary.json", summary)
    _write_json(base / "m1_aligned_payload.json", alignment)

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Milestone 1 offline reconstruction pipeline")
    parser.add_argument("--video", required=True, help="Input room scan video path")
    parser.add_argument("--output", required=True, help="Output folder for Milestone 1 artifacts")
    parser.add_argument("--room-width", required=True, type=float, help="Approx room width in meters")
    parser.add_argument("--room-depth", required=True, type=float, help="Approx room depth in meters")
    parser.add_argument("--interval-sec", type=float, default=1.0)
    parser.add_argument("--max-frames", type=int, default=80)
    parser.add_argument("--min-sharpness", type=float, default=50.0)
    parser.add_argument("--cpu", action="store_true", help="Force CPU mode for COLMAP SIFT")
    args = parser.parse_args()

    summary = run_m1_pipeline(
        video_path=args.video,
        output_dir=args.output,
        room_width=args.room_width,
        room_depth=args.room_depth,
        interval_sec=args.interval_sec,
        max_frames=args.max_frames,
        min_sharpness=args.min_sharpness,
        use_gpu=not args.cpu,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
