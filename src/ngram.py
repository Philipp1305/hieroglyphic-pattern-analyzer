from __future__ import annotations

from collections import Counter
from typing import Sequence

from src.database.tools import insert, select


def fetch_sorted_gardiner_ids(image_id: int) -> list[tuple[int, int]]:
    rows = select(
        """
        SELECT gs.v_column, gs.v_row, gr.id_gardiner, gr.id
        FROM T_GLYPHES_SORTED AS gs
        JOIN T_GLYPHES_RAW AS gr ON gr.id = gs.id_glyph
        WHERE gr.id_image = %s
        ORDER BY gs.v_column, gs.v_row
        """,
        (image_id,),
    )

    sequence: list[tuple[int, int]] = []
    for _col, _row, gardiner_id, glyph_id in rows:
        if gardiner_id is None:
            continue
        sequence.append((int(gardiner_id), int(glyph_id)))

    return sequence


def find_ngram_occurrences(
    gardiner_ids: Sequence[int],
    *,
    min_length: int,
    max_length: int,
) -> dict[tuple[int, ...], list[int]]:
    occurrences: dict[tuple[int, ...], list[int]] = {}
    total = len(gardiner_ids)
    if total < min_length:
        return occurrences

    max_n = min(max_length, total)

    for n in range(min_length, max_n + 1):
        limit = total - n + 1
        for start in range(limit):
            ngram = tuple(gardiner_ids[start : start + n])
            occurrences.setdefault(ngram, []).append(start)

    return occurrences


def filter_closed_patterns(
    occurrences: dict[tuple[int, ...], list[int]],
) -> dict[tuple[int, ...], list[int]]:
    filtered: dict[tuple[int, ...], list[int]] = {}

    patterns_by_count: dict[
        int, dict[int, list[tuple[tuple[int, ...], list[int]]]]
    ] = {}
    for ngram, starts in occurrences.items():
        if len(starts) <= 1:
            continue
        patterns_by_count.setdefault(len(starts), {}).setdefault(len(ngram), []).append(
            (ngram, starts)
        )

    def intervals_fully_covered(
        short_starts: list[int],
        short_len: int,
        long_starts: list[int],
        long_len: int,
    ) -> bool:
        # Check if every short interval is contained in some longer interval
        idx = 0
        for start in short_starts:
            short_end = start + short_len
            while idx < len(long_starts) and long_starts[idx] + long_len < short_end:
                idx += 1
            if idx == len(long_starts) or long_starts[idx] > start:
                return False
        return True

    for count, patterns_by_length in patterns_by_count.items():
        lengths_desc = sorted(patterns_by_length, reverse=True)
        longer_patterns: list[tuple[int, list[int]]] = []

        for length in lengths_desc:
            for ngram, starts in patterns_by_length[length]:
                overlapped = any(
                    intervals_fully_covered(starts, length, long_starts, long_len)
                    for long_len, long_starts in longer_patterns
                )

                if not overlapped:
                    filtered[ngram] = starts

            # Make current length patterns available as supersets for shorter n-grams
            longer_patterns.extend(
                (length, starts) for _, starts in patterns_by_length[length]
            )

    return filtered


def persist_patterns(
    image_id: int,
    occurrences: dict[tuple[int, ...], list[int]],
    glyph_ids: Sequence[int],
) -> None:
    for ngram, starts in occurrences.items():
        if len(starts) <= 1:
            continue

        pattern_id = insert(
            """
            INSERT INTO T_NGRAM_PATTERN (id_image, gardiner_ids, length, count)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (image_id, list(ngram), len(ngram), len(starts)),
        )

        insert(
            """
            INSERT INTO T_NGRAM_OCCURENCES (id_pattern, glyph_ids)
            VALUES (%s, %s)
            """,
            [
                (pattern_id, list(glyph_ids[start : start + len(ngram)]))
                for start in starts
            ],
            many=True,
        )
    return None


def ngram_counts_from_occurrences(
    occurrences: dict[tuple[int, ...], list[int]],
) -> Counter[tuple[int, ...]]:
    rows_to_insert = [
        (ngram, len(starts)) for ngram, starts in occurrences.items() if len(starts) > 1
    ]

    return Counter(dict(rows_to_insert))


def run_ngram(
    image_id: int,
) -> Counter[tuple[int, ...]]:
    sequence_pairs = fetch_sorted_gardiner_ids(image_id)
    if not sequence_pairs:
        return Counter()

    gardiner_ids = [gid for gid, _ in sequence_pairs]
    glyph_ids = [glyph_id for _, glyph_id in sequence_pairs]

    occurrences = find_ngram_occurrences(
        gardiner_ids,
        min_length=2,
        max_length=max(2, len(gardiner_ids) // 2),
    )

    occurrences = filter_closed_patterns(occurrences)

    if occurrences:
        persist_patterns(image_id, occurrences, glyph_ids)

    return ngram_counts_from_occurrences(occurrences)


def debug_example_sequence(sequence: list[str] | list[int]) -> Counter[tuple[int, ...]]:
    """
    Helper to inspect which n-grams would be kept for an ad-hoc sequence.
    Accepts a list of glyph IDs (ints) or symbols (str) and returns the filtered Counter.
    """
    if not sequence:
        return Counter()

    # Convert symbols to stable, order-based ints for the algorithm.
    symbol_map: dict[str, int] = {}
    normalized: list[int] = []
    for val in sequence:
        if isinstance(val, (int, float)):
            normalized.append(int(val))
        else:
            key = str(val)
            if key not in symbol_map:
                symbol_map[key] = len(symbol_map) + 1
            normalized.append(symbol_map[key])
    occurrences = find_ngram_occurrences(
        normalized,
        min_length=2,
        max_length=max(2, len(normalized) // 2),
    )
    occurrences = filter_closed_patterns(occurrences)
    return ngram_counts_from_occurrences(occurrences)


if __name__ == "__main__":
    run_ngram(1)
