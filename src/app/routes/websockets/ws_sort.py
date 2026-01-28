from flask import request, current_app

from ... import socketio
from src.database.tools import select, update
from src.process_image import process_image
from src.sort import run_sort
from src.app.services.status_service import ensure_status_code
from src.app.services.pipeline_service import emit_pipeline_status


def _emit_to_request(event: str, payload: dict) -> None:
    sid = getattr(request, "sid", None)
    if sid:
        socketio.emit(event, payload, to=sid)
    else:
        socketio.emit(event, payload)


@socketio.on("c2s:start_sorting")
def start_sorting(payload=None, tolerance=100):
    print(f"[ws_sort] c2s:start_sorting payload={payload} tolerance={tolerance}")
    if isinstance(payload, dict):
        image_id = payload.get("image_id")
        tolerance = payload.get("tolerance", tolerance)
    else:
        image_id = payload

    if not image_id:
        print("[ws_sort] start_sorting missing image_id")
        _emit_to_request(
            "s2c:start_sorting:response",
            {"status": "error", "message": "image_id is required"},
        )
        return

    try:
        tolerance_value = float(tolerance)
    except (TypeError, ValueError):
        print(
            f"[ws_sort] start_sorting invalid tolerance={tolerance}, defaulting to 100"
        )
        tolerance_value = 100

    try:
        status_start_id = ensure_status_code("SORT_START", "Sorting started")
        update(
            "UPDATE T_IMAGES SET id_status = %s WHERE id = %s",
            (status_start_id, image_id),
        )
        current_app.logger.info(
            "[ws_sort] SORT_START image_id=%s tol=%s", image_id, tolerance_value
        )
        emit_pipeline_status(
            image_id,
            "SORT_START",
            current_app._get_current_object(),  # type: ignore[attr-defined]
            status="running",
        )
        rows = select(
            "SELECT reading_direction FROM T_IMAGES WHERE id = %s", (image_id,)
        )
        reading_dir_value = rows[0][0] if rows else 0
        reading_direction = "rtl" if reading_dir_value == 1 else "ltr"

        print(
            f"[ws_sort] start_sorting image_id={image_id} direction={reading_direction} tolerance={tolerance_value}"
        )
        count, _ = run_sort(int(image_id), tolerance_value, reading_direction)
        print(f"[ws_sort] start_sorting sorted={count}")
        current_app.logger.info(
            "[ws_sort] SORT_VALIDATE image_id=%s sorted=%s", image_id, count
        )

        status_validate_id = ensure_status_code(
            "SORT_VALIDATE", "Sorting needs validation"
        )
        update(
            "UPDATE T_IMAGES SET id_status = %s WHERE id = %s",
            (status_validate_id, image_id),
        )
        print(f"[ws_sort] start_sorting updated status_id={status_validate_id}")
        emit_pipeline_status(
            image_id,
            "SORT_VALIDATE",
            current_app._get_current_object(),  # type: ignore[attr-defined]
            status="success",
            extra={"sorted": count},
        )

        _emit_to_request(
            "s2c:start_sorting:response",
            {
                "image_id": image_id,
                "status": "success",
                "status_code": "SORT_VALIDATE",
                "sorted": count,
            },
        )
    except Exception as exc:
        print(f"[ws_sort] start_sorting error={exc}")
        _emit_to_request(
            "s2c:start_sorting:response",
            {
                "image_id": image_id,
                "status": "error",
                "message": str(exc),
            },
        )


@socketio.on("c2s:process_image")
def start_processing(payload=None):
    print(f"[ws_sort] c2s:process_image payload={payload}")
    if isinstance(payload, dict):
        image_id = payload.get("image_id")
    else:
        image_id = payload

    if not image_id:
        print("[ws_sort] process_image missing image_id")
        _emit_to_request(
            "s2c:process_image:response",
            {"status": "error", "message": "image_id is required"},
        )
        return

    try:
        status_start_id = ensure_status_code("JSON_START", "JSON processing started")
        update(
            "UPDATE T_IMAGES SET id_status = %s WHERE id = %s",
            (status_start_id, image_id),
        )
        emit_pipeline_status(
            image_id,
            "JSON_START",
            current_app._get_current_object(),  # type: ignore[attr-defined]
            status="running",
        )
        current_app.logger.info("[ws_sort] JSON_START image_id=%s", image_id)
        count = process_image(int(image_id))
        current_app.logger.info(
            "[ws_sort] JSON_DONE image_id=%s processed=%s", image_id, count
        )
        status_done_id = ensure_status_code("JSON_DONE", "JSON processed")
        update(
            "UPDATE T_IMAGES SET id_status = %s WHERE id = %s",
            (status_done_id, image_id),
        )
        print(f"[ws_sort] process_image updated status_id={status_done_id}")
        emit_pipeline_status(
            image_id,
            "JSON_DONE",
            current_app._get_current_object(),  # type: ignore[attr-defined]
            status="success",
            extra={"processed": count},
        )

        _emit_to_request(
            "s2c:process_image:response",
            {
                "image_id": image_id,
                "status": "success",
                "status_code": "JSON_DONE",
                "processed": count,
            },
        )
    except Exception as exc:
        print(f"[ws_sort] process_image error={exc}")
        _emit_to_request(
            "s2c:process_image:response",
            {
                "image_id": image_id,
                "status": "error",
                "message": str(exc),
            },
        )
