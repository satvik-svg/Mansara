from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.product_search import search_products
from services.scene_validator import validate_scene
from session.store import session_store

router = APIRouter(tags=["shop"])


class ShopSearchRequest(BaseModel):
    object_type: str
    color: str | None = None
    style: str | None = None
    max_width_m: float | None = None
    max_depth_m: float | None = None


class ShopPlaceRequest(BaseModel):
    session_id: str
    object_id: str
    product: dict


@router.post("/api/shop/search")
def shop_search(payload: ShopSearchRequest) -> dict:
    results = search_products(
        object_type=payload.object_type,
        color=payload.color,
        max_width_m=payload.max_width_m,
        max_depth_m=payload.max_depth_m,
    )
    return {"results": results, "source": "mock", "size_filtered": True}


@router.post("/api/shop/place")
def shop_place(payload: ShopPlaceRequest) -> dict:
    scene = session_store.get_scene(payload.session_id)
    if scene is None:
        raise HTTPException(status_code=404, detail="Scene not found")

    updated = dict(scene)
    objects = []
    for obj in updated.get("objects", []):
        if obj.get("id") == payload.object_id:
            obj = dict(obj)
            obj["product_url"] = payload.product.get("product_url")
            obj["product_name"] = payload.product.get("title")
        objects.append(obj)
    updated["objects"] = objects

    valid_scene = validate_scene(updated)
    session_store.update_scene(payload.session_id, valid_scene, push_history=True)
    return {"scene": valid_scene}
