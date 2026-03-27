from __future__ import annotations

from fastapi import APIRouter, HTTPException

from models.agent_action import AgentRequest, AgentResponse
from services.design_agent import apply_instruction
from services.scene_validator import validate_scene
from session.store import session_store

router = APIRouter(tags=["agent"])


@router.post("/api/agent", response_model=AgentResponse)
def run_agent(payload: AgentRequest) -> AgentResponse:
    current_scene = session_store.get_scene(payload.session_id)
    if current_scene is None:
        raise HTTPException(status_code=404, detail="Scene not found")

    new_scene, action, message = apply_instruction(
        current_scene,
        instruction=payload.instruction,
        selected_object_id=payload.selected_object_id,
    )
    valid_scene = validate_scene(new_scene)
    session_store.update_scene(payload.session_id, valid_scene, push_history=True)

    return AgentResponse(action=action, scene=valid_scene, message=message)
