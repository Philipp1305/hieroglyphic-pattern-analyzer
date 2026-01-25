from __future__ import annotations

from flask import request

from . import bp, render_page


@bp.route("/pattern-details")
def pattern_details_page():
    # Keep the back-link behaviour consistent with the n-gram view.
    image_id = request.args.get("id", type=int)
    pattern_id = request.args.get("pattern_id", type=int)
    return render_page(
        "pages/pattern_details.html",
        image_id=image_id,
        pattern_id=pattern_id,
    )
