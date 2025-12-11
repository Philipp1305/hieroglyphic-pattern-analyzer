from __future__ import annotations

from . import bp, render_page


@bp.route("/view")
def view_page():
    return render_page("pages/view.html")
