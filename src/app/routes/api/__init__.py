from __future__ import annotations

from flask import Blueprint

bp = Blueprint("api", __name__, url_prefix="/api")


from . import upload_papyrus  # noqa: E402,F401
from . import images  # noqa: E402,F401
from . import collection_items  # noqa: E402,F401
from . import statuses  # noqa: E402,F401
from . import sorting  # noqa: E402,F401
from . import ngrams  # noqa: E402,F401
