from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from data.demo_scene import get_demo_scene
from services.scene_builder import (
    build_scene_from_m1,
    build_scene_from_m2,
    build_scene_from_precomputed,
    collect_m1_warnings,
    collect_m2_warnings,
)
from services.scene_validator import validate_scene
from session.store import session_store

router = APIRouter(tags=["scan"])


class LoadPrecomputedRequest(BaseModel):
    session_id: str
    scene_path: str | None = None


class LoadM1Request(BaseModel):
    session_id: str
    summary_path: str
    aligned_payload_path: str


class LoadM2Request(BaseModel):
    session_id: str
    summary_path: str
    aligned_payload_path: str
    m2_result_path: str


@router.post("/api/load_precomputed")
def load_precomputed(payload: LoadPrecomputedRequest) -> dict:
    if payload.scene_path:
        path = Path(payload.scene_path)
        if not path.exists() or not path.is_file():
            raise HTTPException(status_code=404, detail="scene_path not found")
        with path.open("r", encoding="utf-8") as f:
            scene_raw = json.load(f)
        if "session_id" not in scene_raw:
            scene_raw["session_id"] = payload.session_id
    else:
        scene_raw = get_demo_scene(session_id=payload.session_id)

    built_scene = build_scene_from_precomputed(scene_raw)
    valid_scene = validate_scene(built_scene)
    session_store.create_from_scene(payload.session_id, valid_scene)

    return {
        "session_id": payload.session_id,
        "scene": valid_scene,
        "mode": "precomputed",
    }


@router.post("/api/load_m1")
def load_m1(payload: LoadM1Request) -> dict:
    summary_file = Path(payload.summary_path)
    aligned_file = Path(payload.aligned_payload_path)

    if not summary_file.exists() or not summary_file.is_file():
        raise HTTPException(status_code=404, detail="summary_path not found")
    if not aligned_file.exists() or not aligned_file.is_file():
        raise HTTPException(status_code=404, detail="aligned_payload_path not found")

    with summary_file.open("r", encoding="utf-8") as f:
        m1_summary = json.load(f)
    with aligned_file.open("r", encoding="utf-8") as f:
        m1_aligned = json.load(f)

    scene_raw = build_scene_from_m1(
        session_id=payload.session_id,
        m1_summary=m1_summary,
        m1_aligned_payload=m1_aligned,
    )
    warnings = collect_m1_warnings(m1_summary, m1_aligned)
    valid_scene = validate_scene(scene_raw)
    session_store.create_from_scene(payload.session_id, valid_scene)

    return {
        "session_id": payload.session_id,
        "scene": valid_scene,
        "mode": "m1_import",
        "pipeline_tier": valid_scene.get("metadata", {}).get("confidence", "approximate"),
        "warnings": warnings,
        "diagnostics": {
            "num_objects_proposed": len(valid_scene.get("objects", [])),
            "registration_ratio": valid_scene.get("metadata", {}).get("m1_registration_ratio", 0.0),
            "num_sparse_points": valid_scene.get("metadata", {}).get("m1_num_sparse_points", 0),
        },
    }


@router.post("/api/load_m2")
def load_m2(payload: LoadM2Request) -> dict:
    summary_file = Path(payload.summary_path)
    aligned_file = Path(payload.aligned_payload_path)
    m2_file = Path(payload.m2_result_path)

    if not summary_file.exists() or not summary_file.is_file():
        raise HTTPException(status_code=404, detail="summary_path not found")
    if not aligned_file.exists() or not aligned_file.is_file():
        raise HTTPException(status_code=404, detail="aligned_payload_path not found")
    if not m2_file.exists() or not m2_file.is_file():
        raise HTTPException(status_code=404, detail="m2_result_path not found")

    with summary_file.open("r", encoding="utf-8") as f:
        m1_summary = json.load(f)
    with aligned_file.open("r", encoding="utf-8") as f:
        m1_aligned = json.load(f)
    with m2_file.open("r", encoding="utf-8") as f:
        m2_result = json.load(f)

    scene_raw = build_scene_from_m2(
        session_id=payload.session_id,
        m1_summary=m1_summary,
        m1_aligned_payload=m1_aligned,
        m2_result=m2_result,
    )

    warnings = collect_m1_warnings(m1_summary, m1_aligned)
    warnings.extend(collect_m2_warnings(m2_result))

    valid_scene = validate_scene(scene_raw)
    session_store.create_from_scene(payload.session_id, valid_scene)

    return {
        "session_id": payload.session_id,
        "scene": valid_scene,
        "mode": "m2_import",
        "pipeline_tier": valid_scene.get("metadata", {}).get("confidence", "approximate"),
        "warnings": warnings,
        "diagnostics": {
            "num_objects": len(valid_scene.get("objects", [])),
            "num_windows": len(valid_scene.get("windows", [])),
            "num_doors": len(valid_scene.get("doors", [])),
            "m2_detection_frames": valid_scene.get("metadata", {}).get("m2_detection_frames", 0),
            "m2_fused_objects": valid_scene.get("metadata", {}).get("m2_fused_objects", 0),
        },
    }


@router.get("/api/scan/status/{session_id}")
def scan_status(session_id: str) -> dict:
    state = session_store.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    has_scene = state.scene is not None
    return {
        "session_id": session_id,
        "status": "complete" if has_scene else "waiting",
        "stage": "scenescript_ready" if has_scene else "upload_pending",
        "pipeline_tier_so_far": "demo" if has_scene else "unknown",
        "elapsed_seconds": 0,
    }
