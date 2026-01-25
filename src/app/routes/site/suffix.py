from __future__ import annotations

from flask import request

from . import bp, render_page


@bp.route("/suffixes", endpoint="suffix_page")
@bp.route("/suffix", endpoint="suffix_page_alt")
def view_suffix_page():
    image_id = request.args.get("id", type=int)
    return render_page("pages/suffix.html", image_id=image_id)
