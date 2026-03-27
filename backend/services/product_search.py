from __future__ import annotations


def search_products(object_type: str, color: str | None, max_width_m: float | None, max_depth_m: float | None) -> list[dict]:
    suffix = f"{color} " if color else ""
    return [
        {
            "title": f"{suffix}{object_type.title()} Option A",
            "price": "$499",
            "product_url": "https://example.com/product-a",
            "image_url": "https://images.unsplash.com/photo-1555041469-a586c61ea9bc",
            "dimensions": {"w": max_width_m or 1.8, "d": max_depth_m or 0.9, "h": 0.9},
        },
        {
            "title": f"{suffix}{object_type.title()} Option B",
            "price": "$699",
            "product_url": "https://example.com/product-b",
            "image_url": "https://images.unsplash.com/photo-1505693416388-ac5ce068fe85",
            "dimensions": {"w": max_width_m or 2.0, "d": max_depth_m or 1.0, "h": 0.8},
        },
    ]
