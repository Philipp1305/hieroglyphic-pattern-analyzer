from __future__ import annotations

from flask import Blueprint, render_template

bp = Blueprint("site", __name__)


def render_page(template_name: str, **context):
    return render_template("index.html", content_template=template_name, **context)


from . import errors  # noqa: E402,F401
from . import home  # noqa: E402,F401
from . import database  # noqa: E402,F401
from . import upload_page  # noqa: E402,F401
from . import view_page  # noqa: E402,F401
from . import overview  # noqa: E402,F401
from . import sort_page  # noqa: E402,F401
from . import collection  # noqa: E402,F401
