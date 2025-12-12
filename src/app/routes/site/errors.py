from __future__ import annotations

from . import bp, render_page


@bp.app_errorhandler(404)
def not_found_error(e):
    title = getattr(e, "name", "Page not found")
    description = getattr(e, "description", "The requested page could not be found.")
    return render_page(
        "pages/error.html", error_code=404, error_title=title, error_message=description
    ), 404


@bp.app_errorhandler(500)
def internal_error(e):
    title = getattr(e, "name", "Internal Server Error")
    description = getattr(
        e,
        "description",
        "The server encountered an internal error and was unable to complete your request.",
    )
    return render_page(
        "pages/error.html", error_code=500, error_title=title, error_message=description
    ), 500
