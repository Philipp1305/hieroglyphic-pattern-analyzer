from __future__ import annotations

from flask import request

from ... import socketio
from src.database.tools import delete, select, update
from src.ngram import run_ngram


def _emit_to_request(event: str, payload: dict) -> None:
    sid = getattr(request, "sid", None)
    if sid:
        socketio.emit(event, payload, to=sid)
    else:
        socketio.emit(event, payload)


@socketio.on("c2s:start_patterns")
def start_patterns(payload=None):
    print(f"[ws_pattern] c2s:start_patterns payload={payload}")
    if isinstance(payload, dict):
        image_id = payload.get("image_id")
    else:
        image_id = payload

    if not image_id:
        print("[ws_pattern] start_patterns missing image_id")
        _emit_to_request(
            "s2c:start_patterns:response",
            {"status": "error", "message": "image_id is required"},
        )
        return

    try:
        image_id_int = int(image_id)
    except (TypeError, ValueError):
        print(f"[ws_pattern] start_patterns invalid image_id={image_id}")
        _emit_to_request(
            "s2c:start_patterns:response",
            {"status": "error", "message": "image_id must be an integer"},
        )
        return

    try:
        # Clear previous pattern results for idempotent runs.
        delete(
            "DELETE FROM T_NGRAM_PATTERN WHERE id_image = %s",
            (image_id_int,),
        )

        print(f"[ws_pattern] start_patterns image_id={image_id_int} starting")
        counts = run_ngram(image_id_int)
        patterns = len(counts)
        occurrences = sum(counts.values())
        print(
            f"[ws_pattern] start_patterns completed patterns={patterns} occurrences={occurrences}"
        )

        status_rows = select(
            "SELECT id FROM T_IMAGES_STATUS WHERE status_code = %s", ("NGRAMS",)
        )
        if status_rows:
            status_id = status_rows[0][0]
            update(
                "UPDATE T_IMAGES SET id_status = %s WHERE id = %s",
                (status_id, image_id_int),
            )
            print(f"[ws_pattern] start_patterns updated status_id={status_id}")
        else:
            print("[ws_pattern] start_patterns missing NGRAMS status code")

        _emit_to_request(
            "s2c:start_patterns:response",
            {
                "image_id": image_id_int,
                "status": "success",
                "status_code": "NGRAMS",
                "patterns": patterns,
                "occurrences": occurrences,
            },
        )
    except Exception as exc:
        print(f"[ws_pattern] start_patterns error={exc}")
        _emit_to_request(
            "s2c:start_patterns:response",
            {
                "image_id": image_id_int,
                "status": "error",
                "message": str(exc),
            },
        )
