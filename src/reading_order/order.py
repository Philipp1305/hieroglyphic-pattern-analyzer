import json
from pathlib import Path, PosixPath
from typing import cast

import numpy as np

import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

BASE_DIR = Path(__file__).resolve().parents[2]
ANNOTATIONS_PATH = BASE_DIR / "data" / "annotations.json"
FONT_PATH = cast(PosixPath, (BASE_DIR / "static" / "NotoSansEgyptianHieroglyphs-Regular.ttf"))
TRANSLATION_PATH = BASE_DIR / "translationorder.txt"

with open(ANNOTATIONS_PATH, 'r', encoding="utf-8") as file:
    annotations = json.load(file)

# Normalize to a list of annotation dicts
if isinstance(annotations, dict):
    if 'annotations' in annotations and isinstance(annotations['annotations'], list):
        annotations = annotations['annotations']
    elif 'features' in annotations and isinstance(annotations['features'], list):
        annotations = annotations['features']
    else:
        annotations = list(annotations.values())  # fallback: take dict values
else:
    annotations = annotations

if not isinstance(annotations, list) or len(annotations) == 0:
    raise ValueError("No annotations found or annotations is not a list.")

glyphs = []

glyphs = []
for d in annotations:
    x, y, w, h = d["bbox"]
    cx, cy = x + w / 2, y + h / 2  # center of the bounding box
    glyphs.append({
        "id": d["id"],
        "unicode": d["attributes"]["Unicode"],
        "x": cx,
        "y": cy,
        "w": w,
        "h": h
    })

direction = "ltr"  # or "rtl"
column_tolerance = 0.7

glyphs.sort(key=lambda g: g['x'])

columns = []
current_col = [glyphs[0]]

for g in glyphs[1:]:
    # Compare current glyph x with average x of current column
    avg_x = np.mean([x["x"] for x in current_col])
    avg_w = np.mean([x["w"] for x in current_col])
    if abs(g["x"] - avg_x) < column_tolerance * avg_w:
        current_col.append(g)
    else:
        columns.append(current_col)
        current_col = [g]
columns.append(current_col)


sequenced_glyphs = []
for col in columns:
    if direction == "ltr":
        col.sort(key=lambda g: g['x'])
    else:
        col.sort(key=lambda g: -g['x'])
    sequenced_glyphs.extend(col)

reading_order = [g['unicode'] for g in sequenced_glyphs]

#sort out every entries that is not a valid unicode
reading_order = [code for code in reading_order if code.startswith('U+')]

glyphs = [chr(int(code.replace('U+', ''), 16)) for code in reading_order]
text = ''.join(glyphs)

font_prop = FontProperties(fname=FONT_PATH, size=40)

with open(TRANSLATION_PATH, 'w', encoding="utf-8") as file:
    file.write(text)
