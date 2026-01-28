from __future__ import annotations

import json
from PIL import Image
import io
import psycopg2

from flask import current_app, jsonify, request
from psycopg2.extras import Json
from src.database.tools import insert
from src.app.services.pipeline_service import (
    STATUS_UPLOAD_DONE,
    start_pipeline_async,
)
from src.app.services.status_service import ensure_status_code
from . import bp


def make_preview(img_bytes: bytes, max_width: int = 800) -> bytes:
    img: Image.Image = Image.open(io.BytesIO(img_bytes))
    img = img.convert("RGB")

    w, h = img.size
    if w > max_width:
        new_height = int(h * max_width / w)
        img = img.resize((max_width, new_height), resample=Image.Resampling.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=70, optimize=True)
    return buf.getvalue()


@bp.post("/upload_papyrus")
def upload_papyrus():
    try:
        papyrus_name = request.form.get("papyrus_name", "papyrus")
        reading_direction_raw = request.form.get("reading_direction", "ltr")
        reading_direction = 1 if reading_direction_raw == "rtl" else 0
        sort_tolerance_raw = request.form.get("sort_tolerance")
        try:
            sort_tolerance = int(sort_tolerance_raw) if sort_tolerance_raw else 100
        except ValueError:
            sort_tolerance = 100
        id_status = ensure_status_code(STATUS_UPLOAD_DONE, "Upload done")

        image_file = request.files.get("papyrus_image_file")
        json_file = request.files.get("annotation_json_file")

        if not image_file or not json_file:
            return jsonify({"status": "error", "message": "missing files", "id": None})

        json_payload = json.loads(json_file.read().decode("utf-8"))
        img_bytes = image_file.read()
        img_preview_bytes = make_preview(img_bytes)
        file_name = image_file.filename
        mimetype = image_file.mimetype

        sql = """
            INSERT INTO T_IMAGES (
                json,
                title,
                img,
                img_preview,
                file_name,
                mimetype,
                reading_direction,
                id_status,
                sort_tolerance
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """

        params = (
            Json(json_payload),
            papyrus_name,
            psycopg2.Binary(img_bytes),
            psycopg2.Binary(img_preview_bytes),
            file_name,
            mimetype,
            reading_direction,
            id_status,
            sort_tolerance,
        )
        new_id = insert(sql, params)

        # Fire-and-forget pipeline with app context
        start_pipeline_async(new_id, current_app._get_current_object())  # type: ignore[attr-defined]

        return jsonify({"status": "success", "id": new_id})

    except Exception as exc:
        current_app.logger.exception("Error in upload_papyrus", exc_info=exc)
        return jsonify({"status": "error", "message": str(exc), "id": None})
