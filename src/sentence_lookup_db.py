"""Match Gardiner code patterns to TLA sentence data using database."""

import re
from typing import Optional

# Using the project's standard tool
from src.database.tools import select

def _get_codes(mdc: str) -> list[str]:
    """Return a list of individual codes from an MDC string."""
    if not mdc:
        return []
    return re.findall(r"[A-Z][a-z]?\d+[A-Z]?", mdc)

def _normalize(mdc: str) -> str:
    """Flatten MDC into a dash-separated string for searching."""
    return "-".join(_get_codes(mdc))

def lookup_all(pattern: list[str]) -> list[dict]:
    target = "-".join(pattern)
    target_len = len(pattern)
    results = []
    
    # Fetch sentences
    rows = select("""
        SELECT id, mdc_compact, transcription, translation, tokens
        FROM T_SENTENCES
    """)
    
    for r in rows:
        sent_id, mdc_compact, transcription, translation, tokens = r
        if not tokens: 
            tokens = []
            
        normalized_mdc = _normalize(mdc_compact)
        
        # 1. Check if pattern exists in the sentence
        if target in normalized_mdc:
            occurrence_count = normalized_mdc.count(target)
            
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
            for i in range(len(all_codes) - target_len + 1):
                if all_codes[i : i + target_len] == pattern:
                    match_indices.append(i)

            # 4. Extract the unique tokens involved in these matches
            matching_tokens = []
            seen_token_indices = set()
            lemma_ids_to_fetch = set()

            for start_idx in match_indices:
                for i in range(target_len):
                    code_idx = start_idx + i
                    if code_idx < len(code_map):
                        t_idx, token = code_map[code_idx]
                        if t_idx not in seen_token_indices:
                            matching_tokens.append(token)
                            seen_token_indices.add(t_idx)
                            if token.get("lemma_id"):
                                lemma_ids_to_fetch.add(token["lemma_id"])

            # 5. Bulk fetch frequencies
            frequencies = _count_corpus_occurrences(lemma_ids_to_fetch)
            
            for token in matching_tokens:
                lid = token.get("lemma_id", "")
                token["corpus_frequency"] = frequencies.get(lid, 0)
            
            results.append({
                "id": sent_id,
                "mdc_compact": mdc_compact,
                "transcription": transcription,
                "translation": translation,
                "matching_tokens": matching_tokens, 
                "match_occurrence_count": occurrence_count,
            })

    # Sort by number of matches (descending), then by ID
    results.sort(key=lambda x: (x['match_occurrence_count'], x['id']), reverse=True)
    return results


def _count_corpus_occurrences(target_ids: set[str]) -> dict[str, int]:
    if not target_ids:
        return {}
    
    rows = select("""
        SELECT token->>'lemma_id', COUNT(*)
        FROM T_SENTENCES,
        jsonb_array_elements(tokens) as token
        WHERE token->>'lemma_id' IN %s
        GROUP BY token->>'lemma_id'
    """, (tuple(target_ids),))
    
    return {row[0]: row[1] for row in rows}


if __name__ == "__main__":
    test_pattern = ["F20", "O1", "Z1", "W24", "W24", "W24", "A17", "A52", "N35", "F20", "X1", "D21", "S19"]
    pattern_str = "-".join(test_pattern)
    
    print(f"Searching for pattern: {pattern_str}...")
    results = lookup_all(test_pattern)
    print(f"\nFound {len(results)} matching sentences.")
    
    if results:
        limit = 5
        print(f"Showing top {limit} 'most likely' matches (sorted by occurrence count):")
        
        for i, result in enumerate(results[:limit], 1):
            print("\n" + "=" * 60)
            print(f"MATCH {i} (Count: {result['match_occurrence_count']})")
            print("=" * 60)
            print(f"ID: {result['id']}")
            print(f"Transcription: {result['transcription']}")
            print(f"Translation: {result['translation']}")
            print("-" * 20)
            print(f"Tokens containing pattern:")
            
            for t in result['matching_tokens']:
                lemma = t.get('lemma_id', 'N/A')
                freq = t.get('corpus_frequency', 0)
                mdc = t.get('mdc', '')
                pos = t.get('pos', 'N/A')
                
                # Retrieve transliteration (transcription) and translation
                translit = t.get('transcription', '-')
                transl = t.get('translation', '-')

                print(f"  [POS: {pos:<5}] Lemma: {lemma:<7} | Freq: {freq:<4} | MdC: {mdc}")
                print(f"      -> Translit: {translit}")
                print(f"      -> Transl:   {transl}")
    else:
        print("No matches found.")