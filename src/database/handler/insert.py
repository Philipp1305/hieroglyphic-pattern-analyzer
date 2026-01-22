from typing import Any, Iterable, Sequence, cast

from psycopg2.extras import execute_batch

from src.database.connect import connect


def run_insert(
    query: str,
    params: Sequence[Any] | Iterable[Sequence[Any]] | None = None,
    *,
    many: bool = False,
    page_size: int = 100,
) -> Any:
    """
    Execute an INSERT statement and return the inserted id if available,
    otherwise the number of affected rows. When `many` is True the query
    is executed as a batch insert and the number of inserted rows is returned.

    Parameters
    ----------
    query:
        SQL INSERT statement. Use placeholders (%s) for parameters.
    params:
        Optional values that will be bound to the placeholders in `query`.
    many:
        When True, execute the statement with `execute_batch` for the provided rows.
    page_size:
        Batch size for psycopg2 `execute_batch`.
    """
    if not query.strip().lower().startswith("insert"):
        raise ValueError("Only INSERT statements are allowed.")

    rows: list[Sequence[Any]] | None = None
    single_params: Sequence[Any] | None = None

    if many:
        rows_iter = cast(Iterable[Sequence[Any]], params if params is not None else [])
        rows = list(rows_iter)
        if not rows:
            return 0
        if any(
            not isinstance(row, Sequence) or isinstance(row, (str, bytes, bytearray))
            for row in rows
        ):
            raise TypeError("Batch parameters must be sequences of values.")
    else:
        single_params = cast(Sequence[Any] | None, params)

    conn = connect()
    try:
        with conn.cursor() as cur:
            if many:
                assert rows is not None
                execute_batch(cur, query, rows, page_size=page_size)
                result: Any = len(rows)
            else:
                cur.execute(query, single_params)

                if cur.description:
                    row = cur.fetchone()
                    if row is None:
                        raise RuntimeError("INSERT did not return a row.")
                    result = row[0] if len(row) == 1 else row
                else:
                    result = cur.rowcount

        conn.commit()
        return result

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
