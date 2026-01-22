from typing import Any, Iterable, Sequence

from src.database.handler.select import run_select
from src.database.handler.insert import run_insert
from src.database.handler.delete import run_delete
from src.database.handler.update import run_update


def insert(
    query: str,
    params: Sequence[Any] | Iterable[Sequence[Any]] | None = None,
    *,
    many: bool = False,
    page_size: int = 100,
) -> Any:
    return run_insert(query, params, many=many, page_size=page_size)


def delete(query: str, params: Sequence[Any] | None = None) -> int:
    return run_delete(query, params)


def update(query: str, params: Sequence[Any] | None = None) -> int:
    return run_update(query, params)


def select(query: str, params: Sequence[Any] | None = None) -> list[tuple[Any, ...]]:
    return run_select(query, params)
