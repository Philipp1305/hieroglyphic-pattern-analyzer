from __future__ import annotations

from flask import request

from . import bp, render_page


@bp.route("/structure", endpoint="structure")
def view_suffix_page():
    image_id = request.args.get("id", type=int)
    return render_page("pages/structure.html", image_id=image_id)
