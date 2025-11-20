from __future__ import annotations

from base64 import b64encode
from dataclasses import dataclass
from typing import Optional

from src.database.select import run_select


@dataclass(frozen=True)
class PapyrusSummary:
    """Lightweight representation of a papyrus card."""

    id: int
    title: str
    image_src: str
    status_label: str
    status_variant: str


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


def fetch_papyri_summaries(limit: Optional[int] = None) -> list[PapyrusSummary]:
    """
    Load papyri with their status labels and ready-to-use <img> sources.
    """

    sql = """
        SELECT
            i.id,
            i.title,
            i.file_name,
            i.mimetype,
            i.img,
            s.status AS status_label
        FROM t_images AS i
        LEFT JOIN t_images_status AS s ON s.id = i.id_status
        ORDER BY i.id DESC
    """
    params = None
    if limit is not None:
        sql += " LIMIT %s"
        params = (limit,)

    results = run_select(sql, params)
    papyri: list[PapyrusSummary] = []

    for row in results:
        (
            papyrus_id,
            title,
            file_name,
            mimetype,
            img_blob,
            status_label,
        ) = row
        papyri.append(
            PapyrusSummary(
                id=papyrus_id,
                title=((title or file_name or "")).strip(),
                image_src=_build_image_src(img_blob, mimetype),
                status_label=status_label or "",
                status_variant=_resolve_status_variant(status_label),
            )
        )

    return papyri


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
