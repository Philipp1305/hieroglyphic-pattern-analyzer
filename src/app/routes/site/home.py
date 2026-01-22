from __future__ import annotations

from . import bp, render_page


@bp.route("/")
def home():
    return render_page("pages/home.html")
