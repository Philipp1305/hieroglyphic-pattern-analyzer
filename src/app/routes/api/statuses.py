from __future__ import annotations

from flask import jsonify

from src.database.tools import select

from . import bp


@bp.get("/statuses")
def list_statuses():
    rows = select(
        """
        SELECT id, status, status_code
        FROM t_images_status
        ORDER BY id
        """
    )
    payload = {
        "items": [
            {
                "id": int(status_id),
                "status": status_label or "",
                "status_code": (status_code or "").upper(),
            }
            for status_id, status_label, status_code in rows
        ]
    }
    response = jsonify(payload)
    response.headers["Cache-Control"] = "no-store"
    return response
