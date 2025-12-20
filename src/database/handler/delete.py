from typing import Any, Sequence
from src.database.connect import connect


def run_delete(query: str, params: Sequence[Any] | None = None) -> int:
    """
    Execute a DELETE statement and return the number of affected rows.

    Parameters
    ----------
    query:
        SQL DELETE statement. Use placeholders (%s) for parameters.
    params:
        Optional values that will be bound to the placeholders in `query`.
    """
    if not query.strip().lower().startswith("delete"):
        raise ValueError("Only DELETE statements are allowed.")

    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            affected = cur.rowcount

        conn.commit()
        return affected

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
