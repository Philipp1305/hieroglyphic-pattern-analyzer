from __future__ import annotations

from . import bp, render_page


@bp.route("/sort/<int:image_id>")
def sort_page(image_id: int):
    return render_page("pages/sort.html", image_id=image_id)
