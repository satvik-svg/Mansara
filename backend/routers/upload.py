from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import aiofiles
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from session.store import session_store

router = APIRouter(tags=["upload"])


@router.post("/api/upload")
async def upload_video(
    file: UploadFile = File(...),
    room_width: float = Form(...),
    room_depth: float = Form(...),
) -> dict:
    ext = Path(file.filename or "video.mp4").suffix.lower()
    if ext not in {".mp4", ".mov", ".avi", ".webm"}:
        raise HTTPException(status_code=400, detail="Unsupported video type")

    session_id = str(uuid4())
    out_dir = Path("tmp") / session_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"video{ext}"

    async with aiofiles.open(out_path, "wb") as f:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            await f.write(chunk)

    session_store.create_empty(
        session_id=session_id,
        room_width=room_width,
        room_depth=room_depth,
        video_path=str(out_path),
    )

    return {
        "session_id": session_id,
        "status": "uploaded",
        "duration_seconds": 0,
        "video_path": str(out_path),
    }
