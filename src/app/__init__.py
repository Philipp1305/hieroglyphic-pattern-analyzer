from flask import Flask, render_template, current_app
from flask_socketio import SocketIO, emit
import os
from base64 import b64decode
import json
from psycopg2.extras import Json
from src.database.insert import run_insert
from src.database.select import run_select
from .services.papyri_service import fetch_papyri_summaries

socketio = SocketIO()

def create_app():
    base_dir = os.path.dirname(os.path.abspath(__file__))

    app = Flask(
        __name__,
        template_folder=os.path.join(base_dir, "templates"),
        static_folder=os.path.join(base_dir, "static")
    )
    socketio.init_app(app, cors_allowed_origins="*")

    def list_static_js_files():
        static_dir = app.static_folder
        if not static_dir:
            return []
        js_dir = os.path.join(static_dir, "js")
        if not os.path.isdir(js_dir):
            return []
        return sorted(
            [
                os.path.join("js", entry)
                for entry in os.listdir(js_dir)
                if entry.endswith(".js")
            ]
        )

    @app.context_processor
    def inject_static_assets():
        return {"static_js_files": list_static_js_files()}

    def render_page(template_name: str, **context):
        return render_template("index.html", content_template=template_name, **context)

    @app.route("/")
    def home():
        return render_page("pages/home.html")

    @app.route("/papyri")
    def papyri():
        try:
            papyri_cards = fetch_papyri_summaries()
        except Exception as exc:
            app.logger.exception("Failed to load papyri from database", exc_info=exc)
            papyri_cards = []
        return render_page("pages/papyri.html", papyri=papyri_cards)

    @app.route("/database")
    def database():
        return render_page("pages/database.html")

    @app.route("/upload")
    def upload():
        return render_page("pages/upload.html")

    @app.route("/view")
    def view():
        return render_page("pages/view.html")

    return app


@socketio.on("connect")
def handle_connect():
    current_app.logger.debug("WebSocket client connected")
    emit("server_ready", {"message": "Connected to GlyPat Server"})


@socketio.on("ts_new_papyrus")
def upload_new_papyrus(data):
    id_new_papyrus = None

    try:
        if not isinstance(data, dict):
            raise ValueError("Upload payload must be an object.")

        title = (data.get("papyrus_name") or "").strip()
        reading_direction = (
            1
            if str(data.get("reading_direction", "ltr")).strip().lower() == "rtl"
            else 0
        )
        status_id = int(data.get("status_id") or 1)

        annotation_payload = data.get("annotation_json")
        if annotation_payload is None:
            raise ValueError("annotation_json missing")
        if isinstance(annotation_payload, str):
            annotation_payload = annotation_payload.strip()
            if not annotation_payload:
                raise ValueError("annotation_json empty")
            annotation_payload = json.loads(annotation_payload)
        elif not isinstance(annotation_payload, (dict, list)):
            raise ValueError("annotation_json must be a JSON object or list")

        image_payload = data.get("papyrus_image")
        if image_payload is None:
            raise ValueError("papyrus_image missing")

        file_name = (
            data.get("papyrus_image_name")
            or data.get("papyrus_image_filename")
            or ""
        )
        mimetype = data.get("papyrus_image_mimetype")
        raw_image = image_payload
        if isinstance(image_payload, dict):
            file_name = (
                image_payload.get("name")
                or image_payload.get("filename")
                or file_name
            )
            mimetype = (
                image_payload.get("mimetype")
                or image_payload.get("content_type")
                or mimetype
            )
            raw_image = image_payload.get("data") or image_payload.get("content")

        if isinstance(raw_image, (bytes, bytearray)):
            image_bytes = bytes(raw_image)
        elif isinstance(raw_image, str):
            payload = raw_image
            if payload.startswith("data:") and "," in payload:
                header, payload = payload.split(",", 1)
                if not mimetype and header.startswith("data:"):
                    mimetype = header.split(";")[0].split(":")[1]
            image_bytes = b64decode(payload)
        else:
            raise ValueError("Unsupported papyrus_image payload")

        if not file_name:
            file_name = f"{title or 'papyrus'}.bin"
        if not mimetype:
            mimetype = "application/octet-stream"

        insert_sql = """
            INSERT INTO t_images (json, title, img, file_name, mimetype, reading_direction, id_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        params = (
            Json(annotation_payload),
            title or file_name,
            image_bytes,
            file_name,
            mimetype,
            reading_direction,
            status_id,
        )
        id_new_papyrus = run_insert(insert_sql, params)

    except Exception as exc:
        current_app.logger.exception("Failed to upload papyrus", exc_info=exc)

    if id_new_papyrus is None:
        emit("fs-r_new_papyrus", {"message": "error", "id": None})
    else:
        emit("fs-r_new_papyrus", {"message": "success", "id": id_new_papyrus})
