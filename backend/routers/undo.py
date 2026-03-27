from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from session.store import session_store

router = APIRouter(tags=["undo"])


class UndoRequest(BaseModel):
    session_id: str


@router.post("/api/scene/undo")
def undo_scene(payload: UndoRequest) -> dict:
    try:
        scene, version = session_store.undo(payload.session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"scene": scene, "version": version}
