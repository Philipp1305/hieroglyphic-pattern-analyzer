import pandas as pd
from collections import Counter
from typing import List
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
data_path = BASE_DIR / "data" / "sorted_glyphes.csv"
df = pd.read_csv(data_path)

whole_sequence = df["gardiner_code"].astype(str).tolist()

def count_ngrams(sequence: List[str], n: int) -> Counter:
    c = Counter()
    for i in range(len(sequence)-n+1):
        ngram = tuple(sequence[i:i+n])
        c[ngram] += 1
    return c


def get_top_ngrams_df(sequence: List[str], n: int, topk: int = 30) -> pd.DataFrame:
    """Gibt ein DataFrame mit den Top-n-Grammen zurück.
    Spalten: ngram (tuple), ngram_str (lesbare Darstellung), count, n."""
    c = count_ngrams(sequence, n)
    items = c.most_common(topk)
    df_out = pd.DataFrame([{
        "ngram": item[0],
        "ngram_str": " ".join(map(str, item[0])),
        "count": item[1],
        "n": n
    } for item in items])
    return df_out

def save_ngrams(df: pd.DataFrame, path: str, fmt: str = "csv") -> None:
    """Speichert das DataFrame in csv/json/pickle/parquet (fmt)."""
    p = Path(path)
    df.to_csv(p, index=False, encoding="utf-8")
   
# Beispiel: Top-n-Gramme erzeugen und speichern
if __name__ == "__main__":
    # ...existing code...
    # whole_sequence ist bereits vorhanden oben
    for n in (10,15,20,27):
        top_df = get_top_ngrams_df(whole_sequence, n, topk=50)
        save_ngrams(top_df, f"top_{n}_grams.csv")
