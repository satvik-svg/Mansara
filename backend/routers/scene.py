from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.scene_validator import validate_scene
from session.store import session_store

router = APIRouter(tags=["scene"])


class CorrectSceneRequest(BaseModel):
    session_id: str
    scene: dict


@router.get("/api/scene/{session_id}")
def get_scene(session_id: str) -> dict:
    state = session_store.get(session_id)
    if not state or state.scene is None:
        raise HTTPException(status_code=404, detail="Scene not found")
    return {"scene": state.scene, "version": state.version}


@router.put("/api/scene/correct")
def correct_scene(payload: CorrectSceneRequest) -> dict:
    state = session_store.get(payload.session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    valid_scene = validate_scene(payload.scene)
    version = session_store.update_scene(payload.session_id, valid_scene, push_history=True)
    return {"scene": valid_scene, "status": "confirmed", "version": version}
