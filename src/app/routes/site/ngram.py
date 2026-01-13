from __future__ import annotations

from flask import request

from . import bp, render_page


@bp.route("/ngrams", endpoint="ngrams_page")
@bp.route("/ngram")
def view_page():
    image_id = request.args.get("id", type=int)
    return render_page("pages/ngram.html", image_id=image_id)
