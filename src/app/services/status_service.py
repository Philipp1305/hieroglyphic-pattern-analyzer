from __future__ import annotations

from src.database.tools import select, update


def change_image_status(image_id: int, status_code: str) -> bool:
    if image_id is None:
        raise ValueError("image_id is required")
    try:
        image_id_int = int(image_id)
    except (TypeError, ValueError):
        raise ValueError("image_id must be an integer") from None

    normalized_code = (status_code or "").strip().upper()
    if not normalized_code:
        raise ValueError("status_code is required")

    rows = select(
        "SELECT id FROM T_IMAGES_STATUS WHERE status_code = %s",
        (normalized_code,),
    )
    if not rows:
        raise ValueError(f"status_code '{normalized_code}' does not exist")

    status_id = rows[0][0]
    updated = update(
        "UPDATE T_IMAGES SET id_status = %s WHERE id = %s",
        (status_id, image_id_int),
    )
    return bool(updated)
