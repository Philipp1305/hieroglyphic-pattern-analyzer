from __future__ import annotations

from . import bp, render_page


@bp.route("/upload")
def upload_page():
    return render_page("pages/upload.html")
