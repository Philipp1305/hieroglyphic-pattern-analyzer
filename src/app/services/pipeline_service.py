from __future__ import annotations

import threading
from typing import Optional

from flask import current_app
from src.database.tools import select
from src.process_image import process_image
from src.suffixarray import run_suffixarray
from src.app.services.status_service import change_image_status, ensure_status_code
from src.sort import run_sort

STATUS_UPLOAD_DONE = "UPLOAD"
STATUS_JSON_START = "JSON_START"
STATUS_JSON_DONE = "JSON_DONE"
STATUS_SORT_START = "SORT_START"
STATUS_SORT_VALIDATE = "SORT_VALIDATE"
STATUS_SORT_DONE = "SORT_DONE"
STATUS_ANALYZE_START = "ANALYZE_START"
STATUS_ANALYZE_DONE = "ANALYZE_DONE"
STATUS_DONE = "DONE"


def start_pipeline_async(image_id: int, app=None) -> threading.Thread:
    """Kick off the pipeline in a background thread."""
    app_obj = app or current_app._get_current_object()  # type: ignore[attr-defined]
    try:
        app_obj.logger.info("[pipeline] scheduling async run image_id=%s", image_id)
    except Exception:
        pass
    thread = threading.Thread(
        target=_run_pipeline_safely, args=(int(image_id), app_obj), daemon=True
    )
    thread.start()
    return thread


def _run_pipeline_safely(image_id: int, app) -> None:
    try:
        with app.app_context():
            app.logger.info("[pipeline] run start image_id=%s", image_id)
            _run_pipeline(image_id, app)
            app.logger.info("[pipeline] run finished image_id=%s", image_id)
    except Exception as exc:  # pragma: no cover - safety net
        try:
            app.logger.exception("pipeline failed", exc_info=exc)
        except Exception:
            pass
        emit_pipeline_status(image_id, "ERROR", app, extra={"message": str(exc)})


def start_analysis_async(image_id: int, app=None) -> threading.Thread:
    """Run the suffixarray analysis in a background thread with live status updates."""
    app_obj = app or current_app._get_current_object()  # type: ignore[attr-defined]
    try:
        app_obj.logger.info("[pipeline] scheduling analysis image_id=%s", image_id)
    except Exception:
        pass
    thread = threading.Thread(
        target=_run_analysis_safely, args=(int(image_id), app_obj), daemon=True
    )
    thread.start()
    return thread


def _run_analysis_safely(image_id: int, app) -> None:
    try:
        with app.app_context():
            _run_analysis(image_id, app)
    except Exception as exc:  # pragma: no cover - safety net
        try:
            app.logger.exception("analysis failed", exc_info=exc)
        except Exception:
            pass
        emit_pipeline_status(image_id, "ERROR", app, extra={"message": str(exc)})


def _run_pipeline(image_id: int, app) -> None:
    # JSON processing
    app.logger.info("[pipeline] JSON_START image_id=%s", image_id)
    change_image_status(image_id, STATUS_JSON_START)
    emit_pipeline_status(image_id, STATUS_JSON_START, app, status="running")

    processed = process_image(int(image_id))
    app.logger.info(
        "[pipeline] JSON_DONE image_id=%s processed=%s", image_id, processed
    )
    change_image_status(image_id, STATUS_JSON_DONE)
    emit_pipeline_status(
        image_id,
        STATUS_JSON_DONE,
        app,
        status="success",
        extra={"processed": processed},
    )

    # Sort
    tolerance, reading_direction = _load_sort_params(image_id)
    change_image_status(image_id, STATUS_SORT_START)
    app.logger.info(
        "[pipeline] SORT_START image_id=%s tolerance=%s dir=%s",
        image_id,
        tolerance,
        reading_direction,
    )
    emit_pipeline_status(image_id, STATUS_SORT_START, app, status="running")

    sorted_count, _ = run_sort(
        int(image_id),
        float(tolerance) if tolerance is not None else 100.0,
        reading_direction or "ltr",
    )
    app.logger.info(
        "[pipeline] SORT_VALIDATE image_id=%s sorted=%s", image_id, sorted_count
    )
    change_image_status(image_id, STATUS_SORT_VALIDATE)
    emit_pipeline_status(
        image_id,
        STATUS_SORT_VALIDATE,
        app,
        status="success",
        extra={"sorted": sorted_count},
    )


def _run_analysis(image_id: int, app) -> None:
    """Second stage: pattern analysis via suffix array."""
    app.logger.info("[pipeline] ANALYZE_START image_id=%s", image_id)
    change_image_status(image_id, STATUS_ANALYZE_START)
    emit_pipeline_status(image_id, STATUS_ANALYZE_START, app, status="running")

    run_suffixarray(int(image_id))

    app.logger.info("[pipeline] DONE image_id=%s", image_id)
    change_image_status(image_id, STATUS_DONE)
    emit_pipeline_status(image_id, STATUS_DONE, app, status="success")


def _load_sort_params(image_id: int) -> tuple[Optional[float], Optional[str]]:
    rows = select(
        "SELECT sort_tolerance, reading_direction FROM T_IMAGES WHERE id = %s",
        (image_id,),
    )
    if not rows:
        return None, None
    tolerance, reading_dir = rows[0]
    reading_direction = "rtl" if str(reading_dir) == "1" else "ltr"
    return tolerance, reading_direction


def emit_pipeline_status(
    image_id: int,
    status_code: str,
    app,
    status: str | None = None,
    extra: dict | None = None,
) -> None:
    payload = {"image_id": image_id, "status_code": status_code}
    if status:
        payload["status"] = status
    if extra:
        payload.update(extra)
    try:
        sio = app.extensions.get("socketio") if app else None
        if sio:
            # Flask-SocketIO 5+ no longer accepts broadcast kwarg; emitting without a room targets all clients.
            sio.emit("s2c:pipeline_status", payload)
    except Exception as exc:  # pragma: no cover - guard against socket failures
        try:
            if app:
                app.logger.warning("pipeline emit failed", exc_info=exc)
        except Exception:
            pass


# Ensure required status codes exist at import time.
for code, label in [
    (STATUS_UPLOAD_DONE, "Upload done"),
    (STATUS_JSON_START, "JSON processing started"),
    (STATUS_JSON_DONE, "JSON processed"),
    (STATUS_SORT_START, "Sorting started"),
    (STATUS_SORT_VALIDATE, "Sorting needs validation"),
    (STATUS_SORT_DONE, "Sorting done"),
    (STATUS_ANALYZE_START, "Pattern analysis started"),
    (STATUS_ANALYZE_DONE, "Pattern analysis done"),
    (STATUS_DONE, "Done"),
]:
    try:
        ensure_status_code(code, label)
    except Exception:
        # Avoid import-time crash; will be retried on first use.
        pass
