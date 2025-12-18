from app import socketio
from sort import sort_and_insert
from database.select import run_select

@socketio.on("c2s:start_sorting")
def start_sorting(image_id, tolerance=100):
    rows = run_select(
        "SELECT reading_direction FROM T_IMAGES WHERE id = %s", (image_id,)
    )
    reading_dir_value = rows[0][0] if rows else 0
    reading_direction = "rtl" if reading_dir_value == 1 else "ltr"

    sort_and_insert(image_id, tolerance, reading_direction)

    socketio.emit("s2c:start_sorting:response", {"image_id": image_id, "status": "success"})