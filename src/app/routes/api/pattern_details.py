from __future__ import annotations

from flask import jsonify

from src.database.tools import select
from src.sentence_lookup_db import lookup_all

from . import bp
from .patterns import (
    _gardiner_map_for_ids,
    _normalize_gardiner_code,
    _normalize_unicode,
    _occurrences_with_bboxes,
    _unicode_to_symbol,
)


def _fetch_pattern_row(pattern_id: int):
    rows = select(
        """
        SELECT id, id_image, gardiner_ids, sequence_length, sequence_count
        FROM t_suffixarray_patterns
        WHERE id = %s
        """,
        (pattern_id,),
    )
    if not rows:
        return None
    pat_id, image_id, gardiner_ids, length, count = rows[0]
    ids = [int(gid) for gid in (gardiner_ids or []) if gid is not None]
    return {
        "id": int(pat_id),
        "image_id": int(image_id) if image_id is not None else None,
        "gardiner_ids": ids,
        "length": int(length) if length is not None else len(ids),
        # number of occurrences of this pattern in the image
        "count": int(count) if count is not None else 0,
    }


def _build_pattern_payload(pattern: dict) -> dict:
    gardiner_ids = pattern.get("gardiner_ids", [])
    gardiner_map = _gardiner_map_for_ids(gardiner_ids)

    unicode_values = [
        _normalize_unicode(gardiner_map.get(gid, {}).get("unicode", ""))
        for gid in gardiner_ids
    ]
    symbol_values = [_unicode_to_symbol([u]) if u else "" for u in unicode_values]
    gardiner_codes = [
        _normalize_gardiner_code(gardiner_map.get(gid, {}).get("code", ""))
        for gid in gardiner_ids
    ]
    symbol = "".join(val for val in symbol_values if val)
    label = " ".join(code for code in gardiner_codes if code)

    return {
        **pattern,
        "gardiner_codes": gardiner_codes,
        "unicode_values": unicode_values,
        "symbol_values": symbol_values,
        "symbol": symbol,
        "gardiner_label": label,
    }


@bp.get("/patterns/<int:pattern_id>/details")
def get_pattern_details(pattern_id: int):
    pattern_row = _fetch_pattern_row(pattern_id)
    if pattern_row is None:
        return {"error": "pattern not found"}, 404

    pattern_payload = _build_pattern_payload(pattern_row)
    gardiner_codes = [
        code for code in pattern_payload.get("gardiner_codes", []) if code
    ]

    sentences_raw = (
        lookup_all(gardiner_codes, include_partials=True) if gardiner_codes else []
    )
    print(f"[pattern_details] sentences found (raw): {len(sentences_raw)}")

    def _to_int(val) -> int:
        try:
            return int(val)
        except Exception:
            return 0

    # Deduplicate by ID first
    sentences_by_id: dict[str, dict] = {}
    for s in sentences_raw:
        sid_raw = s.get("id")
        if sid_raw is None:
            continue
        sid = str(sid_raw)
        if sid in sentences_by_id:
            sentences_by_id[sid]["match_occurrence_count"] = sentences_by_id[sid].get(
                "match_occurrence_count", 0
            ) + _to_int(s.get("match_occurrence_count", 0))
            sentences_by_id[sid].setdefault("matched_patterns", []).extend(
                s.get("matched_patterns", [])
            )
        else:
            sentences_by_id[sid] = s

    # Merge sentences with identical content (transcription / translation) but different TLA IDs
    grouped: list[dict] = []
    by_key: dict[tuple[str, str], dict] = {}

    def _norm(text: str | None) -> str:
        if not text:
            return ""
        cleaned = " ".join(text.strip().split())
        return cleaned.lower()

    def _sentence_key(sent: dict) -> tuple[str, str]:
        return (
            _norm(sent.get("transcription")),
            _norm(sent.get("translation")),
        )

    for s in sentences_by_id.values():
        key = _sentence_key(s)
        if key in by_key:
            agg = by_key[key]
            agg["match_occurrence_count"] += _to_int(s.get("match_occurrence_count", 0))
            agg.setdefault("matched_patterns", []).extend(s.get("matched_patterns", []))
            agg.setdefault("tla_ids", []).append(s.get("id"))
        else:
            copy = dict(s)
            copy["tla_ids"] = [s.get("id")]
            by_key[key] = copy
            grouped.append(copy)

    sentences = grouped

    match_occurrences = sum(
        item.get("match_occurrence_count", 0) or 0 for item in sentences
    )

    occurrences = _occurrences_with_bboxes([pattern_id]).get(pattern_id, [])

    response = jsonify(
        {
            "pattern": pattern_payload,
            "occurrence_count": pattern_payload.get("count", 0),
            "sentences": sentences,
            "sentence_count": len(sentences),
            "match_occurrence_total": match_occurrences,
            "occurrences": occurrences,
        }
    )
    response.headers["Cache-Control"] = "no-store"
    return response
