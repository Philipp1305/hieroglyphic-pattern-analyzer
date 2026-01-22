from __future__ import annotations

from __future__ import annotations

from . import bp, render_page


@bp.route("/collection")
def collection():
    return render_page("pages/collection.html")
