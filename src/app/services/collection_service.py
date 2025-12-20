from __future__ import annotations

from base64 import b64encode
from dataclasses import dataclass
from typing import Optional

from src.database.tools import select


@dataclass(frozen=True)
class CollectionItem:
    """Lightweight representation of an entry in the collection."""

    id: int
    title: str
    image_src: str
    status_label: str
    status_variant: str
    status_code: str


STATUS_VARIANT_MAP = {
    "processed": "success",
    "complete": "success",
    "completed": "success",
    "ok": "success",
    "pending": "warning",
    "processing": "info",
    "in progress": "info",
    "queued": "info",
    "error": "error",
    "failed": "error",
    "failure": "error",
}

DEFAULT_STATUS_VARIANT = "info"
DEFAULT_MIMETYPE = "image/png"


def fetch_collection_items(limit: Optional[int] = None) -> list[CollectionItem]:
    """Load collection items with their status labels and ready-to-use <img> sources."""

    sql = """
        SELECT
            i.id,
            i.title,
            i.file_name,
            i.mimetype,
            i.img_preview,
            s.status AS status_label,
            s.status_code
        FROM t_images AS i
        LEFT JOIN t_images_status AS s ON s.id = i.id_status
        ORDER BY i.id DESC
    """
    params = None
    if limit is not None:
        sql += " LIMIT %s"
        params = (limit,)

    results = select(sql, params)
    collection: list[CollectionItem] = []

    for row in results:
        (
            item_id,
            title,
            file_name,
            mimetype,
            img_blob,
            status_label,
            status_code,
        ) = row
        normalized_code = (status_code or "").strip().upper()
        status_variant = _resolve_status_variant(status_label)
        if normalized_code == "SORT_VALIDATE":
            status_variant = "warning"
        collection.append(
            CollectionItem(
                id=item_id,
                title=(title or file_name or "").strip(),
                image_src=_build_image_src(img_blob, mimetype),
                status_label=status_label or "",
                status_variant=status_variant,
                status_code=normalized_code,
            )
        )

    return collection


def _build_image_src(img_blob: Optional[bytes], mimetype: Optional[str]) -> str:
    if not img_blob:
        return ""
    mime = mimetype or DEFAULT_MIMETYPE
    encoded = b64encode(img_blob).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _resolve_status_variant(status_label: Optional[str]) -> str:
    if not status_label:
        return DEFAULT_STATUS_VARIANT
    normalized = status_label.strip().lower()
    return STATUS_VARIANT_MAP.get(normalized, DEFAULT_STATUS_VARIANT)
