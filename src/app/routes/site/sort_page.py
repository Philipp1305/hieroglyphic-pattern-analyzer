from __future__ import annotations

from flask import request

from . import bp, render_page


@bp.route("/sort")
def sort_page():
    image_id = request.args.get("id", type=int)
    return render_page("pages/sort.html", image_id=image_id)
