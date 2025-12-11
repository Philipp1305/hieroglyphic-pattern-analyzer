"""Extract JSON annotations from T_IMAGES and insert into T_GLYPHES_RAW."""

import sys
from psycopg2.extras import execute_batch
from src.database.select import run_select
from src.database.connect import connect


def process_image(image_id):
    rows = run_select("SELECT json FROM T_IMAGES WHERE id = %s", (image_id,))
    if not rows:
        raise ValueError(f"No image found with ID {image_id}")
    
    json_data = rows[0][0]
    
    # Extract annotations
    category_map = {c["id"]: c.get("name", "") for c in json_data.get("categories", [])}
    annotations = [
        (a["id"], category_map.get(a["category_id"], ""), a.get("bbox", [0, 0, 0, 0]))
        for a in json_data.get("annotations", [])
    ]
    
    if not annotations:
        raise ValueError("No annotations found")
    
    # Lookup gardiner codes
    codes = set(a[1] for a in annotations)
    gardiner_map = dict(run_select(
        f"SELECT code, id FROM T_GARDINER_CODES WHERE code IN ({','.join(['%s']*len(codes))})",
        tuple(codes)
    ))
    
    # Insert
    conn = connect()
    try:
        with conn.cursor() as cur:
            execute_batch(cur, 
                "INSERT INTO T_GLYPHES_RAW (id_original, id_image, id_gardiner, bbox_x, bbox_y, bbox_height, bbox_width) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                [(aid, image_id, gardiner_map.get(gc), b[0], b[1], b[3], b[2]) for aid, gc, b in annotations]
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    
    return len(annotations)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m src.process_image <image_id>")
        sys.exit(1)
    
    try:
        count = process_image(int(sys.argv[1]))
        print(f"Image {sys.argv[1]}: {count or 'already processed'}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
