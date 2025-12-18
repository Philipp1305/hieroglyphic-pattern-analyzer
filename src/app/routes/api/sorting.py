from __future__ import annotations

from typing import Dict, List

from flask import jsonify, request
from psycopg2.extras import execute_values

from src.database.connect import connect
from src.database.select import run_select

from . import bp


@bp.get("/sorting/<int:image_id>")
def get_sorting_columns(image_id: int):
    if not _image_exists(image_id):
        return {"error": "image not found"}, 404

    rows = run_select(
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

    columns_payload = [
        {"col": col_idx, "glyph_ids": glyph_ids}
        for col_idx, glyph_ids in sorted(columns.items())
    ]

    glyph_meta = _glyph_metadata(image_id)

    return jsonify(
        {
            "image_id": image_id,
            "sort_version": 1,
            "columns": columns_payload,
            "glyphs": glyph_meta,
        }
    )


@bp.put("/sorting/<int:image_id>")
def apply_sorting_snapshot(image_id: int):
    if not _image_exists(image_id):
        return {"error": "image not found"}, 404

    data = request.get_json(silent=True) or {}
    columns = data.get("columns")
    if not isinstance(columns, list):
        return {"error": "columns must be a list"}, 400

    ordered_entries: list[tuple[int, int, int]] = []
    for entry in columns:
        if not isinstance(entry, dict):
            return {"error": "Invalid column entry"}, 400
        col_idx = entry.get("col")
        glyph_ids = entry.get("glyph_ids")
        if not isinstance(col_idx, int) or col_idx < 0:
            return {"error": "col must be a non-negative integer"}, 400
        if not isinstance(glyph_ids, list):
            return {"error": "glyph_ids must be a list"}, 400
        for row_idx, glyph_id in enumerate(glyph_ids):
            if not isinstance(glyph_id, int):
                return {"error": "glyph_ids must contain integers"}, 400
            ordered_entries.append((glyph_id, col_idx, row_idx))

    valid_glyph_ids = _glyph_ids_for_image(image_id)
    if not valid_glyph_ids:
        return {"error": "image has no glyphs"}, 400

    invalid = [gid for gid, _, _ in ordered_entries if gid not in valid_glyph_ids]
    if invalid:
        return {"error": f"glyph ids do not belong to image: {invalid}"}, 400

    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM t_glyphes_sorted
                WHERE id_glyph = ANY(%s)
                """,
                (list(valid_glyph_ids),),
            )

            if ordered_entries:
                execute_values(
                    cur,
                    """
                    INSERT INTO t_glyphes_sorted (id_glyph, v_column, v_row)
                    VALUES %s
                    """,
                    ordered_entries,
                )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return jsonify({"status": "ok", "updated": len(ordered_entries)})


def _image_exists(image_id: int) -> bool:
    rows = run_select("SELECT 1 FROM t_images WHERE id = %s", (image_id,))
    return bool(rows)


def _glyph_ids_for_image(image_id: int) -> set[int]:
    rows = run_select("SELECT id FROM t_glyphes_raw WHERE id_image = %s", (image_id,))
    return {int(row[0]) for row in rows}


def _glyph_metadata(image_id: int) -> dict[str, dict[str, float | str]]:
    rows = run_select(
        """
        SELECT gr.id, gr.bbox_x, gr.bbox_y, gr.bbox_width, gr.bbox_height,
               gc.code, gc.unicode
        FROM t_glyphes_raw AS gr
        LEFT JOIN t_gardiner_codes AS gc ON gc.id = gr.id_gardiner
        WHERE id_image = %s
        """,
        (image_id,),
    )
    glyphs: dict[str, dict[str, float | str]] = {}
    for glyph_id, x, y, width, height, code, unicode_val in rows:
        glyphs[str(int(glyph_id))] = {
            "x": float(x),
            "y": float(y),
            "width": float(width),
            "height": float(height),
            "gardiner_code": code or "",
            "unicode": unicode_val or "",
        }
    return glyphs
