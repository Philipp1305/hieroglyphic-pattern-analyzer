from __future__ import annotations

from flask import request

from . import bp, render_page


@bp.route("/overview")
def overview():
    image_id = request.args.get("id", type=int)
    return render_page("pages/overview.html", image_id=image_id)
