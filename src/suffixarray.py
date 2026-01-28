import argparse
import sys
from pathlib import Path
from typing import Sequence

import psycopg2.extras

from src.database.connect import connect
from src.database.tools import insert, select, delete

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Runs in O(nlogn)


def fetch_sorted_gardiner_ids(image_id: int) -> list[tuple[int, int]]:
    rows = select(
        """
        SELECT gs.v_column, gs.v_row, gr.id_gardiner, gr.id
        FROM T_GLYPHES_SORTED AS gs
        LEFT JOIN T_GLYPHES_RAW AS gr ON gr.id = gs.id_glyph
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


def find_suffixarray_occurrences(
    gardiner_ids: list[int],
    *,
    min_length: int,
) -> dict[tuple[int, ...], list[int]]:
    """
    Find all repeated substrings and their start positions using suffix array.
    Similar to find_ngram_occurrences but uses suffix array approach.

    Returns dict mapping pattern -> list of start positions.
    """
    occurrences: dict[tuple[int, ...], list[int]] = {}

    if len(gardiner_ids) < min_length:
        return occurrences

    suffixes = build_suffixes(gardiner_ids)

    # For each pair of consecutive suffixes, find LCP and track positions
    for i in range(len(suffixes) - 1):
        s1, pos1 = suffixes[i]
        s2, pos2 = suffixes[i + 1]
        lcp_len = lcp_length(s1, s2)

        # Extract all prefixes of the LCP that meet min_length
        for prefix_len in range(min_length, lcp_len + 1):
            pattern = tuple(s1[:prefix_len])

            # Add both positions
            if pattern not in occurrences:
                occurrences[pattern] = []
            if pos1 not in occurrences[pattern]:
                occurrences[pattern].append(pos1)
            if pos2 not in occurrences[pattern]:
                occurrences[pattern].append(pos2)

    # Sort positions for each pattern
    for pattern in occurrences:
        occurrences[pattern].sort()

    return occurrences


def build_suffixes(seq: list[int]) -> list[tuple[list[int], int]]:
    suffixes = [
        (seq[i:], i) for i in range(len(seq))
    ]  # Create suffixes with their starting indices
    suffixes.sort()  # Sort suffixes lexicographically
    return suffixes


def lcp_length(
    a: list[int], b: list[int]
) -> int:  # Compute length of longest common prefix
    i = 0
    while i < min(len(a), len(b)) and a[i] == b[i]:
        i += 1
    return i


def find_lcps(seq: list[int], min_length: int) -> list[tuple[int, tuple[int, ...]]]:
    suffixes = build_suffixes(seq)
    lcps: list[tuple[int, tuple[int, ...]]] = []

    for i in range(len(suffixes) - 1):
        s1, _ = suffixes[i]
        s2, _ = suffixes[i + 1]
        length = lcp_length(s1, s2)  # Get LCP length between suffixes

        if (
            length >= min_length and length > 0
        ):  # Only consider LCPs above min_length. min_length >= 1
            prefix = tuple(s1[:length])
            lcps.append((length, prefix))

    unique: dict[
        tuple[int, ...], int
    ] = {}  # Keep only the longest LCP for each unique prefix
    for length, prefix in lcps:
        if (
            prefix not in unique or length > unique[prefix]
        ):  # Update if longer LCP found
            unique[prefix] = length

    sorted_lcps = sorted(
        unique.items(), key=lambda item: (-item[1], item[0])
    )  # Sort by length desc, then prefix asc
    return [(length, prefix) for prefix, length in sorted_lcps]


def search_pattern(suffixes: list[tuple[list[int], int]], pattern: list[int]) -> int:
    """
    Search for a pattern in the sorted suffix array using binary search.
    Returns the count of occurrences.
    """
    if not pattern:
        return 0

    def matches_prefix(suffix: list[int], pat: list[int]) -> bool:
        if len(suffix) < len(pat):
            return False
        return suffix[: len(pat)] == pat

    def compare(suffix: list[int], pat: list[int]) -> int:
        # Returns: -1 if suffix < pattern, 0 if matches, 1 if suffix > pattern
        min_len = min(len(suffix), len(pat))
        for i in range(min_len):
            if suffix[i] < pat[i]:
                return -1
            elif suffix[i] > pat[i]:
                return 1
        # All compared elements match
        if len(suffix) < len(pat):
            return -1  # suffix is shorter, so it comes before
        return 0  # matches or suffix is longer (which means match for prefix)

    # Binary search for first occurrence
    left, right = 0, len(suffixes)
    first = -1
    while left < right:
        mid = (left + right) // 2
        cmp = compare(suffixes[mid][0], pattern)
        if cmp < 0:
            left = mid + 1
        else:
            if matches_prefix(suffixes[mid][0], pattern):
                first = mid
            right = mid

    if first == -1:
        return 0

    # Binary search for last occurrence
    left, right = first, len(suffixes)
    last = first
    while left < right:
        mid = (left + right) // 2
        if matches_prefix(suffixes[mid][0], pattern):
            last = mid
            left = mid + 1
        else:
            right = mid

    return last - first + 1


def find_all_repeated_substrings(
    seq: list[int], min_length: int = 1
) -> list[tuple[int, tuple[int, ...], int]]:
    """
    Find ALL repeated substrings (not just LCPs).
    Returns list of (length, substring, occurrence_count) tuples sorted by occurrence desc, length desc.
    """
    suffixes = build_suffixes(seq)

    # Collect all repeated prefixes between consecutive suffixes
    all_repeated: dict[tuple[int, ...], int] = {}

    for i in range(len(suffixes) - 1):
        s1, _ = suffixes[i]
        s2, _ = suffixes[i + 1]
        length = lcp_length(s1, s2)

        # For this LCP, collect ALL possible prefixes (length min_length, ..., lcp_length)
        for prefix_len in range(min_length, length + 1):
            prefix = tuple(s1[:prefix_len])
            all_repeated[prefix] = all_repeated.get(prefix, 1) + 1

    # Convert to list and sort by occurrence count (desc), then by length (desc)
    result = [(len(prefix), prefix, count) for prefix, count in all_repeated.items()]
    result.sort(key=lambda x: (-x[2], -x[0]))

    return result


def persist_suffixarray_patterns(
    image_id: int,
    occurrences: dict[tuple[int, ...], list[int]],
    glyph_ids: Sequence[int],
) -> None:
    
    patterns = list(occurrences.items())
    
    if not patterns:
        return

    conn = connect()
    cur = conn.cursor()
    try:
        pattern_rows = [
            (image_id, list(pattern), len(pattern), len(starts))
            for pattern, starts in patterns
        ]

        # Insert patterns
        psycopg2.extras.execute_values(
            cur,
            """
            INSERT INTO T_SUFFIXARRAY_PATTERNS (id_image, gardiner_ids, sequence_length, sequence_count)
            VALUES %s
            """,
            pattern_rows,
            page_size=100,
        )
        conn.commit()

        # Fetch all pattern IDs for this image in the same order
        cur.execute(
            """
            SELECT id, gardiner_ids FROM T_SUFFIXARRAY_PATTERNS 
            WHERE id_image = %s 
            ORDER BY id DESC 
            LIMIT %s
            """,
            (image_id, len(patterns)),
        )
        pattern_data = cur.fetchall()
        
        # Build a map from gardiner_ids to pattern_id
        gardiner_to_id = {tuple(row[1]): row[0] for row in pattern_data}
        
        occurrence_rows: list[tuple[int, list[int]]] = []
        for (pattern, starts), in zip(patterns):
            pattern_tuple = tuple(pattern)
            pattern_id = gardiner_to_id.get(pattern_tuple)
            
            if pattern_id is None:
                print(f"Warning: Could not find pattern {pattern}")
                continue
                
            pat_len = len(pattern)
            for start in starts:
                occurrence_rows.append(
                    (pattern_id, list(glyph_ids[start : start + pat_len]))
                )

        if occurrence_rows:
            psycopg2.extras.execute_values(
                cur,
                """
                INSERT INTO T_SUFFIXARRAY_OCCURENCES (id_pattern, glyph_ids)
                VALUES %s
                """,
                occurrence_rows,
                page_size=500,
            )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        try:
            cur.close()
        except Exception:
            pass
        conn.close()

    return None


def store_occurrence_bboxes(image_id: int) -> None:
    """
    Compute and persist bounding boxes for each suffix array occurrence, grouped by column.
    Multiple boxes can be stored for a single occurrence when it spans several columns.
    """
    occ_rows = select(
        """
        SELECT occ.id, occ.glyph_ids
        FROM T_SUFFIXARRAY_OCCURENCES AS occ
        LEFT JOIN T_SUFFIXARRAY_PATTERNS AS pat ON pat.id = occ.id_pattern
        WHERE pat.id_image = %s
        """,
        (image_id,),
    )
    if not occ_rows:
        return

    # Use a left join so we still get geometry even if a glyph is missing from the sorted table.
    glyph_rows = select(
        """
        SELECT gr.id, gr.bbox_x, gr.bbox_y, gr.bbox_width, gr.bbox_height, gs.v_column
        FROM T_GLYPHES_RAW AS gr
        LEFT JOIN T_GLYPHES_SORTED AS gs ON gs.id_glyph = gr.id
        WHERE gr.id_image = %s
        """,
        (image_id,),
    )
    if not glyph_rows:
        return

    glyph_map: dict[int, tuple[float, float, float, float, int]] = {}
    for gid, x, y, width, height, col in glyph_rows:
        if any(val is None for val in (gid, x, y, width, height)):
            continue
        col_idx = int(col) if col is not None else 0
        glyph_map[int(gid)] = (
            float(x),
            float(y),
            float(width),
            float(height),
            col_idx,
        )

    bbox_rows: list[tuple[int, float, float, float, float]] = []

    for occ_id, glyph_ids in occ_rows:
        if not glyph_ids:
            continue

        glyphs_by_column: dict[int, list[tuple[float, float, float, float]]] = {}
        for glyph_id in glyph_ids:
            glyph_data = glyph_map.get(int(glyph_id))
            if glyph_data is None:
                # Skip missing glyphs entirely; without geometry we cannot build a bbox.
                continue
            x, y, width, height, col = glyph_data
            glyphs_by_column.setdefault(col, []).append((x, y, width, height))

        for col in sorted(glyphs_by_column):
            col_glyphs = glyphs_by_column[col]
            min_x = min(g[0] for g in col_glyphs)
            min_y = min(g[1] for g in col_glyphs)
            max_x = max(g[0] + g[2] for g in col_glyphs)
            max_y = max(g[1] + g[3] for g in col_glyphs)
            bbox_rows.append((occ_id, min_x, min_y, max_y - min_y, max_x - min_x))

    if bbox_rows:
        insert(
            """
            INSERT INTO T_SUFFIXARRAY_OCCURENCES_BBOXES (id_occ, bbox_x, bbox_y, bbox_height, bbox_width)
            VALUES (%s, %s, %s, %s, %s)
            """,
            bbox_rows,
            many=True,
        )


def run_suffixarray(
    image_id: int,
    *,
    min_length: int = 2,
) -> dict[tuple[int, ...], list[int]]:
    """
    Run suffix array analysis on an image, similar to run_ngram workflow.
    Returns occurrences dict for further processing.
    """
    sequence_pairs = fetch_sorted_gardiner_ids(image_id)
    if not sequence_pairs:
        return {}

    gardiner_ids = [gid for gid, _ in sequence_pairs]
    glyph_ids = [glyph_id for _, glyph_id in sequence_pairs]

    occurrences = find_suffixarray_occurrences(
        gardiner_ids,
        min_length=min_length,
    )

    if occurrences:
        # Delete existing patterns for this image to avoid duplicates
        delete(
            """
            DELETE FROM T_SUFFIXARRAY_OCCURENCES
            WHERE id_pattern IN (
                SELECT id FROM T_SUFFIXARRAY_PATTERNS WHERE id_image = %s
            )
            """,
            (image_id,),
        )
        delete(
            """
            DELETE FROM T_SUFFIXARRAY_PATTERNS WHERE id_image = %s
            """,
            (image_id,),
        )
        delete(
            """
            DELETE FROM T_SUFFIXARRAY_OCCURENCES_BBOXES
            WHERE id_occ IN (
                SELECT occ.id
                FROM T_SUFFIXARRAY_OCCURENCES AS occ
                LEFT JOIN T_SUFFIXARRAY_PATTERNS AS pat ON pat.id = occ.id_pattern
                WHERE pat.id_image = %s
            )
            """,
            (image_id,),
        )

        persist_suffixarray_patterns(image_id, occurrences, glyph_ids)
        store_occurrence_bboxes(image_id)

    return occurrences


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run suffix array analysis on an image"
    )
    parser.add_argument("image_id", type=int, help="Image ID to analyze")
    parser.add_argument(
        "--min-length", type=int, default=2, help="Minimum pattern length"
    )
    parser.add_argument(
        "--search",
        type=str,
        help="Search for a pattern (comma-separated gardiner IDs, e.g. '10,44,5')",
    )

    args = parser.parse_args()

    if args.search:
        # Search mode
        print(f"Searching for pattern '{args.search}' in image {args.image_id}...")

        sequence_pairs = fetch_sorted_gardiner_ids(args.image_id)
        if not sequence_pairs:
            print("No sequence found for this image")
        else:
            gardiner_ids = [gid for gid, _ in sequence_pairs]
            suffixes = build_suffixes(gardiner_ids)

            pattern = [int(x.strip()) for x in args.search.split(",")]
            count = search_pattern(suffixes, pattern)

            print(f"Pattern {pattern} found {count} times")
    else:
        # Analysis mode
        print(f"Running suffix array analysis on image {args.image_id}...")
        occurrences = run_suffixarray(args.image_id, min_length=args.min_length)

        print(f"Found {len(occurrences)} unique patterns")
        print(
            f"Total occurrences: {sum(len(starts) for starts in occurrences.values())}"
        )


# Für String-Pattern-Suche:
# .archeo/bin/python src/suffixarray.py 1 --search "10,44,5"

# Für Analyse:
# .archeo/bin/python src/suffixarray.py 1 --min-length 2
