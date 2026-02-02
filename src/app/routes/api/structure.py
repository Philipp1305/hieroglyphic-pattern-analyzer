from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from math import ceil, log, sqrt
from statistics import median

from flask import jsonify

from src.database.tools import select
from . import bp
from .patterns import (
    _gardiner_map_for_ids,
    _image_exists,
    _normalize_gardiner_code,
    _normalize_unicode,
    _unicode_to_symbol,
)

BOS = -1
EOS = -2

@dataclass(frozen=True)
class PatternRow:
    id_pattern: int
    seq: tuple[int, ...]   # gardiner ids
    length: int
    count: int

def _entropy(dist: Counter[int]) -> float:
    total = sum(dist.values())
    if total <= 0:
        return 0.0
    h = 0.0
    for c in dist.values():
        p = c / total
        h -= p * log(p)
    return h

@bp.get("/images/<int:image_id>/structure/stable_sequences")
def get_stable_sequences(image_id: int):
    if not _image_exists(image_id):
        return {"error": "not found"}, 404

    top_patterns = load_top_patterns(select, image_id, limit=10)
    payload = (
        _decorate_sequences(
            image_id,
            [
                {
                    "seq": p.seq,
                    "length": p.length,
                    "count": p.count,
                }
                for p in top_patterns
            ],
        )
        if top_patterns
        else {"image_id": image_id, "items": [], "lengths": []}
    )

    response = jsonify(payload)
    response.headers["Cache-Control"] = "no-store"
    return response


@bp.get("/images/<int:image_id>/structure/stable_stems")
def get_stable_stems(image_id: int):
    if not _image_exists(image_id):
        return {"error": "not found"}, 404

    n = count_glyphs(select, image_id)
    min_count = max(3, ceil(sqrt(n) / 6)) if n else 3

    stable_stems = compute_stable_stems_from_linear(
        select, image_id, max_len=6, min_count=min_count
    )
    filtered = _filter_stable_stems(stable_stems, n, min_count)
    payload = _decorate_sequences(image_id, filtered)
    response = jsonify(payload)
    response.headers["Cache-Control"] = "no-store"
    return response


@bp.get("/images/<int:image_id>/structure/prefixes")
def get_prefixes(image_id: int):
    if not _image_exists(image_id):
        return {"error": "not found"}, 404

    n = count_glyphs(select, image_id)
    prefixes = compute_most_prefixes(select, image_id, max_len=5)
    prefixes = _attach_share(prefixes)
    filtered = _filter_prefixes(prefixes, n)
    payload = _decorate_sequences(image_id, filtered)
    response = jsonify(payload)

    response.headers["Cache-Control"] = "no-store"
    return response


@bp.get("/images/<int:image_id>/structure/suffixes")
def get_suffixes(image_id: int):
    if not _image_exists(image_id):
        return {"error": "not found"}, 404

    n = count_glyphs(select, image_id)
    suffixes = compute_most_suffixes(select, image_id, max_len=5)
    suffixes = _attach_share(suffixes)
    filtered = _filter_suffixes(suffixes, n)
    payload = _decorate_sequences(image_id, filtered)
    response = jsonify(payload)
    response.headers["Cache-Control"] = "no-store"
    return response


def load_linear_tokens(select, image_id: int) -> list[tuple[int, int]]:
    """Return glyphs in reading order as (glyph_id, gardiner_id)."""
    rows = select(
        """
        SELECT gs.v_column, gs.v_row, gr.id, gr.id_gardiner
        FROM t_glyphes_sorted AS gs
        JOIN t_glyphes_raw AS gr ON gr.id = gs.id_glyph
        WHERE gr.id_image = %s
        ORDER BY gs.v_column, gs.v_row
        """,
        (image_id,),
    )

    linear: list[tuple[int, int]] = []
    for _col, _row, glyph_id, gardiner_id in rows:
        if glyph_id is None or gardiner_id is None:
            continue
        linear.append((int(glyph_id), int(gardiner_id)))
    return linear


def count_glyphs(select, image_id: int) -> int:
    rows = select(
        "SELECT COUNT(*) FROM t_glyphes_raw WHERE id_image = %s",
        (image_id,),
    )
    if not rows:
        return 0
    try:
        return int(rows[0][0])
    except Exception:
        return 0

def load_suffixarray_patterns(select, image_id: int) -> list[PatternRow]:
    rows = select(
        """
        SELECT id, gardiner_ids, sequence_length, sequence_count
        FROM t_suffixarray_patterns
        WHERE id_image = %s
        """,
        (image_id,),
    )
    out: list[PatternRow] = []
    for pid, gard_arr, L, cnt in rows:
        if not gard_arr:
            continue
        # Postgres int[] kommt meistens als list[int]
        seq = tuple(int(x) for x in gard_arr)
        seq_len = len(seq)
        out.append(PatternRow(int(pid), seq, seq_len, int(cnt)))
    return out

def load_top_patterns(select, image_id: int, limit: int = 10) -> list[PatternRow]:
    rows = select(
        """
        SELECT id, gardiner_ids, sequence_length, sequence_count
        FROM t_suffixarray_patterns
        WHERE id_image = %s
        ORDER BY sequence_count DESC, sequence_length DESC, id ASC
        LIMIT %s
        """,
        (image_id, limit),
    )
    patterns: list[PatternRow] = []
    for pid, gard_arr, seq_len, cnt in rows:
        if not gard_arr:
            continue
        seq = tuple(int(x) for x in gard_arr)
        length = int(seq_len) if seq_len is not None else len(seq)
        patterns.append(PatternRow(int(pid), seq, length, int(cnt)))
    return patterns

def load_suffixarray_occurrences(select, image_id: int) -> list[tuple[int, tuple[int, ...]]]:
    """
    Returns list of (id_pattern, glyph_ids_tuple)
    """
    rows = select(
        """
        SELECT o.id_pattern, o.glyph_ids
        FROM t_suffixarray_occurences o
        JOIN t_suffixarray_patterns p ON p.id = o.id_pattern
        WHERE p.id_image = %s
        """,
        (image_id,),
    )
    out = []
    for pid, glyph_arr in rows:
        if not glyph_arr:
            continue
        out.append((int(pid), tuple(int(x) for x in glyph_arr)))
    return out

def build_glyph_index(linear: list[tuple[int, int]]) -> dict[int, int]:
    """glyph_id -> position index in linear order"""
    return {glyph_id: i for i, (glyph_id, _gard) in enumerate(linear)}

def occurrence_contexts(
    linear: list[tuple[int, int]],
    occ_glyph_ids: tuple[int, ...],
    glyph_pos: dict[int, int],
) -> tuple[int, int] | None:
    """
    Returns (left_gardiner_id, right_gardiner_id) for this occurrence.
    Uses glyph positions; skips occurrences that are not contiguous.
    """
    if not occ_glyph_ids:
        return None

    try:
        positions = [glyph_pos[g] for g in occ_glyph_ids]
    except KeyError:
        return None

    # check contiguity
    positions_sorted = sorted(positions)
    if positions_sorted[-1] - positions_sorted[0] != len(positions_sorted) - 1:
        return None  # not contiguous in linear order -> skip

    start = positions_sorted[0]
    end = positions_sorted[-1]

    left_g = BOS if start == 0 else linear[start - 1][1]   # neighbor gardiner id
    right_g = EOS if end == len(linear) - 1 else linear[end + 1][1]
    return int(left_g), int(right_g)

def compute_stable_sequences_from_suffixarray(
    select,
    image_id: int,
    min_occ: int = 2,
) -> list[dict]:
    patterns = load_suffixarray_patterns(select, image_id)
    occs = load_suffixarray_occurrences(select, image_id)

    linear = load_linear_tokens(select, image_id)
    glyph_pos = build_glyph_index(linear)

    # pattern_id -> context distributions
    left_dist: dict[int, Counter[int]] = defaultdict(Counter)
    right_dist: dict[int, Counter[int]] = defaultdict(Counter)
    occ_count: Counter[int] = Counter()

    for pid, glyph_ids in occs:
        ctx = occurrence_contexts(linear, glyph_ids, glyph_pos)
        if ctx is None:
            continue
        l, r = ctx
        left_dist[pid][l] += 1
        right_dist[pid][r] += 1
        occ_count[pid] += 1

    # id -> PatternRow
    by_id = {p.id_pattern: p for p in patterns}

    out = []
    for pid, c in occ_count.items():
        if c < min_occ or pid not in by_id:
            continue

        p = by_id[pid]
        left_types = len(left_dist[pid])
        right_types = len(right_dist[pid])
        productivity = left_types + right_types

        boundary_strength = (_entropy(left_dist[pid]) + _entropy(right_dist[pid])) / 2.0
        stability_score = log(1 + c) * (1 + productivity) * (1 + boundary_strength)

        out.append({
            "id_pattern": pid,
            "seq": p.seq,
            "length": p.length,
            "count": c,  # occurrences gezählt (soll nahe an sequence_count sein)
            "productivity": productivity,
            "boundary_strength": boundary_strength,
            "stability_score": stability_score,
            "left_types": left_types,
            "right_types": right_types,
        })

    out.sort(key=lambda d: d["stability_score"], reverse=True)
    return out

def compute_stable_stems_from_linear(
    select,
    image_id: int,
    max_len: int = 6,
    min_count: int = 3,
) -> list[dict]:
    linear = load_linear_tokens(select, image_id)
    tokens = [gard for (_glyph, gard) in linear]
    n = len(tokens)

    freq: Counter[tuple[int, ...]] = Counter()
    left_dist: dict[tuple[int, ...], Counter[int]] = defaultdict(Counter)
    right_dist: dict[tuple[int, ...], Counter[int]] = defaultdict(Counter)

    for i in range(n):
        left = BOS if i == 0 else tokens[i - 1]
        for L in range(1, max_len + 1):
            j = i + L
            if j > n:
                break
            seq = tuple(tokens[i:j])
            right = EOS if j == n else tokens[j]

            freq[seq] += 1
            left_dist[seq][left] += 1
            right_dist[seq][right] += 1

    out = []
    for seq, c in freq.items():
        if c < min_count:
            continue
        left_types = len(left_dist[seq])
        right_types = len(right_dist[seq])
        productivity = left_types + right_types
        boundary_strength = (_entropy(left_dist[seq]) + _entropy(right_dist[seq])) / 2.0
        stability_score = log(1 + c) * (1 + productivity) * (1 + boundary_strength)

        out.append({
            "seq": seq,
            "length": len(seq),
            "count": c,
            "productivity": productivity,
            "boundary_strength": boundary_strength,
            "stability_score": stability_score,
            "left_types": left_types,
            "right_types": right_types,
        })

    out.sort(key=lambda d: d["stability_score"], reverse=True)
    return out

def compute_most_affixes_from_patterns(
    select,
    image_id: int,
    mode: str,          # "prefix" | "suffix"
    min_len: int = 1,
    max_len: int = 5,
) -> list[dict]:
    assert mode in ("prefix", "suffix")
    patterns = load_suffixarray_patterns(select, image_id)

    counts: Counter[tuple[int, ...]] = Counter()
    for p in patterns:
        L = len(p.seq)
        for k in range(min_len, min(max_len, L) + 1):
            aff = p.seq[:k] if mode == "prefix" else p.seq[-k:]
            counts[aff] += p.count  # gewichtet mit sequence_count

    out = [{"seq": seq, "length": len(seq), "count": cnt} for seq, cnt in counts.most_common()]
    return out

def compute_most_prefixes(select, image_id: int, max_len: int = 5) -> list[dict]:
    return compute_most_affixes_from_patterns(select, image_id, "prefix", 1, max_len)

def compute_most_suffixes(select, image_id: int, max_len: int = 5) -> list[dict]:
    return compute_most_affixes_from_patterns(select, image_id, "suffix", 1, max_len)


def _attach_share(items: list[dict]) -> list[dict]:
    total = sum(int(r.get("count", 0)) for r in items) or 1
    out: list[dict] = []
    for r in items:
        share = (float(r.get("count", 0)) / total) * 100.0
        out.append({**r, "share_percent": share})
    return out


def _filter_stable_sequences(items: list[dict], n: int, min_count: int) -> list[dict]:
    # base filters
    filtered = [
        r
        for r in items
        if r.get("count", 0) >= min_count
        and r.get("length", 0) >= 2
        and r.get("productivity", 0) >= 3
    ]
    if not filtered:
        return []

    # top 10% by stability score
    filtered.sort(key=lambda r: r.get("stability_score", 0), reverse=True)
    top_n = max(1, int(ceil(len(filtered) * 0.10)))
    filtered = filtered[:top_n]

    def bucket_limit(length: int) -> int:
        if length <= 1:
            return 0
        if length <= 3:
            return 20
        if length <= 5:
            return 10
        return 5

    counters: dict[int, int] = defaultdict(int)
    out: list[dict] = []
    for r in filtered:
        L = int(r.get("length", 0))
        limit = bucket_limit(L)
        if limit <= 0:
            continue
        if counters[L] >= limit:
            continue
        counters[L] += 1
        out.append(r)
    return out


def _filter_stable_stems(items: list[dict], n: int, min_count: int) -> list[dict]:
    base = [
        r
        for r in items
        if r.get("count", 0) >= min_count
        and 2 <= r.get("length", 0) <= 5
    ]
    if not base:
        return []

    # productivity median
    prod_values = [float(r.get("productivity", 0)) for r in base]
    prod_median = median(prod_values) if prod_values else 0
    base = [r for r in base if r.get("productivity", 0) >= prod_median]
    if not base:
        return []

    # top 10% by stability score
    base.sort(key=lambda r: r.get("stability_score", 0), reverse=True)
    top_n = max(1, int(ceil(len(base) * 0.10)))
    base = base[:top_n]

    def limit_for_length(length: int) -> int:
        if length in (2, 3):
            return 20
        if length == 4:
            return 10
        if length >= 5:
            return 5
        return 0

    counters: dict[int, int] = defaultdict(int)
    out: list[dict] = []
    for r in base:
        L = int(r.get("length", 0))
        limit = limit_for_length(L)
        if limit <= 0:
            continue
        if counters[L] >= limit:
            continue
        counters[L] += 1
        out.append(r)
    return out


def _filter_prefixes(items: list[dict], n: int) -> list[dict]:
    if not items:
        return []
    threshold = 1.0
    if n and n > 0:
        threshold = max(1.0, 100.0 / n)

    items = [r for r in items if r.get("length", 0) <= 3]
    items.sort(key=lambda r: r.get("count", 0), reverse=True)
    top = items[:15]
    share_selected = [r for r in items if r.get("share_percent", 0) >= threshold]

    # preserve order by count
    seen = set()
    out = []
    for r in top + share_selected:
        key = (tuple(r.get("seq", ())), r.get("length", 0))
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def _filter_suffixes(items: list[dict], n: int) -> list[dict]:
    if not items:
        return []
    threshold = 2.0
    if n and n > 0:
        threshold = max(2.0, 150.0 / n)

    items = [r for r in items if r.get("length", 0) <= 3]
    items.sort(key=lambda r: r.get("count", 0), reverse=True)
    top = items[:10]
    share_selected = [r for r in items if r.get("share_percent", 0) >= threshold]

    seen = set()
    out = []
    for r in top + share_selected:
        key = (tuple(r.get("seq", ())), r.get("length", 0))
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out

def _decorate_sequences(image_id: int, items: list[dict]) -> dict:
    """
    Enrich plain sequence rows with Gardiner metadata and display helpers.
    """
    if not items:
        return {"image_id": image_id, "items": [], "lengths": []}

    all_ids: set[int] = set()
    for row in items:
        seq = row.get("seq") or []
        all_ids.update(int(x) for x in seq if x is not None)

    gard_map = _gardiner_map_for_ids(all_ids)

    total_count = sum(int(row.get("count", 0)) for row in items) or 1
    lengths: set[int] = set()
    enriched: list[dict] = []
    for row in items:
        seq = tuple(int(x) for x in (row.get("seq") or []))
        lengths.add(len(seq))

        codes = [
            _normalize_gardiner_code(gard_map.get(gid, {}).get("code", ""))
            for gid in seq
        ]
        unicodes = [
            _normalize_unicode(gard_map.get(gid, {}).get("unicode", ""))
            for gid in seq
        ]
        symbols = [_unicode_to_symbol([u]) if u else "" for u in unicodes]

        if "share_percent" in row:
            share = float(row["share_percent"])
        else:
            share = (float(row.get("count", 0)) / total_count) * 100.0 if total_count else 0.0

        enriched.append(
            {
                **row,
                "gardiner_ids": list(seq),
                "gardiner_codes": codes,
                "unicode_values": unicodes,
                "symbol_values": symbols,
                "symbol": "".join(symbols),
                "share_percent": share,
            }
        )

    return {"image_id": image_id, "items": enriched, "lengths": sorted(lengths)}
