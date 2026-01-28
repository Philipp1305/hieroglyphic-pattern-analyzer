from __future__ import annotations

from flask import request

from . import bp, render_page


@bp.route("/pattern", endpoint="pattern_page")
@bp.route("/patterns")
def pattern_page():
    image_id = request.args.get("id", type=int)
    return render_page("pages/pattern.html", image_id=image_id)
