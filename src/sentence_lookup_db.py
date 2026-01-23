"""Match Gardiner code patterns to TLA sentence data using database.

This module searches the Thesaurus Linguae Aegyptiae (TLA) sentence database
for matches to detected hieroglyphic patterns. It extracts matching tokens
with their linguistic information (lemma, POS, transcription, translation)
and calculates corpus frequency for each token.

For long patterns (>15 codes), it automatically searches for sub-patterns
using a sliding window approach to find partial matches in the corpus.
"""

import re

from src.database.tools import select


def _get_codes(mdc: str) -> list[str]:
    """Return a list of individual codes from an MDC string.

    Extracts Gardiner codes and normalizes them to standard format:
    - First letter(s): Capital first, lowercase second (Aa not AA)
    - Examples: A1, Aa1, D21, G43
    """
    if not mdc:
        return []
    codes = re.findall(r"[A-Z][a-z]?\d+[A-Z]?", mdc)
    # Normalize: ensure double-letter codes are like "Aa" not "AA"
    normalized = []
    for code in codes:
        if len(code) >= 2 and code[0].isupper() and code[1].isupper():
            # Convert AA1 -> Aa1
            normalized.append(code[0] + code[1].lower() + code[2:])
        else:
            normalized.append(code)
    return normalized


def _normalize(mdc: str) -> str:
    """Flatten MDC into a dash-separated string for searching."""
    return "-".join(_get_codes(mdc))


def _normalize_pattern(pattern: list[str]) -> list[str]:
    """Normalize Gardiner codes to match TLA database format.

    Converts codes like AA1, AA11 to Aa1, Aa11 (capital first, lowercase second).

    Args:
        pattern: List of Gardiner codes (may have inconsistent casing)

    Returns:
        List of normalized Gardiner codes
    """
    normalized = []
    for code in pattern:
        if len(code) >= 2 and code[0].isupper() and code[1].isupper():
            # Convert AA1 -> Aa1, AA11 -> Aa11
            normalized.append(code[0] + code[1].lower() + code[2:])
        else:
            normalized.append(code)
    return normalized


def lookup_all(
    pattern: list[str],
    min_subpattern_len: int = 5,
    include_partials: bool = True,
) -> list[dict]:
    """Look up sentences matching a pattern.

    For long patterns (>15 codes), also searches for sub-patterns of length min_subpattern_len.
    This helps find partial matches in the corpus.

    Args:
        pattern: List of Gardiner codes to search for
        min_subpattern_len: Minimum length of sub-patterns to search (default: 5)
    """
    # Normalize input pattern to match TLA format (AA1 -> Aa1, etc.)
    pattern = _normalize_pattern(pattern)

    target_len = len(pattern)

    # For long patterns, also search for sub-patterns
    # This helps find partial matches when the full sequence is too specific
    search_patterns: list[tuple[list[str], int, str, int]] = [
        (pattern, target_len, "full", 0)
    ]  # (subpattern, length, type, start_in_original)

    if include_partials and target_len >= 10:
        # Determine sub-pattern length based on pattern size
        if target_len >= 30:
            subpattern_len = 7  # Very long patterns: use 7-code chunks
        elif target_len >= 20:
            subpattern_len = 6  # Long patterns: use 6-code chunks
        elif target_len >= 15:
            subpattern_len = 5  # Medium patterns: use 5-code chunks
        else:
            subpattern_len = 4  # Shorter patterns (10-14): use 4-code chunks

        # Override with minimum if specified
        subpattern_len = max(min_subpattern_len, subpattern_len)

        # Generate sliding window sub-patterns, overlapping by half
        step = max(2, subpattern_len // 2)  # Step by half the window size
        for i in range(0, target_len - subpattern_len + 1, step):
            sub = pattern[i : i + subpattern_len]
            if len(sub) >= subpattern_len:
                search_patterns.append((sub, len(sub), "partial", i))

    # Fetch all sentences from the TLA database
    # tokens field contains JSONB array with linguistic information for each word
    rows = select("""
        SELECT id, mdc_compact, transcription, translation, tokens
        FROM T_SENTENCES
    """)

    # Track which sentences matched and with which patterns
    sentence_matches: dict[
        int, dict
    ] = {}  # sent_id -> {pattern_info, match_count, tokens}

    for pat, pat_len, match_type, pat_start in search_patterns:
        pat_str = "-".join(pat)

        for r in rows:
            sent_id, mdc_compact, transcription, translation, tokens = r
            if not tokens:
                tokens = []

            normalized_mdc = _normalize(mdc_compact)

            # 1. Check if pattern exists in the sentence
            if pat_str not in normalized_mdc:
                continue

            occurrence_count = normalized_mdc.count(pat_str)

            # If we've already matched this sentence, add to its count
            if sent_id in sentence_matches:
                sentence_matches[sent_id]["match_occurrence_count"] += occurrence_count
                sentence_matches[sent_id]["matched_patterns"].append(
                    {
                        "pattern": pat,
                        "type": match_type,
                        "count": occurrence_count,
                        "pattern_start": pat_start,
                        "pattern_end": pat_start + pat_len,
                    }
                )
                continue

            # 2. Map global code indices to specific tokens
            code_map = []  # list of (token_index, token_data) for every code in the sentence

            for t_idx, token in enumerate(tokens):
                t_mdc = token.get("mdc", "")
                t_codes = _get_codes(t_mdc)
                for _ in t_codes:
                    code_map.append((t_idx, token))

            # 3. Find the pattern matches in the list of codes
            all_codes = _get_codes(mdc_compact)

            # Find all start indices of the pattern
            match_indices = []
            for i in range(len(all_codes) - pat_len + 1):
                if all_codes[i : i + pat_len] == pat:
                    match_indices.append(i)

            # 4. Collect frequencies for ALL tokens in the sentence
            lemma_ids_to_fetch: set[str] = {
                str(t.get("lemma_id"))
                for t in tokens
                if isinstance(t, dict) and t.get("lemma_id") is not None
            }

            frequencies = _count_corpus_occurrences(lemma_ids_to_fetch)

            for token in tokens:
                lid = token.get("lemma_id", "")
                token["corpus_frequency"] = frequencies.get(lid, 0)

            sentence_matches[sent_id] = {
                "id": sent_id,
                "mdc_compact": mdc_compact,
                "transcription": transcription,
                "translation": translation,
                # Return ALL tokens so frontend can display the full sentence tokens
                "matching_tokens": tokens,
                "match_occurrence_count": occurrence_count,
                "matched_patterns": [
                    {
                        "pattern": pat,
                        "type": match_type,
                        "count": occurrence_count,
                        "pattern_start": pat_start,
                        "pattern_end": pat_start + pat_len,
                    }
                ],
            }

    # Convert to list and sort by number of matches (descending), then by ID
    results = list(sentence_matches.values())
    results.sort(key=lambda x: (-x["match_occurrence_count"], x["id"]))
    return results


def _count_corpus_occurrences(target_ids: set[str]) -> dict[str, int]:
    if not target_ids:
        return {}

    rows = select(
        """
        SELECT token->>'lemma_id', COUNT(*)
        FROM T_SENTENCES,
        jsonb_array_elements(tokens) as token
        WHERE token->>'lemma_id' IN %s
        GROUP BY token->>'lemma_id'
    """,
        (tuple(target_ids),),
    )

    return {row[0]: row[1] for row in rows}


if __name__ == "__main__":
    # Test multiple patterns
    test_patterns = [
        ["D21", "Aa1", "Y1", "V31"],  # Short pattern
        ["N35", "X1", "Q1", "D4", "A40"],  # Medium pattern
    ]

    for test_pattern in test_patterns:
        pattern_str = "-".join(test_pattern)

        print(f"\n{'=' * 70}")
        print(f"Searching for pattern (n={len(test_pattern)}): {pattern_str[:50]}...")
        print(f"{'=' * 70}")
        results = lookup_all(test_pattern)
        print(f"Found {len(results)} matching sentences.")

        if results:
            limit = 5
            print(
                f"Showing top {limit} 'most likely' matches (sorted by occurrence count):"
            )

            for i, result in enumerate(results[:limit], 1):
                print("\n" + "=" * 60)
                print(f"MATCH {i} (Count: {result['match_occurrence_count']})")
                print("=" * 60)
                print(f"ID: {result['id']}")
                print(f"Transcription: {result['transcription']}")
                print(f"Translation: {result['translation']}")
                print("-" * 20)
                print("Tokens containing pattern:")

                for t in result["matching_tokens"]:
                    lemma = t.get("lemma_id", "N/A")
                    freq = t.get("corpus_frequency", 0)
                    mdc = t.get("mdc", "")
                    pos = t.get("pos", "N/A")

                    # Retrieve transliteration (transcription) and translation
                    translit = t.get("transcription", "-")
                    transl = t.get("translation", "-")

                    print(
                        f"  [POS: {pos:<5}] Lemma: {lemma:<7} | Freq: {freq:<4} | MdC: {mdc}"
                    )
                    print(f"      -> Translit: {translit}")
                    print(f"      -> Transl:   {transl}")
        else:
            print("No matches found.")
