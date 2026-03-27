from __future__ import annotations


def get_demo_scene(session_id: str = "demo") -> dict:
    return {
        "version": 2,
        "session_id": session_id,
        "source": "demo",
        "pipeline_mode": "demo",
        "room": {
            "width": 4.5,
            "width_confidence": 1.0,
            "depth": 5.5,
            "depth_confidence": 1.0,
            "height": 2.8,
            "height_confidence": 1.0,
            "floor_plane": [0.0, 1.0, 0.0, 0.0],
            "floor_plane_inlier_ratio": 1.0,
        },
        "walls": [
            {"id": "wall_north", "x1": 0.0, "z1": 0.0, "x2": 4.5, "z2": 0.0, "confidence": 1.0},
            {"id": "wall_south", "x1": 0.0, "z1": 5.5, "x2": 4.5, "z2": 5.5, "confidence": 1.0},
            {"id": "wall_east", "x1": 4.5, "z1": 0.0, "x2": 4.5, "z2": 5.5, "confidence": 1.0},
            {"id": "wall_west", "x1": 0.0, "z1": 0.0, "x2": 0.0, "z2": 5.5, "confidence": 1.0},
        ],
        "windows": [
            {
                "id": "win_001",
                "wall": "wall_north",
                "x": 1.4,
                "width": 1.2,
                "height": 1.1,
                "sill_height": 0.9,
                "confidence": 1.0,
                "user_confirmed": True,
            }
        ],
        "doors": [
            {
                "id": "door_001",
                "wall": "wall_west",
                "x": 0.5,
                "width": 0.9,
                "height": 2.1,
                "sill_height": 0.0,
                "confidence": 1.0,
                "user_confirmed": True,
            }
        ],
        "objects": [
            {
                "id": "obj_001",
                "type": "sofa",
                "type_confidence": 1.0,
                "position_confidence": 1.0,
                "size_confidence": 1.0,
                "rotation_confidence": 1.0,
                "label_confirmed": True,
                "position": {"x": 1.2, "y": 0.0, "z": 0.6},
                "size": {"w": 2.2, "h": 0.85, "d": 0.9},
                "rotation_y": 0.0,
                "color": "grey",
                "product_url": None,
                "product_name": None,
            },
            {
                "id": "obj_002",
                "type": "coffee_table",
                "type_confidence": 1.0,
                "position_confidence": 1.0,
                "size_confidence": 1.0,
                "rotation_confidence": 1.0,
                "label_confirmed": True,
                "position": {"x": 1.5, "y": 0.0, "z": 1.8},
                "size": {"w": 1.0, "h": 0.45, "d": 0.6},
                "rotation_y": 0.0,
                "color": "brown",
                "product_url": None,
                "product_name": None,
            },
        ],
        "metadata": {
            "room_type": "living_room",
            "room_type_confidence": 1.0,
            "pipeline_version": "demo",
            "confidence": "demo",
            "created_at": "2026-03-27T00:00:00Z",
            "last_edited": "2026-03-27T00:00:00Z",
        },
    }
