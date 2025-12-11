#generate a suffixtree based on restored readingorder
import pandas as pd
from collections import Counter
from typing import List
from pathlib import Path
from suffix_trees import STree

BASE_DIR = Path(__file__).resolve().parent.parent
data_path = BASE_DIR / "data" / "sorted_glyphes.csv"
df = pd.read_csv(data_path)

sequence = df["gardiner_code"].astype(str).tolist()
#sequence = ['160', '242', '236', '611', '87', '353', '14', '542', '294', '242', '462', '493', '87', '462', '294', '422', '602', '353', '557', '126', '388', '461']
sequence ='#'.join(sequence) + '$'


def build_suffix_array(s):
    n = len(s)
    k = 1
    rank = [ord(c) for c in s]
    tmp = [0]*n
    sa = list(range(n))

    while k < n:
        sa.sort(key=lambda i: (rank[i], rank[i+k] if i+k < n else -1))
        tmp[sa[0]] = 0

        for i in range(1, n):
            tmp[sa[i]] = tmp[sa[i-1]] + (
                (rank[sa[i-1]], rank[sa[i-1]+k] if sa[i-1]+k < n else -1) <
                (rank[sa[i]],   rank[sa[i]+k]   if sa[i]+k   < n else -1)
            )

        rank = tmp[:]
        k <<= 1

    return sa

def kasai_lcp(s, sa):
    n = len(s)
    k = 0
    rank = [0]*n
    lcp = [0]*n

    for i in range(n):
        rank[i] = sa[i]

    for i in range(n):
        if rank[i] == n-1:
            k = 0
            continue
        j = sa[rank[i] + 1]
        while i+k < n and j+k < n and s[i+k] == s[j+k]:
            k += 1
        lcp[rank[i]] = k
        if k:
            k -= 1

    return lcp


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
    positions = [sa[i] for i in indices] + [sa[i+1] for i in indices]
    positions = sorted(set(positions))

    # Das Substring extrahieren
    substring = s[positions[0]:positions[0] + max_lcp]

    return substring, max_lcp, positions

suffixarray = build_suffix_array(sequence)
#print(suffixarray)
lcp = kasai_lcp(sequence, suffixarray)
print(lcp)
lrs = longest_repeated_substring(sequence,suffixarray,lcp)
#print(lrs[0])
