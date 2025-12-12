from __future__ import annotations

from base64 import b64encode
from typing import Optional

from flask import jsonify

from src.database.select import run_select

from . import bp


@bp.get("/images/<int:image_id>")
def get_image_metadata(image_id: int):
    metadata = _fetch_image_metadata(image_id)
    if not metadata:
        return {"error": "not found"}, 404
    response = jsonify(metadata)
    response.headers["Cache-Control"] = "no-store"
    return response


def _fetch_image_metadata(image_id: int) -> Optional[dict]:
    sql = """
        SELECT
            i.id,
            i.title,
            i.img_preview,
            i.mimetype,
            s.status AS status_label,
            s.status_code
        FROM t_images AS i
        LEFT JOIN t_images_status AS s ON s.id = i.id_status
        WHERE i.id = %s
    """

    rows = run_select(sql, (image_id,))
    if not rows:
        return None

    image_id, title, img_blob, mimetype, status_label, status_code = rows[0]
    return {
        "id": image_id,
        "title": (title or "").strip(),
        "image": _build_image_src(img_blob, mimetype),
        "status": status_label or "",
        "status_code": (status_code or "").upper(),
    }


def _build_image_src(img_blob: Optional[bytes], mimetype: Optional[str]) -> str:
    if not img_blob:
        return ""
    mime = mimetype or "image/png"
    return f"data:{mime};base64,{b64encode(img_blob).decode('ascii')}"
