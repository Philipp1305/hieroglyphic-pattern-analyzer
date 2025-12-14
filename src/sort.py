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
    method: str = "bbox",
    preview: bool = False,
):
    """Sort glyphs and optionally insert into T_GLYPHES_SORTED."""
    
    # Get glyphs from database
    rows = run_select(
        "SELECT id, id_image, id_gardiner, bbox_x, bbox_y, bbox_width, bbox_height "
        "FROM T_GLYPHES_RAW WHERE id_image = %s",
        (image_id,),
    )

    if not rows:
        return 0, {}
    
    # Calculate coordinates based on method
    if method == "center":
        # Use center of gravity: (x + width/2, y + height/2)
        items = [(r[0], r[1], r[2], r[3] + r[5]/2, r[4] + r[6]/2, r[5], r[6]) for r in rows]
        x_idx, y_idx = 3, 4
    else:
        # Use top-left corner (bbox_x, bbox_y)
        items = rows
        x_idx, y_idx = X_IDX, Y_IDX
    
    # Sort by x, then y
    items = sorted(items, key=lambda r: (r[x_idx], r[y_idx]))
    
    # Group into columns by x tolerance
    columns: List[List[Tuple[Any, ...]]] = []
    i = 0
    n = len(items)

    while i < n:
        x0 = items[i][x_idx]
        current_col = []
        while i < n and items[i][x_idx] <= x0 + tolerance:
            current_col.append(items[i])
            i += 1
        
        current_col.sort(key=lambda r: r[y_idx])
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
    
    # Preview mode - just return stats
    if preview:
        col_stats = {}
        for _, col_idx, _ in data:
            col_stats[col_idx] = col_stats.get(col_idx, 0) + 1
        return len(data), col_stats
    
    # Insert into database
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO t_glyphes_sorted (id_glyph, v_column, v_row) VALUES (%s, %s, %s)",
                data,
            )
        conn.commit()
        return len(data), {}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    
    # Parse arguments
    method = "bbox"
    preview = False
    args = []
    
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--method" and i + 1 < len(sys.argv):
            method = sys.argv[i + 1]
            i += 2
        elif arg.startswith("--method="):
            method = arg.split("=")[1]
            i += 1
        elif arg == "--preview":
            preview = True
            i += 1
        else:
            args.append(arg)
            i += 1
    
    if len(args) < 1:
        print("Usage: python -m src.sort <image_id> [tolerance] [--method bbox|center] [--preview]")
        print("Examples:")
        print("  python -m src.sort 2")
        print("  python -m src.sort 2 --method center --preview")
        print("  python -m src.sort 2 150 --method center")
        sys.exit(1)
    
    image_id = int(args[0])
    tolerance = float(args[1]) if len(args) > 1 else 100.0
    
    rows = run_select("SELECT reading_direction FROM T_IMAGES WHERE id = %s", (image_id,))
    reading_dir = "rtl" if (rows and rows[0][0] == 1) else "ltr"
    
    count, col_stats = sort_and_insert(image_id, tolerance, reading_dir, method, preview)
    
    if preview:
        print(f"\nPreview mode (method={method}, tolerance={tolerance})")
        print(f"Total glyphs: {count}")
        print(f"Columns: {len(col_stats)}")
        print(f"\nColumn distribution:")
        for col in sorted(col_stats.keys()):
            print(f"  Column {col}: {col_stats[col]} glyphs")
    else:
        print(f"Sorted {count} glyphs for image {image_id} (method={method})")
