from __future__ import annotations

from typing import Dict, List, Set

from flask import jsonify

from . import bp
from src.database.tools import select


def _normalize_code(value: str | None) -> str:
    if not value:
        return ""
    return value.strip().upper()


def _normalize_unicode_str(value: str | None) -> str:
    if not value:
        return ""
    cleaned = value.strip().upper()
    return cleaned if cleaned.startswith("U+") else f"U+{cleaned}"


@bp.get("/glyphes/<int:image_id>/stats")
def glyph_stats(image_id: int):
    glyphs = _glyph_metadata(image_id)
    columns = _ordered_columns(image_id)
    patterns = _pattern_rows(image_id)

    groups: Dict[str, Dict] = {}

    def key_for(gid: int) -> str:
        meta = glyphs.get(str(gid), {})
        code = (meta.get("gardiner_code") or "").strip()
        unicode_val = (meta.get("unicode") or "").strip()
        if code:
            return code
        if unicode_val:
            return unicode_val.upper()
        return f"ID-{gid}"

    def symbol_for(gid: int) -> str:
        meta = glyphs.get(str(gid), {})
        unicode_val = (meta.get("unicode") or "").strip()
        if unicode_val:
            cleaned = unicode_val.replace("U+", "")
            try:
                return chr(int(cleaned, 16))
            except Exception:
                pass
        code = (meta.get("gardiner_code") or "").strip()
        return code or f"#{gid}"

    # Initialize groups
    for gid_str in glyphs.keys():
        gid = int(gid_str)
        key = key_for(gid)
        groups.setdefault(
            key,
            {
                "key": key,
                "code": (glyphs[gid_str].get("gardiner_code") or "").strip(),
                "unicode": (glyphs[gid_str].get("unicode") or "").strip(),
                "symbol": symbol_for(gid),
                "gardiner_id": glyphs[gid_str].get("gardiner_id"),
                "ids": [],
                "count": 0,
                "positions": {"start": 0, "mid": 0, "end": 0, "bins": [0] * 12},
                "transitions": {"prev": {}, "next": {}},
            },
        )
        groups[key]["ids"].append(gid)
        groups[key]["count"] += 1
        gid_gardiner = glyphs[gid_str].get("gardiner_id")
        if gid_gardiner is not None:
            groups[key].setdefault("gardiner_ids", set()).add(int(gid_gardiner))

    # Compute order-based stats
    for col in columns:
        glyph_ids = col
        last_idx = len(glyph_ids) - 1
        for idx, gid in enumerate(glyph_ids):
            key = key_for(gid)
            group = groups[key]
            # positions
            if idx == 0:
                group["positions"]["start"] += 1
            elif idx == last_idx:
                group["positions"]["end"] += 1
            else:
                group["positions"]["mid"] += 1
            if last_idx > 0:
                bin_idx = min(11, max(0, int((idx / last_idx) * 12)))
                group["positions"]["bins"][bin_idx] += 1

            # transitions
            if idx > 0:
                prev_id = glyph_ids[idx - 1]
                prev_key = key_for(prev_id)
                group["transitions"]["prev"][prev_key] = (
                    group["transitions"]["prev"].get(prev_key, 0) + 1
                )
            if idx < last_idx:
                next_id = glyph_ids[idx + 1]
                next_key = key_for(next_id)
                group["transitions"]["next"][next_key] = (
                    group["transitions"]["next"].get(next_key, 0) + 1
                )

            # contexts removed; replaced by pattern stats

    # Build payload
    # Build gardiner lookup for patterns
    pattern_gardiner_ids: Set[int] = set()
    for _, gids, _, _ in patterns:
        for gid in gids:
            if gid is not None:
                pattern_gardiner_ids.add(int(gid))
    gardiner_lookup = (
        _gardiner_map(pattern_gardiner_ids) if pattern_gardiner_ids else {}
    )

    groups_payload = []
    for group in groups.values():
        prev_sorted = sorted(
            group["transitions"]["prev"].items(), key=lambda kv: kv[1], reverse=True
        )
        next_sorted = sorted(
            group["transitions"]["next"].items(), key=lambda kv: kv[1], reverse=True
        )
        combined = prev_sorted + next_sorted
        combined_sorted = sorted(combined, key=lambda kv: kv[1], reverse=True)

        # patterns containing this group's gardiner_ids
        group_gardiner_ids = set(group.get("gardiner_ids") or [])
        pattern_matches = []
        if group_gardiner_ids:
            for pid, gids, seq_len, seq_count in patterns:
                gids_set = {int(g) for g in gids if g is not None}
                if not gids_set.intersection(group_gardiner_ids):
                    continue
                codes = [
                    _normalize_code(gardiner_lookup.get(gid, {}).get("code", ""))
                    for gid in gids
                    if gid is not None
                ]
                unicodes = [
                    _normalize_unicode_str(
                        gardiner_lookup.get(gid, {}).get("unicode", "")
                    )
                    for gid in gids
                    if gid is not None
                ]
                pattern_matches.append(
                    {
                        "id": int(pid),
                        "length": int(seq_len),
                        "count": int(seq_count),
                        "codes": codes,
                        "unicode": unicodes,
                        "label": " ".join(c for c in codes if c),
                    }
                )
            pattern_matches.sort(key=lambda p: (-p["count"], -p["length"], p["id"]))
            pattern_matches = pattern_matches[:10]

        groups_payload.append(
            {
                "key": group["key"],
                "code": group["code"],
                "unicode": group["unicode"],
                "symbol": group["symbol"],
                "ids": group["ids"],
                "count": group["count"],
                "positions": group["positions"],
                "transitions": {
                    "prev": [{"key": k, "count": v} for k, v in prev_sorted[:8]],
                    "next": [{"key": k, "count": v} for k, v in next_sorted[:8]],
                    "matrix": [{"key": k, "count": v} for k, v in combined_sorted[:5]],
                },
                "patterns": pattern_matches,
            }
        )

    groups_payload.sort(key=lambda g: (-g["count"], g["key"]))

    return jsonify(
        {
            "image_id": image_id,
            "types": len(groups_payload),
            "groups": groups_payload,
            "glyphs": glyphs,
        }
    )


def _glyph_metadata(image_id: int) -> dict[str, dict[str, float | str | int]]:
    rows = select(
        """
        SELECT gr.id, gr.bbox_x, gr.bbox_y, gr.bbox_width, gr.bbox_height,
               gr.id_gardiner, gc.code, gc.unicode
        FROM t_glyphes_raw AS gr
        LEFT JOIN t_gardiner_codes AS gc ON gc.id = gr.id_gardiner
        WHERE id_image = %s
        """,
        (image_id,),
    )
    glyphs: dict[str, dict[str, float | str]] = {}
    for glyph_id, x, y, width, height, gid_gardiner, code, unicode_val in rows:
        glyphs[str(int(glyph_id))] = {
            "x": float(x),
            "y": float(y),
            "width": float(width),
            "height": float(height),
            "gardiner_id": int(gid_gardiner) if gid_gardiner is not None else None,
            "gardiner_code": code or "",
            "unicode": unicode_val or "",
        }
    return glyphs


def _ordered_columns(image_id: int) -> List[List[int]]:
    rows = select(
        """
        SELECT gs.v_column, gs.v_row, gs.id_glyph
        FROM t_glyphes_sorted AS gs
        JOIN t_glyphes_raw AS gr ON gr.id = gs.id_glyph
        WHERE gr.id_image = %s
        ORDER BY gs.v_column, gs.v_row
        """,
        (image_id,),
    )
    columns: Dict[int, List[int]] = {}
    for col_idx, _, glyph_id in rows:
        col_idx = int(col_idx)
        columns.setdefault(col_idx, []).append(int(glyph_id))
    return [glyph_ids for _, glyph_ids in sorted(columns.items())]


def _pattern_rows(image_id: int) -> List[tuple]:
    rows = select(
        """
        SELECT id, gardiner_ids, sequence_length, sequence_count
        FROM t_suffixarray_patterns
        WHERE id_image = %s
        """,
        (image_id,),
    )
    normalized = []
    for pid, gids, seq_len, seq_count in rows:
        gids_list = gids or []
        normalized.append(
            (
                int(pid),
                [int(g) for g in gids_list if g is not None],
                int(seq_len),
                int(seq_count),
            )
        )
    return normalized


def _gardiner_map(ids: Set[int]) -> dict[int, dict[str, str]]:
    if not ids:
        return {}
    rows = select(
        "SELECT id, code, unicode FROM t_gardiner_codes WHERE id = ANY(%s)",
        (list(ids),),
    )
    return {
        int(row[0]): {"code": row[1] or "", "unicode": row[2] or ""} for row in rows
    }
