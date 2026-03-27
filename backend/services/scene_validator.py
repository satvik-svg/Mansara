from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from jsonschema import validate

from models.scene_script import SceneScript


@lru_cache(maxsize=1)
def _load_schema() -> dict:
    root = Path(__file__).resolve().parents[2]
    schema_path = root / "shared" / "scene_schema.json"
    with schema_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_scene(scene: dict) -> dict:
    schema = _load_schema()
    validate(instance=scene, schema=schema)

    parsed = SceneScript.model_validate(scene)

    room_w = parsed.room.width
    room_d = parsed.room.depth
    for obj in parsed.objects:
        if not (0.0 <= obj.position.x <= room_w):
            raise ValueError(f"Object {obj.id} out of room bounds on X axis")
        if not (0.0 <= obj.position.z <= room_d):
            raise ValueError(f"Object {obj.id} out of room bounds on Z axis")

    return parsed.model_dump()
