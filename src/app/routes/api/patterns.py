from __future__ import annotations

from typing import Iterable, Sequence

from flask import jsonify

from src.database.tools import select

from . import bp


@bp.get("/images/<int:image_id>/patterns")
def get_image_patterns(image_id: int):
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

    pattern_ids = [int(row[0]) for row in patterns]
    occurrences_by_pattern = _occurrences_with_bboxes(pattern_ids)

    items: list[dict[str, object]] = []
    lengths: set[int] = set()

    if patterns:
        all_gardiner_ids = {
            int(gardiner_id)
            for _, gardiner_ids, _, _ in patterns
            for gardiner_id in (gardiner_ids or [])
            if gardiner_id is not None
        }
        gardiner_map = _gardiner_map_for_ids(all_gardiner_ids)

        for pattern_id, gardiner_ids, length, count in patterns:
            ids = [int(gid) for gid in gardiner_ids or [] if gid is not None]
            unicode_values = [
                _normalize_unicode(gardiner_map.get(gid, {}).get("unicode", ""))
                for gid in ids
            ]
            symbol_values = [
                _unicode_to_symbol([u]) if u else "" for u in unicode_values
            ]
            gardiner_codes = [
                _normalize_gardiner_code(gardiner_map.get(gid, {}).get("code", ""))
                for gid in ids
            ]
            gardiner_label = " ".join(code for code in gardiner_codes if code)
            symbol = "".join(val for val in symbol_values if val)

            items.append(
                {
                    "id": int(pattern_id),
                    "length": int(length),
                    "count": int(count),
                    "gardiner_ids": ids,
                    "gardiner_codes": gardiner_codes,
                    "gardiner_label": gardiner_label,
                    "symbol_values": symbol_values,
                    "symbol": symbol,
                    "occurrences": occurrences_by_pattern.get(int(pattern_id), []),
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


def _gardiner_map_for_ids(ids: Iterable[int]) -> dict[int, dict[str, str]]:
    id_list = list(ids)
    if not id_list:
        return {}
    rows = select(
        "SELECT id, code, unicode FROM t_gardiner_codes WHERE id = ANY(%s)",
        (id_list,),
    )
    return {
        int(row[0]): {"code": row[1] or "", "unicode": row[2] or ""} for row in rows
    }


def _normalize_unicode(value: str | None) -> str:
    if not value:
        return ""
    normalized = value.strip().upper()
    return normalized if normalized.startswith("U+") else f"U+{normalized}"


def _normalize_gardiner_code(value: str | None) -> str:
    if not value:
        return ""
    return value.strip().upper()


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


def _occurrences_with_bboxes(
    pattern_ids: Sequence[int],
) -> dict[int, list[dict[str, object]]]:
    if not pattern_ids:
        return {}

    rows = select(
        """
        SELECT
            occ.id,
            occ.id_pattern,
            occ.glyph_ids,
            bbox.bbox_x,
            bbox.bbox_y,
            bbox.bbox_height,
            bbox.bbox_width
        FROM T_NGRAM_OCCURENCES AS occ
        LEFT JOIN T_NGRAM_OCCURENCES_BBOXES AS bbox ON bbox.id_occ = occ.id
        WHERE occ.id_pattern = ANY(%s)
        ORDER BY occ.id, bbox.id
        """,
        (list(pattern_ids),),
    )

    by_pattern: dict[int, dict[int, dict[str, object]]] = {}
    for occ_id, pattern_id, glyph_ids, bbox_x, bbox_y, bbox_h, bbox_w in rows:
        pattern_key = int(pattern_id)
        occ_key = int(occ_id)
        by_pattern.setdefault(pattern_key, {}).setdefault(
            occ_key,
            {
                "id": occ_key,
                "glyph_ids": [int(gid) for gid in (glyph_ids or []) if gid is not None],
                "bboxes": [],
            },
        )
        if (
            bbox_x is not None
            and bbox_y is not None
            and bbox_h is not None
            and bbox_w is not None
        ):
            by_pattern[pattern_key][occ_key]["bboxes"].append(
                {
                    "bbox_x": float(bbox_x),
                    "bbox_y": float(bbox_y),
                    "bbox_height": float(bbox_h),
                    "bbox_width": float(bbox_w),
                }
            )

    return {
        pattern_id: list(occurrences.values())
        for pattern_id, occurrences in by_pattern.items()
    }
