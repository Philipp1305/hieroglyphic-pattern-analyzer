from flask import Flask, render_template
import os

from .services.papyri_service import fetch_papyri_summaries


def create_app():
    base_dir = os.path.dirname(os.path.abspath(__file__))

    app = Flask(
        __name__,
        template_folder=os.path.join(base_dir, "templates"),
        static_folder=os.path.join(base_dir, "static")
    )

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
