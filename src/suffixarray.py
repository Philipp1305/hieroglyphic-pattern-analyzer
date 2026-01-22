import argparse
import sys
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

DATA_PATH = BASE_DIR / "data" / "sorted_glyphes.csv"

# Runs in O(nlogn)

def load_sequence() -> list[int]:
    df = pd.read_csv(DATA_PATH)
    return df["gardiner_code"].astype(int).tolist() # Convert to list of integers


def build_suffixes(seq: list[int]) -> list[tuple[list[int], int]]:
    suffixes = [(seq[i:], i) for i in range(len(seq))]          # Create suffixes with their starting indices
    suffixes.sort()                                             # Sort suffixes lexicographically
    return suffixes


def lcp_length(a: list[int], b: list[int]) -> int: # Compute length of longest common prefix
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
        length = lcp_length(s1, s2) # Get LCP length between suffixes

        if length >= min_length and length > 0: # Only consider LCPs above min_length. min_length >= 1
            prefix = tuple(s1[:length])
            lcps.append((length, prefix))

    unique: dict[tuple[int, ...], int] = {} # Keep only the longest LCP for each unique prefix
    for length, prefix in lcps:
        if prefix not in unique or length > unique[prefix]: # Update if longer LCP found
            unique[prefix] = length

    sorted_lcps = sorted(unique.items(), key=lambda item: (-item[1], item[0])) # Sort by length desc, then prefix asc
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
        return suffix[:len(pat)] == pat
    
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


def main():
    parser = argparse.ArgumentParser(description="Find repeated glyph sequences with the longest common prefixes.")
    parser.add_argument("--min-length", type=int, default=1, help="Minimum LCP length to report.")
    parser.add_argument("--limit", type=int, default=15, help="How many top LCPs to display.")
    parser.add_argument("--query", type=str, help="Comma-separated Gardiner codes to search as a pattern")
    args = parser.parse_args()

    seq = load_sequence()
    lcps = find_lcps(seq, min_length=args.min_length)

    if not lcps:
        print("No repeated sequences found with the given minimum length.")
        return

    top_lcps = lcps[: args.limit]
    print(f"Top {len(top_lcps)} repeated sequences (length >= {args.min_length}):")
    for length, prefix in top_lcps:
        print(f"length {length}: {list(prefix)}")
    
    if args.query:
        try:
            pattern = [int(x.strip()) for x in args.query.split(",") if x.strip()]
        except ValueError:
            print("Invalid --query pattern. Use comma-separated integers, e.g. '1,2,3'.")
            return
        
        suffixes = build_suffixes(seq)
        occ = search_pattern(suffixes, pattern)
        print(f"\nQuery {pattern} occurrences: {occ}")


if __name__ == "__main__":
    main()