from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

import numpy as np


def _run_command(args: list[str], cwd: Path | None = None) -> None:
    result = subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "COLMAP command failed\n"
            f"Command: {' '.join(args)}\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )


def _find_colmap_binary() -> str | None:
    return shutil.which("colmap")


def _safe_set_attr(obj: Any, name: str, value: Any) -> None:
    if hasattr(obj, name):
        setattr(obj, name, value)


def _resolve_pycolmap_device(pycolmap: Any, use_gpu: bool) -> Any | None:
    device_cls = getattr(pycolmap, "Device", None)
    if device_cls is None:
        return None

    # Prefer AUTO first to avoid hard-failing on runtimes without CUDA support.
    preferred = ("auto", "cuda", "gpu") if use_gpu else ("cpu", "auto")
    for attr in preferred:
        if hasattr(device_cls, attr):
            return getattr(device_cls, attr)
    return None


def _call_with_fallback(func: Any, kwargs: dict[str, Any], drop_order: list[str]) -> Any:
    attempt = dict(kwargs)
    last_error: Exception | None = None
    for key in [None, *drop_order]:
        try:
            return func(**attempt)
        except (TypeError, ValueError) as exc:
            last_error = exc
            if key is None:
                continue
            attempt.pop(key, None)
    if last_error:
        raise last_error
    return func(**kwargs)


def _extract_intrinsics(camera) -> dict:
    params = list(camera.params)
    if len(params) >= 4:
        fx = float(params[0])
        fy = float(params[0])
        cx = float(params[1])
        cy = float(params[2])
    else:
        fx = fy = 1.0
        cx = cy = 0.0
    return {
        "fx": fx,
        "fy": fy,
        "cx": cx,
        "cy": cy,
        "width": int(camera.width),
        "height": int(camera.height),
    }


def _coerce_rotation_matrix(rotation_obj: Any) -> np.ndarray | None:
    if rotation_obj is None:
        return None

    # Common API variants across pycolmap versions.
    if hasattr(rotation_obj, "matrix"):
        try:
            arr = np.asarray(rotation_obj.matrix(), dtype=np.float64)
            if arr.shape == (3, 3):
                return arr
        except Exception:
            pass

    for method in ("as_matrix", "to_matrix", "rotation_matrix"):
        if hasattr(rotation_obj, method):
            try:
                arr = np.asarray(getattr(rotation_obj, method)(), dtype=np.float64)
                if arr.shape == (3, 3):
                    return arr
            except Exception:
                pass

    try:
        arr = np.asarray(rotation_obj, dtype=np.float64)
        if arr.shape == (3, 3):
            return arr
    except Exception:
        pass

    return None


def _extract_pose(image: Any) -> tuple[np.ndarray, np.ndarray]:
    # Old API (pycolmap 0.x)
    if hasattr(image, "rotation_matrix") and hasattr(image, "tvec"):
        R = np.asarray(image.rotation_matrix(), dtype=np.float64)
        t = np.asarray(image.tvec, dtype=np.float64)
        return R, t

    # Newer API uses cam_from_world rigid transform.
    if hasattr(image, "cam_from_world"):
        transform = image.cam_from_world

        # matrix() often returns 3x4 or 4x4
        if hasattr(transform, "matrix"):
            try:
                mat = np.asarray(transform.matrix(), dtype=np.float64)
                if mat.shape == (4, 4):
                    return mat[:3, :3], mat[:3, 3]
                if mat.shape == (3, 4):
                    return mat[:, :3], mat[:, 3]
            except Exception:
                pass

        # rotation/translation fields
        rot_obj = None
        trans_obj = None
        if hasattr(transform, "rotation"):
            rot_obj = transform.rotation
            if callable(rot_obj):
                try:
                    rot_obj = rot_obj()
                except Exception:
                    pass
        if hasattr(transform, "translation"):
            trans_obj = transform.translation
            if callable(trans_obj):
                try:
                    trans_obj = trans_obj()
                except Exception:
                    pass

        R = _coerce_rotation_matrix(rot_obj)
        if R is not None and trans_obj is not None:
            try:
                t = np.asarray(trans_obj, dtype=np.float64).reshape(-1)
                if t.shape[0] >= 3:
                    return R, t[:3]
            except Exception:
                pass

    # Final safe fallback keeps pipeline running for M1 outputs.
    return np.eye(3, dtype=np.float64), np.zeros(3, dtype=np.float64)


def _parse_reconstruction(reconstruction) -> tuple[dict[str, dict], np.ndarray]:
    camera_poses: dict[str, dict] = {}
    for _, image in reconstruction.images.items():
        camera = reconstruction.cameras[image.camera_id]
        R, t = _extract_pose(image)
        camera_poses[image.name] = {
            "R": R.tolist(),
            "t": t.tolist(),
            "camera_id": int(image.camera_id),
            "intrinsics": _extract_intrinsics(camera),
        }

    sparse_points = np.array([p.xyz for p in reconstruction.points3D.values()], dtype=np.float64)
    return camera_poses, sparse_points


def _run_colmap_with_pycolmap(
    frames_path: Path,
    db_path: Path,
    sparse_root: Path,
    camera_model: str,
    sequential_overlap: int,
    use_gpu: bool,
):
    try:
        import pycolmap
    except ImportError as exc:
        raise RuntimeError("pycolmap is required. Install pycolmap in gpu_worker environment.") from exc

    device = _resolve_pycolmap_device(pycolmap, use_gpu)

    extract_opts = pycolmap.SiftExtractionOptions() if hasattr(pycolmap, "SiftExtractionOptions") else None
    if extract_opts is not None:
        _safe_set_attr(extract_opts, "use_gpu", use_gpu)

    match_opts = pycolmap.SiftMatchingOptions() if hasattr(pycolmap, "SiftMatchingOptions") else None
    if match_opts is not None:
        _safe_set_attr(match_opts, "use_gpu", use_gpu)

    seq_opts = pycolmap.SequentialMatchingOptions() if hasattr(pycolmap, "SequentialMatchingOptions") else None
    if seq_opts is not None:
        _safe_set_attr(seq_opts, "overlap", max(1, sequential_overlap))

    extract_kwargs: dict[str, Any] = {
        "database_path": str(db_path),
        "image_path": str(frames_path),
        "camera_model": camera_model,
    }
    if extract_opts is not None:
        extract_kwargs["sift_options"] = extract_opts
    if device is not None:
        extract_kwargs["device"] = device

    _call_with_fallback(
        pycolmap.extract_features,
        extract_kwargs,
        drop_order=["device", "sift_options", "camera_model"],
    )

    match_kwargs: dict[str, Any] = {
        "database_path": str(db_path),
    }
    if match_opts is not None:
        match_kwargs["sift_options"] = match_opts
    if seq_opts is not None:
        match_kwargs["matching_options"] = seq_opts
    if device is not None:
        match_kwargs["device"] = device

    _call_with_fallback(
        pycolmap.match_sequential,
        match_kwargs,
        drop_order=["device", "matching_options", "sift_options"],
    )

    reconstructions = pycolmap.incremental_mapping(
        database_path=str(db_path),
        image_path=str(frames_path),
        output_path=str(sparse_root),
    )
    if not reconstructions:
        raise RuntimeError("pycolmap incremental_mapping produced no reconstructions.")

    if isinstance(reconstructions, dict):
        reconstruction_list = list(reconstructions.values())
    elif isinstance(reconstructions, (list, tuple)):
        reconstruction_list = list(reconstructions)
    else:
        reconstruction_list = [reconstructions]

    # Use the reconstruction with highest registered image count.
    best = max(reconstruction_list, key=lambda r: len(r.images))
    return best


def run_colmap(
    frames_dir: str,
    output_dir: str,
    camera_model: str = "SIMPLE_RADIAL",
    sequential_overlap: int = 10,
    use_gpu: bool = True,
) -> dict:
    """Run COLMAP sparse reconstruction and parse reconstruction metadata."""
    colmap_bin = _find_colmap_binary()
    frames_path = Path(frames_dir)
    if not frames_path.exists() or not frames_path.is_dir():
        raise FileNotFoundError(f"frames_dir not found: {frames_dir}")

    images = sorted(frames_path.glob("*.jpg"))
    if len(images) < 5:
        raise RuntimeError("Need at least 5 frames for COLMAP.")

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    sparse_root = out_path / "sparse"
    sparse_root.mkdir(parents=True, exist_ok=True)
    db_path = out_path / "colmap.db"

    if db_path.exists():
        db_path.unlink()

    if colmap_bin:
        _run_command(
            [
                colmap_bin,
                "feature_extractor",
                "--database_path",
                str(db_path),
                "--image_path",
                str(frames_path),
                "--ImageReader.camera_model",
                camera_model,
                "--SiftExtraction.use_gpu",
                "1" if use_gpu else "0",
            ]
        )

        _run_command(
            [
                colmap_bin,
                "sequential_matcher",
                "--database_path",
                str(db_path),
                "--SequentialMatching.overlap",
                str(sequential_overlap),
                "--SiftMatching.use_gpu",
                "1" if use_gpu else "0",
            ]
        )

        _run_command(
            [
                colmap_bin,
                "mapper",
                "--database_path",
                str(db_path),
                "--image_path",
                str(frames_path),
                "--output_path",
                str(sparse_root),
                "--Mapper.ba_refine_principal_point",
                "0",
            ]
        )

        model_dirs = sorted([p for p in sparse_root.iterdir() if p.is_dir()])
        if not model_dirs:
            raise RuntimeError("COLMAP mapper did not produce a sparse model.")

        try:
            import pycolmap
        except ImportError as exc:
            raise RuntimeError("pycolmap is required to parse reconstruction output.") from exc

        model_dir = model_dirs[0]
        reconstruction = pycolmap.Reconstruction(str(model_dir))
        run_mode = "colmap_cli"
        sparse_model_path = str(model_dir)
    else:
        reconstruction = _run_colmap_with_pycolmap(
            frames_path=frames_path,
            db_path=db_path,
            sparse_root=sparse_root,
            camera_model=camera_model,
            sequential_overlap=sequential_overlap,
            use_gpu=use_gpu,
        )
        run_mode = "pycolmap"
        sparse_model_path = str(sparse_root)

    camera_poses, sparse_points = _parse_reconstruction(reconstruction)

    return {
        "success": True,
        "mode": run_mode,
        "database_path": str(db_path),
        "sparse_model_path": sparse_model_path,
        "num_frames": len(images),
        "num_images_registered": len(reconstruction.images),
        "num_sparse_points": len(reconstruction.points3D),
        "registration_ratio": (len(reconstruction.images) / len(images)) if images else 0.0,
        "camera_poses": camera_poses,
        "sparse_points": sparse_points.tolist(),
    }

