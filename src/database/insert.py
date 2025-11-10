from typing import Any, Sequence
from database.connect import connect

def run_insert(query: str, params: Sequence[Any] | None = None) -> int:
    """
    Execute an INSERT statement and return the number of affected rows.

    Parameters
    ----------
    query:
        SQL INSERT statement. Use placeholders (%s) for parameters.
    params:
        Optional values that will be bound to the placeholders in `query`.
    """
    if not query.strip().lower().startswith("insert"):
        raise ValueError("Only INSERT statements are allowed.")

    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            affected = cur.rowcount
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return affected
