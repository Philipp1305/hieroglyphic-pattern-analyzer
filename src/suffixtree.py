import argparse
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "sorted_glyphes.csv"


def load_sequence() -> list[int]:
    df = pd.read_csv(DATA_PATH)
    return df["gardiner_code"].astype(int).tolist() # Convert to list of integers


def build_suffixes(seq: list[int]) -> list[tuple[list[int], int]]:
    suffixes = [(seq[i:], i) for i in range(len(seq))]          # Create suffixes with their starting indices
    suffixes.sort()                                             # Sort suffixes lexicographically
    return suffixes


def lcp_length(a: list[int], b: list[int]) -> int:
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
        length = lcp_length(s1, s2)

        if length >= min_length and length > 0:
            prefix = tuple(s1[:length])
            lcps.append((length, prefix))

    unique: dict[tuple[int, ...], int] = {}
    for length, prefix in lcps:
        if prefix not in unique or length > unique[prefix]:
            unique[prefix] = length

    sorted_lcps = sorted(unique.items(), key=lambda item: (-item[1], item[0]))
    return [(length, prefix) for prefix, length in sorted_lcps]


def main():
    parser = argparse.ArgumentParser(description="Find repeated glyph sequences with the longest common prefixes.")
    parser.add_argument("--min-length", type=int, default=1, help="Minimum LCP length to report.")
    parser.add_argument("--limit", type=int, default=5, help="How many top LCPs to display.")
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


if __name__ == "__main__":
    main()