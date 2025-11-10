from typing import Any, Sequence
from database.connect import connect

def run_update(query: str, params: Sequence[Any] | None = None) -> int:
    """
    Execute an UPDATE statement and return the number of affected rows.

    Parameters
    ----------
    query:
        SQL UPDATE statement. Use placeholders (%s) for parameters.
    params:
        Optional values that will be bound to the placeholders in `query`.
    """
    if not query.strip().lower().startswith("update"):
        raise ValueError("Only UPDATE statements are allowed.")

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
