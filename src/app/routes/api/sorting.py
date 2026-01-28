from __future__ import annotations

from typing import Dict, List, Tuple, TypedDict

from flask import jsonify, request, current_app

from . import bp
from src.database.tools import insert, select, update
from src.sort import sort as run_sort_algorithm
from src.app.services.pipeline_service import (
    STATUS_SORT_DONE,
    emit_pipeline_status,
    start_analysis_async,
)
from src.app.services.status_service import change_image_status, ensure_status_code
from src.cleanup import delete_existing_entries


class ColumnEntry(TypedDict):
    col: int
    glyph_ids: list[int]


@bp.get("/sorting/<int:image_id>")
def get_sorting_columns(image_id: int):
    if not _image_exists(image_id):
        return {"error": "image not found"}, 404

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
    advance_status = bool(data.get("advance_status"))
    tolerance_raw = data.get("tolerance")
    tolerance_value: int | None = None
    if tolerance_raw is not None:
        try:
            tolerance_value = int(round(float(tolerance_raw)))
        except (TypeError, ValueError):
            return {"error": "tolerance must be numeric"}, 400
        if tolerance_value <= 0:
            return {"error": "tolerance must be positive"}, 400

    normalized_columns: list[tuple[int, list[int]]] = []
    for entry in columns:
        if not isinstance(entry, dict):
            return {"error": "Invalid column entry"}, 400
        col_idx = entry.get("col")
        glyph_ids = entry.get("glyph_ids")
        if not isinstance(col_idx, int) or col_idx < 0:
            return {"error": "col must be a non-negative integer"}, 400
        if not isinstance(glyph_ids, list):
            return {"error": "glyph_ids must be a list"}, 400
        glyph_list: list[int] = []
        for glyph_id in glyph_ids:
            if not isinstance(glyph_id, int):
                return {"error": "glyph_ids must contain integers"}, 400
            glyph_list.append(int(glyph_id))
        if glyph_list:
            normalized_columns.append((int(col_idx), glyph_list))

    valid_glyph_ids = _glyph_ids_for_image(image_id)
    if not valid_glyph_ids:
        return {"error": "image has no glyphs"}, 400

    all_glyph_ids = [gid for _, glyphs in normalized_columns for gid in glyphs]
    invalid = [gid for gid in all_glyph_ids if gid not in valid_glyph_ids]
    if invalid:
        return {"error": f"glyph ids do not belong to image: {invalid}"}, 400

    ordered_entries: list[tuple[int, int, int]] = []
    if normalized_columns:
        normalized_columns.sort(key=lambda item: item[0])
        base_col = normalized_columns[0][0]
        for offset, (col_val, glyphs) in enumerate(normalized_columns):
            mapped_col = base_col + offset
            for row_idx, glyph_id in enumerate(glyphs):
                ordered_entries.append((glyph_id, mapped_col, row_idx))

    delete_existing_entries(image_id, "ANALYSIS")
    delete_existing_entries(image_id, "SORTING")

    if ordered_entries:
        insert(
            """
            INSERT INTO t_glyphes_sorted (id_glyph, v_column, v_row)
            VALUES (%s, %s, %s)
            """,
            ordered_entries,
            many=True,
        )

    if tolerance_value is not None:
        update(
            "UPDATE t_images SET sort_tolerance = %s WHERE id = %s",
            (tolerance_value, image_id),
        )

    status_updated = False
    if advance_status:
        ensure_status_code(STATUS_SORT_DONE, "Sorting done")
        change_image_status(image_id, STATUS_SORT_DONE)
        status_updated = True
        try:
            emit_pipeline_status(
                image_id,
                STATUS_SORT_DONE,
                current_app._get_current_object(),  # type: ignore[attr-defined]
                status="success",
            )
        except Exception:
            pass
        try:
            start_analysis_async(
                image_id,
                current_app._get_current_object(),  # type: ignore[attr-defined]
            )
        except Exception as exc:  # pragma: no cover - safety net
            try:
                current_app.logger.exception("failed to start analysis", exc_info=exc)
            except Exception:
                pass

    return jsonify(
        {
            "status": "ok",
            "updated": len(ordered_entries),
            "tolerance": tolerance_value,
            "status_updated": status_updated,
        }
    )


@bp.post("/sorting/<int:image_id>/preview")
def preview_sorting(image_id: int):
    if not _image_exists(image_id):
        return {"error": "image not found"}, 404

    payload = request.get_json(silent=True) or {}
    tolerance_raw = payload.get("tolerance")
    if tolerance_raw is None:
        return {"error": "tolerance must be provided"}, 400
    try:
        tolerance_value = float(tolerance_raw)
    except (TypeError, ValueError):
        return {"error": "tolerance must be a number"}, 400
    if tolerance_value <= 0:
        return {"error": "tolerance must be positive"}, 400

    glyph_rows = _glyph_rows(image_id)
    if not glyph_rows:
        return {"error": "image has no glyphs"}, 400

    reading_direction = _reading_direction(image_id)
    ordered_entries, _ = run_sort_algorithm(
        glyph_rows, tolerance_value, reading_direction
    )
    columns_payload = _build_columns_payload(ordered_entries)

    return jsonify(
        {
            "image_id": image_id,
            "sort_version": "preview",
            "tolerance": tolerance_value,
            "reading_direction": reading_direction,
            "columns": columns_payload,
            "glyphs": _glyph_metadata(image_id),
            "count": len(ordered_entries),
        }
    )


def _image_exists(image_id: int) -> bool:
    rows = select("SELECT 1 FROM t_images WHERE id = %s", (image_id,))
    return bool(rows)


def _glyph_ids_for_image(image_id: int) -> set[int]:
    rows = select("SELECT id FROM t_glyphes_raw WHERE id_image = %s", (image_id,))
    return {int(row[0]) for row in rows}


def _glyph_metadata(image_id: int) -> dict[str, dict[str, float | str]]:
    rows = select(
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


def _glyph_rows(image_id: int) -> list[tuple]:
    return select(
        """
        SELECT id, id_image, id_gardiner, bbox_x, bbox_y, bbox_width, bbox_height
        FROM t_glyphes_raw
        WHERE id_image = %s
        """,
        (image_id,),
    )


def _reading_direction(image_id: int) -> str:
    rows = select("SELECT reading_direction FROM t_images WHERE id = %s", (image_id,))
    if not rows:
        return "ltr"
    value = rows[0][0]
    return "rtl" if str(value) == "1" else "ltr"


def _current_status_code(image_id: int) -> str | None:
    rows = select(
        """
        SELECT s.status_code
        FROM t_images AS i
        LEFT JOIN t_images_status AS s ON s.id = i.id_status
        WHERE i.id = %s
        """,
        (image_id,),
    )
    if not rows:
        return None
    return rows[0][0]


def _status_id_by_code(status_code: str) -> int | None:
    rows = select(
        "SELECT id FROM t_images_status WHERE UPPER(status_code) = UPPER(%s)",
        (status_code,),
    )
    if not rows:
        return None
    return int(rows[0][0])


def _build_columns_payload(entries: List[Tuple[int, int, int]]) -> list[ColumnEntry]:
    columns: Dict[int, List[int]] = {}
    for glyph_id, col_idx, row_idx in sorted(
        entries, key=lambda item: (item[1], item[2])
    ):
        glyph_id_int = int(glyph_id)
        col_idx_int = int(col_idx)
        columns.setdefault(col_idx_int, []).append(glyph_id_int)

    payload: list[ColumnEntry] = []
    for col_idx, glyph_ids in sorted(columns.items()):
        payload.append(ColumnEntry(col=col_idx, glyph_ids=list(glyph_ids)))
    return payload
