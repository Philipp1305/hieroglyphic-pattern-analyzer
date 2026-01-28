from __future__ import annotations

from src.database.tools import delete


def delete_existing_entries(id_image: int, code: str) -> None:
    """
    Delete existing data for an image based on the provided code.

    Codes:
    - "ANALYSIS": deletes suffix-array patterns, occurrences, and bboxes for the image.
    - "IMAGE": deletes the image row (cascades to related data).
    - "SORTING": deletes sorted glyph rows for the image.
    """

    normalized = (code or "").strip().upper()
    if not normalized:
        raise ValueError("code is required")

    if normalized == "ANALYSIS":
        delete(
            """
            DELETE FROM T_SUFFIXARRAY_OCCURENCES_BBOXES
            WHERE id_occ IN (
                SELECT occ.id
                FROM T_SUFFIXARRAY_OCCURENCES AS occ
                JOIN T_SUFFIXARRAY_PATTERNS AS pat ON pat.id = occ.id_pattern
                WHERE pat.id_image = %s
            )
            """,
            (id_image,),
        )
        delete(
            """
            DELETE FROM T_SUFFIXARRAY_OCCURENCES
            WHERE id_pattern IN (
                SELECT id FROM T_SUFFIXARRAY_PATTERNS WHERE id_image = %s
            )
            """,
            (id_image,),
        )
        delete(
            "DELETE FROM T_SUFFIXARRAY_PATTERNS WHERE id_image = %s",
            (id_image,),
        )
    elif normalized == "IMAGE":
        delete("DELETE FROM T_IMAGES WHERE id = %s", (id_image,))
    elif normalized == "SORTING":
        delete(
            """
            DELETE FROM T_GLYPHES_SORTED
            WHERE id_glyph IN (
                SELECT id FROM T_GLYPHES_RAW WHERE id_image = %s
            )
            """,
            (id_image,),
        )
    else:
        raise ValueError(f"unknown code '{code}'")
