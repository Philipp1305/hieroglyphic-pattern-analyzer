from __future__ import annotations

from flask import request

from . import bp, render_page


@bp.route("/glyphes", endpoint="glyphes")
def glyphes_page():
    image_id = request.args.get("id", type=int)
    return render_page("pages/glyphes.html", image_id=image_id)
