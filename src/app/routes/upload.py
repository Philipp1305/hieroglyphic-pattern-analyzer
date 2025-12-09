from flask import Blueprint, request, jsonify, current_app
import json
import psycopg2
from psycopg2.extras import Json

from src.database.insert import run_insert

bp = Blueprint("upload_api", __name__)

@bp.route("/api/upload_papyrus", methods=["POST"])
def upload_papyrus():
    try:
        # --- Textfelder ---
        papyrus_name = request.form.get("papyrus_name", "papyrus")
        reading_direction_raw = request.form.get("reading_direction", "ltr")
        reading_direction = 1 if reading_direction_raw == "rtl" else 0
        id_status = 1

        # --- Dateien ---
        image_file = request.files.get("papyrus_image_file")
        json_file = request.files.get("annotation_json_file")

        if not image_file or not json_file:
            return jsonify({"status": "error", "message": "missing files", "id": None})

        # JSON einlesen
        json_payload = json.loads(json_file.read().decode("utf-8"))

        # Bilddaten
        img_bytes = image_file.read()
        file_name = image_file.filename
        mimetype = image_file.mimetype

        # --- Insert in die Datenbank ---
        sql = """
            INSERT INTO T_IMAGES (
                json,
                title,
                img,
                file_name,
                mimetype,
                reading_direction,
                id_status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """

        params = (
            Json(json_payload),
            papyrus_name,
            psycopg2.Binary(img_bytes),
            file_name,
            mimetype,
            reading_direction,
            id_status
        )
        new_id = run_insert(sql, params)

        return jsonify({"status": "success", "id": new_id})

    except Exception as e:
        current_app.logger.exception("Error in upload_papyrus")
        return jsonify({"status": "error", "message": str(e), "id": None})