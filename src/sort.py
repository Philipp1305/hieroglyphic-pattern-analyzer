from typing import Any, Dict, List, Tuple

from src.database.tools import delete, insert, select

X_IDX = 3
Y_IDX = 4


def run_sort(
    image_id: int,
    tolerance: float = 100,
    reading_direction: str = "ltr",
    insert_to_db: bool = False,
):
    rows = select(
        """
        SELECT id, id_image, id_gardiner, bbox_x, bbox_y, bbox_width, bbox_height
        FROM T_GLYPHES_RAW
        WHERE id_image = %s
        """,
        (image_id,),
    )

    if not rows:
        return 0, {}

    sorted_rows, column_stats = sort(rows, tolerance, reading_direction)

    if insert_to_db and sorted_rows:
        glyph_ids = [row[0] for row in sorted_rows]
        check_entries = select(
            """
            SELECT 1
            FROM T_GLYPHES_SORTED
            WHERE id_glyph = ANY(%s)
            """,
            (glyph_ids,),
        )

        if check_entries:
            delete(
                """
                DELETE FROM T_GLYPHES_SORTED
                WHERE id_glyph = ANY(%s)
                """,
                (glyph_ids,),
            )

        insert(
            """
            INSERT INTO T_GLYPHES_SORTED (id_glyph, v_column, v_row)
            VALUES (%s, %s, %s)
            """,
            sorted_rows,
            many=True,
        )

    return sorted_rows


def sort(
    rows: List[Tuple[Any, ...]],
    tolerance: float,
    reading_direction: str,
) -> Tuple[List[Tuple[int, int, int]], Dict[int, int]]:
    items = [
        (r[0], r[1], r[2], r[3] + r[5] / 2, r[4] + r[6] / 2, r[5], r[6]) for r in rows
    ]
    x_idx, y_idx = X_IDX, Y_IDX

    items = sorted(items, key=lambda r: (r[x_idx], r[y_idx]))

    columns: List[List[Tuple[Any, ...]]] = []
    i = 0
    n = len(items)

    while i < n:
        x0 = items[i][x_idx]
        current_col: List[Tuple[Any, ...]] = []
        while i < n and items[i][x_idx] <= x0 + tolerance:
            current_col.append(items[i])
            i += 1

        current_col.sort(key=lambda r: r[y_idx])
        columns.append(current_col)

    data: List[Tuple[int, int, int]] = []
    column_stats: Dict[int, int] = {}
    for c_idx, col in enumerate(columns):
        column_stats[c_idx] = len(col)
        for r_idx, r in enumerate(col):
            data.append((r[0], c_idx, r_idx))

    if reading_direction.lower() == "rtl" and data:
        max_col = len(columns) - 1
        data = [(gid, max_col - col_idx, row_idx) for gid, col_idx, row_idx in data]
        column_stats = {max_col - idx: count for idx, count in column_stats.items()}

    return data, column_stats


if __name__ == "__main__":
    import sys

    preview = False
    args: List[str] = []

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--preview":
            preview = True
            i += 1
        else:
            args.append(arg)
            i += 1

    if len(args) < 1:
        print("Usage: python -m src.sort <image_id> [tolerance] [--preview]")
        print("Examples:")
        print("  python -m src.sort 2")
        print("  python -m src.sort 2 --preview")
        print("  python -m src.sort 2 150")
        sys.exit(1)

    image_id = int(args[0])
    tolerance = float(args[1]) if len(args) > 1 else 100.0

    rows = select("SELECT reading_direction FROM T_IMAGES WHERE id = %s", (image_id,))
    reading_dir = "rtl" if (rows and rows[0][0] == 1) else "ltr"

    count, col_stats = run_sort(image_id, tolerance, reading_dir, preview)

    if preview:
        print(f"\nPreview mode (center of gravity, tolerance={tolerance})")
        print(f"Total glyphs: {count}")
        print(f"Columns: {len(col_stats)}")
        print("\nColumn distribution:")
        for col in sorted(col_stats):
            print(f"  Column {col}: {col_stats[col]} glyphs")
    else:
        print(
            f"Sorted {count} glyphs for image {image_id} using center of gravity method"
        )
