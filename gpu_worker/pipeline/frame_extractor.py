from __future__ import annotations

from pathlib import Path

import cv2


def _compute_sharpness(frame) -> float:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def extract_frames(
    video_path: str,
    output_dir: str,
    interval_sec: float = 1.0,
    max_frames: int = 80,
    min_sharpness: float = 50.0,
) -> list[dict]:
    """Extract sharp frames for SfM-friendly reconstruction.

    Returns frame metadata list with output path and quality values.
    """
    input_path = Path(video_path)
    if not input_path.exists() or not input_path.is_file():
        raise FileNotFoundError(f"Video not found: {video_path}")

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(input_path))
    if not cap.isOpened():
        raise RuntimeError(f"Unable to open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0

    interval_frames = max(1, int(round(fps * interval_sec)))
    frame_idx = 0
    saved: list[dict] = []

    while cap.isOpened() and len(saved) < max_frames:
        ok, frame = cap.read()
        if not ok:
            break

        if frame_idx % interval_frames != 0:
            frame_idx += 1
            continue

        sharpness = _compute_sharpness(frame)
        if sharpness < min_sharpness:
            frame_idx += 1
            continue

        out_name = f"frame_{len(saved):04d}.jpg"
        out_path = out_dir / out_name
        cv2.imwrite(str(out_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])

        saved.append(
            {
                "name": out_name,
                "path": str(out_path),
                "frame_idx": frame_idx,
                "timestamp_sec": frame_idx / fps,
                "sharpness": sharpness,
            }
        )
        frame_idx += 1

    cap.release()

    if len(saved) < 5:
        raise RuntimeError("Too few usable frames extracted. Re-capture with better lighting and slower movement.")

    return saved
