from flask import Flask, render_template, current_app
from flask_socketio import SocketIO, emit
import os
import json
import psycopg2
from psycopg2.extras import Json
from .routes.upload import bp as upload_papyrus

from src.database.insert import run_insert
from .services.papyri_service import fetch_papyri_summaries

socketio = SocketIO()

def create_app():
    base_dir = os.path.dirname(os.path.abspath(__file__))

    app = Flask(
        __name__,
        template_folder=os.path.join(base_dir, "templates"),
        static_folder=os.path.join(base_dir, "static")
    )
    app.register_blueprint(upload_papyrus)

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

@socketio.on("c2s:upload_papyrus")
def handle_upload_papyrus(data) -> None:
    current_app.logger.debug("c2s:upload_papyrus received with keys: %s", list(data.keys()))

    required_keys = [
        "papyrus_name",
        "reading_direction",
        "papyrus_image_file",
        "annotation_json_file",
    ]
    missing = [k for k in required_keys if k not in data]
    if missing:
        msg = f"missing fields: {', '.join(missing)}"
        current_app.logger.warning("Upload Papyrus failed: %s", msg)
        emit(
            "s2c:upload_papyrus:response",
            {"status": "error", "message": msg, "id": None},
        )
        return

    try:
        title = data["papyrus_name"] or "papyrus"
        reading_direction = int(data["reading_direction"])
        id_status = 1  # initialer Status

        # --- JSON-Datei aus Payload holen ---
        json_src = data["annotation_json_file"]
        if hasattr(json_src, "read"):          # File-like (z.B. FileStorage)
            json_bytes = json_src.read()
        elif isinstance(json_src, bytes):
            json_bytes = json_src
        else:                                  # str o.ä.
            json_bytes = str(json_src).encode("utf-8")

        json_str = json_bytes.decode("utf-8")
        json_payload = json.loads(json_str)

        # --- Bilddaten aus Payload holen ---
        img_src = data["papyrus_image_file"]
        if hasattr(img_src, "read"):           # File-like
            img_bytes = img_src.read()
        elif isinstance(img_src, bytes):
            img_bytes = img_src
        else:
            raise TypeError("papyrus_image_file must be bytes or file-like")

        file_name = data.get("papyrus_image_filename", "uploaded_papyrus_image")
        mimetype = data.get("papyrus_image_mimetype", "application/octet-stream")

        # --- Insert in T_IMAGES ---
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
            Json(json_payload),             # jsonb
            title,                          # text
            psycopg2.Binary(img_bytes),     # bytea
            file_name,                      # text
            mimetype,                       # text
            reading_direction,              # numeric(1,0)
            id_status,                      # number/int
        )

        new_id = run_insert(sql, params)

        current_app.logger.info("New papyrus inserted with id=%s", new_id)
        emit(
            "s2c:upload_papyrus:response",
            {"status": "success", "message": "inserted", "id": new_id},
        )

    except Exception as e:
        current_app.logger.exception("Error while handling c2s:upload_papyrus: %s", e)
        emit(
            "s2c:upload_papyrus:response",
            {"status": "error", "message": str(e), "id": None},
        )