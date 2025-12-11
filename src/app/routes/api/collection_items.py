from __future__ import annotations

from flask import jsonify

from ...services.collection_service import fetch_collection_items
from . import bp


@bp.get("/collection")
def list_collection_items():
    items = fetch_collection_items()
    payload = {
        "items": [
            {
                "id": item.id,
                "title": item.title,
                "image_src": item.image_src,
                "status_label": item.status_label,
                "status_variant": item.status_variant,
            }
            for item in items
        ]
    }
    response = jsonify(payload)
    response.headers["Cache-Control"] = "no-store"
    return response
