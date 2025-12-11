from __future__ import annotations

from . import bp, render_page


@bp.route("/database")
def database():
    return render_page("pages/database.html")
