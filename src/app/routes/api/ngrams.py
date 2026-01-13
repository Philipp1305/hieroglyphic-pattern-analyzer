from __future__ import annotations

from typing import Iterable, Sequence

from flask import jsonify

from src.database.tools import select

from . import bp


@bp.get("/images/<int:image_id>/ngrams")
def get_image_ngrams(image_id: int):
    if not _image_exists(image_id):
        return {"error": "not found"}, 404

    patterns = select(
        """
        SELECT id, gardiner_ids, length, count
        FROM t_ngram_pattern
        WHERE id_image = %s
        ORDER BY length DESC, count DESC, id ASC
        """,
        (image_id,),
    )

    items: list[dict[str, object]] = []
    lengths: set[int] = set()

    if patterns:
        all_gardiner_ids = {
            int(gardiner_id)
            for _, gardiner_ids, _, _ in patterns
            for gardiner_id in (gardiner_ids or [])
            if gardiner_id is not None
        }
        unicode_map = _unicode_map_for_ids(all_gardiner_ids)

        for pattern_id, gardiner_ids, length, count in patterns:
            ids = [int(gid) for gid in gardiner_ids or [] if gid is not None]
            unicode_values = [
                _normalize_unicode(unicode_map.get(gid, "")) for gid in ids
            ]
            unicode_values = [u for u in unicode_values if u]
            unicode_label = " ".join(unicode_values)
            symbol = _unicode_to_symbol(unicode_values)

            items.append(
                {
                    "id": int(pattern_id),
                    "length": int(length),
                    "count": int(count),
                    "gardiner_ids": ids,
                    "unicode_values": unicode_values,
                    "unicode_label": unicode_label,
                    "symbol": symbol,
                }
            )
            lengths.add(int(length))

    response = jsonify(
        {
            "image_id": image_id,
            "items": items,
            "lengths": sorted(lengths),
        }
    )
    response.headers["Cache-Control"] = "no-store"
    return response


def _image_exists(image_id: int) -> bool:
    rows = select("SELECT 1 FROM t_images WHERE id = %s", (image_id,))
    return bool(rows)


def _unicode_map_for_ids(ids: Iterable[int]) -> dict[int, str]:
    id_list = list(ids)
    if not id_list:
        return {}
    rows = select(
        "SELECT id, unicode FROM t_gardiner_codes WHERE id = ANY(%s)", (id_list,)
    )
    return {int(row[0]): (row[1] or "") for row in rows}


def _normalize_unicode(value: str | None) -> str:
    if not value:
        return ""
    normalized = value.strip().upper()
    return normalized if normalized.startswith("U+") else f"U+{normalized}"


def _unicode_to_symbol(unicode_values: Sequence[str]) -> str:
    codepoints: list[int] = []
    for val in unicode_values:
        cleaned = val.strip().upper().replace("U+", "")
        if not cleaned:
            continue
        try:
            codepoints.append(int(cleaned, 16))
        except ValueError:
            continue
    try:
        return "".join(chr(cp) for cp in codepoints)
    except ValueError:
        return ""
