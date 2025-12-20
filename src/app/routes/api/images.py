from __future__ import annotations

from base64 import b64encode
from typing import Optional

from flask import jsonify

from src.database.tools import select

from . import bp


@bp.get("/images/<int:image_id>")
def get_image_metadata(image_id: int):
    metadata = _fetch_image_metadata(image_id)
    if not metadata:
        return {"error": "not found"}, 404
    response = jsonify(metadata)
    response.headers["Cache-Control"] = "no-store"
    return response


@bp.get("/images/<int:image_id>/meta")
def get_image_metadata_summary(image_id: int):
    summary = _fetch_image_meta_summary(image_id)
    if not summary:
        return {"error": "not found"}, 404
    response = jsonify(summary)
    response.headers["Cache-Control"] = "no-store"
    return response


@bp.get("/images/<int:image_id>/full")
def get_full_image(image_id: int):
    payload = _fetch_full_image(image_id)
    if not payload:
        return {"error": "not found"}, 404
    response = jsonify(payload)
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

    rows = select(sql, (image_id,))
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


def _fetch_image_meta_summary(image_id: int) -> Optional[dict]:
    sql = """
        SELECT
            i.id,
            i.title,
            i.file_name,
            i.sort_tolerance,
            i.reading_direction,
            s.status AS status_label,
            s.status_code
        FROM t_images AS i
        LEFT JOIN t_images_status AS s ON s.id = i.id_status
        WHERE i.id = %s
    """

    rows = select(sql, (image_id,))
    if not rows:
        return None

    (
        img_id,
        title,
        file_name,
        tolerance,
        reading_dir,
        status_label,
        status_code,
    ) = rows[0]

    return {
        "id": img_id,
        "title": (title or "").strip(),
        "file_name": file_name or "",
        "tolerance": tolerance,
        "reading_direction": "rtl" if str(reading_dir) == "1" else "ltr",
        "status": status_label or "",
        "status_code": (status_code or "").upper(),
    }


def _fetch_full_image(image_id: int) -> Optional[dict]:
    rows = select(
        """
        SELECT img, mimetype
        FROM t_images
        WHERE id = %s
        """,
        (image_id,),
    )
    if not rows:
        return None
    img_blob, mimetype = rows[0]
    return {"image": _build_image_src(img_blob, mimetype)}
