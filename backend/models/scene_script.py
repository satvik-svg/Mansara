from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Position(BaseModel):
    x: float
    y: float
    z: float


class Size(BaseModel):
    w: float = Field(gt=0)
    h: float = Field(gt=0)
    d: float = Field(gt=0)


class Room(BaseModel):
    width: float = Field(gt=0)
    width_confidence: float = Field(ge=0, le=1)
    depth: float = Field(gt=0)
    depth_confidence: float = Field(ge=0, le=1)
    height: float = Field(gt=0)
    height_confidence: float = Field(ge=0, le=1)
    floor_plane: list[float] = Field(min_length=4, max_length=4)
    floor_plane_inlier_ratio: float = Field(ge=0, le=1)


class Wall(BaseModel):
    id: str
    x1: float
    z1: float
    x2: float
    z2: float
    confidence: float = Field(ge=0, le=1)


class Opening(BaseModel):
    id: str
    wall: str
    x: float
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    sill_height: float = Field(default=0.0, ge=0)
    confidence: float = Field(ge=0, le=1)
    user_confirmed: bool = False


class SceneObject(BaseModel):
    id: str
    type: str
    type_confidence: float = Field(ge=0, le=1)
    position_confidence: float = Field(ge=0, le=1)
    size_confidence: float = Field(ge=0, le=1)
    rotation_confidence: float = Field(ge=0, le=1)
    label_confirmed: bool = False
    position: Position
    size: Size
    rotation_y: float = 0.0
    color: str | None = None
    product_url: str | None = None
    product_name: str | None = None


class Metadata(BaseModel):
    room_type: str | None = None
    room_type_confidence: float = Field(default=0.5, ge=0, le=1)
    pipeline_version: str = "precomputed"
    confidence: Literal["metric", "partial", "approximate", "demo"] = "demo"
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    last_edited: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class SceneScript(BaseModel):
    version: int = 2
    session_id: str
    source: str = "precomputed"
    pipeline_mode: str = "precomputed"
    room: Room
    walls: list[Wall]
    windows: list[Opening] = []
    doors: list[Opening] = []
    objects: list[SceneObject]
    metadata: Metadata
