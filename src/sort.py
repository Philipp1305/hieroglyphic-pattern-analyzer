from src.database.select import run_select
from src.database.connect import connect
from psycopg2.extras import execute_batch
from typing import List, Tuple, Any

X_IDX = 3
Y_IDX = 4

def sort_and_insert(
    image_id: int,
    tolerance: float,
    reading_direction: str = "ltr",
    x_index: int = X_IDX,
    y_index: int = Y_IDX,
):
    """Sort glyphs and insert directly into T_GLYPHES_SORTED."""
    
    # Get glyphs from database
    rows = run_select(
        "SELECT id, id_image, id_gardiner, bbox_x, bbox_y, bbox_width, bbox_height "
        "FROM T_GLYPHES_RAW WHERE id_image = %s",
        (image_id,)
    )
    
    if not rows:
        return 0
    
    # Sort by x, then y
    items = sorted(rows, key=lambda r: (r[x_index], r[y_index]))
    
    # Group into columns by x tolerance
    columns: List[List[Tuple[Any, ...]]] = []
    i = 0
    n = len(items)
    
    while i < n:
        x0 = items[i][x_index]
        current_col = []
        while i < n and items[i][x_index] <= x0 + tolerance:
            current_col.append(items[i])
            i += 1
        
        current_col.sort(key=lambda r: r[y_index])
        columns.append(current_col)
    
    # Build insert data
    data = []
    for c_idx, col in enumerate(columns):
        for r_idx, r in enumerate(col):
            data.append((r[0], c_idx, r_idx))  # (id_glyph, column, row)
    
    # Reverse column indices for RTL
    if reading_direction.lower() == "rtl":
        max_col = max(d[1] for d in data)
        data = [(d[0], max_col - d[1], d[2]) for d in data]
    
    # Insert into database
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO t_glyphes_sorted (id_glyph, v_column, v_row) VALUES (%s, %s, %s)",
                data
            )
        conn.commit()
        return len(data)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m src.sort <image_id> [tolerance]")
        sys.exit(1)
    
    image_id = int(sys.argv[1])
    tolerance = float(sys.argv[2]) if len(sys.argv) > 2 else 100.0
    rows = run_select("SELECT reading_direction FROM T_IMAGES WHERE id = %s", (image_id,))
    reading_dir = "rtl" if (rows and rows[0][0] == 1) else "ltr"
    
    count = sort_and_insert(image_id, tolerance, reading_dir)
    print(f"Sorted {count} glyphs for image {image_id}")
