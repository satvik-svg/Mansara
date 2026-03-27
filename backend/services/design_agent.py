from __future__ import annotations

from datetime import datetime


SUPPORTED_TYPES = {
    "sofa": {"w": 2.1, "h": 0.85, "d": 0.9, "color": "grey"},
    "chair": {"w": 0.6, "h": 0.9, "d": 0.6, "color": "beige"},
    "armchair": {"w": 0.9, "h": 0.9, "d": 0.85, "color": "beige"},
    "coffee_table": {"w": 1.0, "h": 0.45, "d": 0.6, "color": "brown"},
    "table": {"w": 1.4, "h": 0.75, "d": 0.8, "color": "brown"},
    "bookshelf": {"w": 0.9, "h": 1.8, "d": 0.35, "color": "white"},
    "plant": {"w": 0.45, "h": 1.0, "d": 0.45, "color": "green"},
    "tv_unit": {"w": 1.6, "h": 0.5, "d": 0.45, "color": "black"},
}


def _next_object_id(objects: list[dict]) -> str:
    max_id = 0
    for obj in objects:
        raw = str(obj.get("id", ""))
        if raw.startswith("obj_"):
            try:
                max_id = max(max_id, int(raw.split("_")[-1]))
            except ValueError:
                pass
    return f"obj_{max_id + 1:03d}"


def _extract_type_from_instruction(instruction_lc: str) -> str | None:
    # Match longer names first.
    ordered = sorted(SUPPORTED_TYPES.keys(), key=len, reverse=True)
    for obj_type in ordered:
        if obj_type.replace("_", " ") in instruction_lc or obj_type in instruction_lc:
            return obj_type

    if "coffee table" in instruction_lc:
        return "coffee_table"
    if "tv unit" in instruction_lc:
        return "tv_unit"
    return None


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def apply_instruction(scene: dict, instruction: str, selected_object_id: str | None = None) -> tuple[dict, dict, str]:
    updated = dict(scene)
    objects = list(updated.get("objects", []))
    instruction_lc = instruction.lower()

    action = {"action": "noop"}
    message = "No scene change applied yet."

    if selected_object_id and "remove" in instruction_lc:
        before = len(objects)
        objects = [o for o in objects if o.get("id") != selected_object_id]
        if len(objects) < before:
            action = {"action": "remove", "object_id": selected_object_id}
            message = f"Removed object {selected_object_id}."

    elif "add" in instruction_lc:
        obj_type = _extract_type_from_instruction(instruction_lc) or "chair"
        spec = SUPPORTED_TYPES.get(obj_type, SUPPORTED_TYPES["chair"])

        room = updated.get("room", {})
        room_w = float(room.get("width", 4.0))
        room_d = float(room.get("depth", 4.0))

        idx = len(objects)
        base_x = room_w * 0.5 + (idx % 3 - 1) * 0.6
        base_z = room_d * 0.5 + (idx // 3) * 0.6

        new_obj = {
            "id": _next_object_id(objects),
            "type": obj_type,
            "type_confidence": 0.65,
            "position_confidence": 0.55,
            "size_confidence": 0.65,
            "rotation_confidence": 0.5,
            "label_confirmed": False,
            "position": {
                "x": _clamp(base_x, 0.0, room_w),
                "y": 0.0,
                "z": _clamp(base_z, 0.0, room_d),
            },
            "size": {
                "w": spec["w"],
                "h": spec["h"],
                "d": spec["d"],
            },
            "rotation_y": 0.0,
            "color": spec["color"],
            "product_url": None,
            "product_name": None,
        }
        objects.append(new_obj)
        action = {"action": "add", "object_type": obj_type, "object_id": new_obj["id"]}
        message = f"Added {obj_type} as {new_obj['id']}."

    elif "remove" in instruction_lc and not selected_object_id:
        message = "Select an object first, then run remove."

    updated["objects"] = objects
    metadata = dict(updated.get("metadata", {}))
    metadata["last_edited"] = datetime.utcnow().isoformat() + "Z"
    updated["metadata"] = metadata

    return updated, action, message
