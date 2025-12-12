# generate a suffixtree based on restored readingorder
import pandas as pd
from collections import Counter
from typing import List
from pathlib import Path
from suffix_trees import STree

BASE_DIR = Path(__file__).resolve().parent.parent
data_path = BASE_DIR / "data" / "sorted_glyphes.csv"
df = pd.read_csv(data_path)

sequence = df["gardiner_code"].astype(str).tolist()
sequence = "#".join(sequence) + "$"


def build_suffix_array(s):
    n = len(s)
    k = 1
    rank = [ord(c) for c in s]
    tmp = [0] * n
    sa = list(range(n))

    while k < n:
        sa.sort(key=lambda i: (rank[i], rank[i + k] if i + k < n else -1))
        tmp[sa[0]] = 0

        for i in range(1, n):
            tmp[sa[i]] = tmp[sa[i - 1]] + (
                (rank[sa[i - 1]], rank[sa[i - 1] + k] if sa[i - 1] + k < n else -1)
                < (rank[sa[i]], rank[sa[i] + k] if sa[i] + k < n else -1)
            )

        rank = tmp[:]
        k <<= 1

    return sa


build_suffix_array(sequence)


def longest_repeated_substring(s, sa, lcp):
    """
    s   : Originalstring
    sa  : Suffix Array
    lcp : LCP Array

    Returns:
      substring, length, positions
    """

    # Größtes LCP finden
    max_lcp = max(lcp)
    if max_lcp == 0:
        return "", 0, []

    # Alle Indizes mit maximalem LCP finden
    indices = [i for i, v in enumerate(lcp) if v == max_lcp]

    # Alle Startpositionen im Text
    positions = [sa[i] for i in indices] + [sa[i + 1] for i in indices]
    positions = sorted(set(positions))

    # Das Substring extrahieren
    substring = s[positions[0] : positions[0] + max_lcp]

    return substring, max_lcp, positions


# print("Loaded sequence of length:", sequence)

"""st = STree.STree(sequence)
print(STree.lrs(st))
print(st.find_all("620"))"""


unique_ids = sorted(set(sequence))
mapping = {id_: chr(0x10000 + i) for i, id_ in enumerate(unique_ids)}

seq_str = "".join(mapping[id_] for id_ in sequence)

# tree = STree.STree(seq_str)

# print(tree.lcs())
