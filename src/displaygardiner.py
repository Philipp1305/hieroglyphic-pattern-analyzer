from __future__ import annotations

import sys
import re
from typing import Iterable
from pathlib import Path

from src.database.select import run_select
from PIL import Image, ImageDraw, ImageFont


def translate_to_gardiner(image_id: int) -> list[str]:
    """Return the ordered Gardiner unicodes for one image."""

    sql = (
        "SELECT glysor.v_column, glysor.v_row, garcod.unicode "
        "FROM t_glyphes_sorted AS glysor "
        "JOIN t_glyphes_raw AS glyraw ON glysor.id_glyph = glyraw.id "
        "LEFT JOIN t_gardiner_codes AS garcod ON glyraw.id_gardiner = garcod.id "
        "WHERE glyraw.id_image = %s "
        "ORDER BY glysor.v_column, glysor.v_row"
    )

    rows: Iterable[tuple[int, int, str | None]] = run_select(sql, (image_id,))

    def _convert(u: str | None) -> str:
        if not u:
            return ""
        # Mask out <g>...</g> tags but keep inner content
        s = re.sub(r"</?g[^>]*>", "", u).strip()
        m = re.fullmatch(r"U\+([0-9A-Fa-f]{4,6})", s)
        if not m:
            return s
        cp = int(m.group(1), 16)
        try:
            return chr(cp)
        except ValueError:
            return s

    return [_convert(u) for _, _, u in rows]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m src.displaygardiner <image_id>")
        sys.exit(1)

    glyphs = translate_to_gardiner(int(sys.argv[1]))
    print(glyphs)

