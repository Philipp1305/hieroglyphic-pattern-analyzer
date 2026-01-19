"""Match Gardiner code patterns to TLA sentence data using database."""

import os
import re
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor

from dotenv import load_dotenv
load_dotenv()


# Database connection parameters from environment variables
DB_PARAMS = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "18936")),
    "database": os.getenv("DB_NAME", "defaultdb"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "sslmode": "require"
}


def _normalize(mdc: str) -> str:
    """Extract Gardiner codes from MDC string."""
    return "-".join(re.findall(r"[A-Z][a-z]?\d+[A-Z]?", mdc))


def lookup_all(pattern: list[str], db_params: dict = DB_PARAMS) -> list[dict]:
    """
    Find all sentences containing the given Gardiner code pattern.
    Returns list of dicts with sentence info.
    """
    target = "-".join(pattern)
    results = []
    
    try:
        conn = psycopg2.connect(**db_params)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Fetch all sentences
        cur.execute("""
            SELECT id, mdc_compact, transcription, translation, tokens
            FROM T_SENTENCES
        """)
        
        rows = cur.fetchall()
        
        # Search for the pattern in all sentences
        for r in rows:
            normalized_mdc = _normalize(r["mdc_compact"])
            if target in normalized_mdc:
                occurrence_count = normalized_mdc.count(target)
                tokens = r["tokens"] or []
                
                # Calculate corpus frequencies
                target_lemma_ids = {
                    token["lemma_id"] 
                    for token in tokens 
                    if token.get("lemma_id")
                }
                
                frequencies = _count_corpus_occurrences(target_lemma_ids, cur)
                
                # Enrich tokens with frequencies
                for token in tokens:
                    lid = token.get("lemma_id", "")
                    token["corpus_frequency"] = frequencies.get(lid, 0)
                
                results.append({
                    "id": r["id"],
                    "mdc_compact": r["mdc_compact"],
                    "transcription": r["transcription"],
                    "translation": r["translation"],
                    "tokens": tokens,
                    "match_occurrence_count": occurrence_count,
                })
        
        cur.close()
        conn.close()
        return results
        
    except Exception as e:
        print(f"Database error: {e}")
        return []


def lookup(pattern: list[str], db_params: dict = DB_PARAMS) -> Optional[dict]:
    """
    Find first sentence containing the given Gardiner code pattern.
    Returns dict with sentence info, including lemma IDs for all tokens
    and their frequency counts across the entire corpus.
    """
    target = "-".join(pattern)
    
    try:
        conn = psycopg2.connect(**db_params)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 1. Find sentences and normalize them in Python to match the pattern
        cur.execute("""
            SELECT id, mdc_compact, transcription, translation, tokens
            FROM T_SENTENCES
        """)
        
        rows = cur.fetchall()
        row = None
        
        # Search for the pattern in normalized mdc_compact
        for r in rows:
            normalized_mdc = _normalize(r["mdc_compact"])
            if target in normalized_mdc:
                row = r
                break
        
        if not row:
            cur.close()
            conn.close()
            return None
        
        # Calculate occurrence count
        normalized_mdc = _normalize(row["mdc_compact"])
        occurrence_count = normalized_mdc.count(target)
        
        # 2. Extract token data
        tokens = row["tokens"] or []
        
        # 3. Calculate corpus frequencies for these lemmas
        target_lemma_ids = {
            token["lemma_id"] 
            for token in tokens 
            if token.get("lemma_id")
        }
        
        frequencies = _count_corpus_occurrences(target_lemma_ids, cur)
        
        # 4. Enrich tokens with their frequencies
        for token in tokens:
            lid = token.get("lemma_id", "")
            token["corpus_frequency"] = frequencies.get(lid, 0)
        
        result = {
            "id": row["id"],
            "mdc_compact": row["mdc_compact"],
            "transcription": row["transcription"],
            "translation": row["translation"],
            "tokens": tokens,
            "match_occurrence_count": occurrence_count,
        }
        
        cur.close()
        conn.close()
        
        return result
        
    except Exception as e:
        print(f"Database error: {e}")
        return None


def _count_corpus_occurrences(target_ids: set[str], cur) -> dict[str, int]:
    """
    Count occurrences of specified lemma IDs across the entire corpus.
    """
    counts = {lid: 0 for lid in target_ids}
    
    if not target_ids:
        return counts
    
    # Query all sentences and count lemma occurrences
    # This uses JSONB array operations for efficient searching
    for lemma_id in target_ids:
        cur.execute("""
            SELECT COUNT(*) as count
            FROM T_SENTENCES,
            jsonb_array_elements(tokens) as token
            WHERE token->>'lemma_id' = %s
        """, (lemma_id,))
        
        result = cur.fetchone()
        counts[lemma_id] = result["count"] if result else 0
    
    return counts


if __name__ == "__main__":
    # Test with a sample pattern
    test = ["D21", "Aa1"]  # Pattern from first row in database
    pattern_str = "-".join(test)
    
    # Find ALL matches
    print(f"Searching for pattern: {pattern_str}")
    results = lookup_all(test)
    print(f"\nFound {len(results)} matching sentences\n")
    
    # Show first match in detail
    if not results:
        print("No matches found")
    else:
        result = results[0]
    
    if result:
        print("\n" + "=" * 60)
        print(f"SENTENCE MATCH FOR PATTERN: {pattern_str}")
        print("=" * 60)
        print(f"ID: {result['id']}")
        print(f"Transcription: {result['transcription']}")
        print(f"Translation: {result['translation']}")
        print(f"Match Occurrence Count: {result['match_occurrence_count']}")
        print("\n" + "=" * 60)
        print(f"PATTERN TOKENS ({pattern_str}):")
        print("=" * 60)
        
        # Find which tokens match the pattern
        normalized_mdc = _normalize(result['mdc_compact'])
        pattern_start = normalized_mdc.find(pattern_str)
        
        # Count how many pattern codes come before the match
        codes_before = normalized_mdc[:pattern_start].split("-") if pattern_start > 0 else []
        token_start_idx = len([c for c in codes_before if c])  # Filter empty strings
        
        # Show only the tokens that match the pattern
        for i in range(len(test)):
            token_idx = token_start_idx + i
            if token_idx < len(result['tokens']):
                t = result['tokens'][token_idx]
                print(f"\nToken {i} ({test[i]}):")
                print(f"  MDC: {t.get('mdc', '')}")
                print(f"  Transcription: {t.get('transcription', '')}")
                print(f"  Translation: {t.get('translation', '')}")
                print(f"  POS: {t.get('pos', '')}")
                print(f"  Lemma ID: {t.get('lemma_id', '')}")
                print(f"  Corpus Frequency: {t.get('corpus_frequency', 0)}")
    else:
        print("No match found")