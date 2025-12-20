from flask import request

from ... import socketio
from src.database.tools import select, update
from src.process_image import process_image
from src.sort import run_sort


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
        print(f"[ws_sort] start_sorting invalid tolerance={tolerance}, defaulting to 100")
        tolerance_value = 100

    try:
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

        status_rows = select(
            "SELECT id FROM T_IMAGES_STATUS WHERE status_code = %s", ("SORT_VALIDATE",)
        )
        if status_rows:
            status_id = status_rows[0][0]
            update(
                "UPDATE T_IMAGES SET id_status = %s WHERE id = %s",
                (status_id, image_id),
            )
            print(f"[ws_sort] start_sorting updated status_id={status_id}")

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
        print(f"[ws_sort] process_image image_id={image_id} starting")
        count = process_image(int(image_id))
        print(f"[ws_sort] process_image inserted={count}")
        status_rows = select(
            "SELECT id FROM T_IMAGES_STATUS WHERE status_code = %s", ("JSON",)
        )
        if status_rows:
            status_id = status_rows[0][0]
            update(
                "UPDATE T_IMAGES SET id_status = %s WHERE id = %s",
                (status_id, image_id),
            )
            print(f"[ws_sort] process_image updated status_id={status_id}")

        _emit_to_request(
            "s2c:process_image:response",
            {
                "image_id": image_id,
                "status": "success",
                "status_code": "JSON",
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
