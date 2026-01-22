from flask import Flask
from flask_socketio import SocketIO
import os
from .routes.api import bp as api_bp
from .routes.site import bp as site_bp

socketio = SocketIO()


def create_app():
    base_dir = os.path.dirname(os.path.abspath(__file__))

    app = Flask(
        __name__,
        template_folder=os.path.join(base_dir, "templates"),
        static_folder=os.path.join(base_dir, "static"),
    )
    app.register_blueprint(api_bp)
    app.register_blueprint(site_bp)

    socketio.init_app(
        app,
        cors_allowed_origins="*",
        ping_interval=60,  # send pings every 30s
        ping_timeout=1800,  # allow up to 15 minutes for a pong before disconnect
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

    return app


from .routes.websockets import ws_ngram, ws_sort  # noqa: E402,F401
