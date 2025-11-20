from typing import Any, Sequence
from src.database.connect import connect

def run_select(query: str, params: Sequence[Any] | None = None) -> list[tuple[Any, ...]]:
    """
    Execute a SELECT statement and return all rows.

    Parameters
    ----------
    query:
        SQL SELECT statement. Use placeholders (%s) for parameters.
    params:
        Optional values that will be bound to the placeholders in `query`.
    """
    if not query.strip().lower().startswith("select"):
        raise ValueError("Only SELECT statements are allowed.")

    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
    finally:
        conn.close()

    return rows
