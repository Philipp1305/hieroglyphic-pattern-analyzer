from database.select import run_select
from typing import List, Tuple, Any
import pandas as pd

X_IDX = 3
Y_IDX = 4

def sort_hieroglyphes(
    rows: List[Tuple[Any, ...]],
    tolerance: float,
    x_index: int = X_IDX,
    y_index: int = Y_IDX,
    reading_direction: str = "ltr",
):
    if not rows:
        return pd.DataFrame()

    items = sorted(rows, key=lambda r: (r[x_index], r[y_index]))

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

    records = []
    for c_idx, col in enumerate(columns):
        for r_idx, r in enumerate(col):
            rec = {
                "id": r[0],
                "id_image": r[1],
                "gardiner_code": r[2],
                "x": r[x_index],
                "y": r[y_index],
                "width": r[x_index + 2],
                "height": r[x_index + 3],
                "col_index": c_idx,
                "row_index": r_idx,
            }
            records.append(rec)

    df = pd.DataFrame(records)
    if not df.empty and reading_direction.lower() == "rtl":
        max_col = int(df["col_index"].max())
        df["col_index"] = max_col - df["col_index"]
        df = df.sort_values(by=["col_index", "row_index"])
    return df

if __name__ == "__main__":
    id_image    = 1
    tolerance   = 100
    sql_query   = f"SELECT * FROM T_HIEROGLYPHES WHERE id_image = {id_image}"
    rows        = run_select(sql_query)

    df = sort_hieroglyphes(rows, tolerance, reading_direction='rtl')

    df.to_csv('sorted_glyphes.csv', sep=',', encoding='utf-8', index=False)
