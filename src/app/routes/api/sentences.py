from __future__ import annotations

from flask import jsonify, request

from src.sentence_lookup_db import lookup_all

from . import bp


@bp.post("/sentences/lookup")
def lookup_sentences():
    """Look up TLA sentences matching a pattern of Gardiner codes.
    
    This endpoint receives a pattern of Gardiner codes (e.g., ["F20", "O1", "Z1"])
    from the frontend and searches the TLA sentence database for matches.
    """
    # Parse the JSON body sent from the frontend
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body provided"}), 400

    # Extract the pattern array from the request
    # Expected format: {"pattern": ["F20", "O1", "Z1", ...]}
    pattern = data.get("pattern")
    if not pattern:
        return jsonify({"error": "Missing 'pattern' field"}), 400

    # Validate that pattern is a list (array)
    if not isinstance(pattern, list):
        return jsonify({"error": "'pattern' must be an array of Gardiner codes"}), 400

    # Validate that all items in the pattern are strings
    if not all(isinstance(code, str) for code in pattern):
        return jsonify({"error": "All pattern items must be strings"}), 400

    # Validate that the pattern is not empty
    if len(pattern) == 0:
        return jsonify({"error": "Pattern cannot be empty"}), 400

    # Call the lookup function from sentence_lookup_db.py
    # This searches the T_SENTENCES table for sentences containing the pattern
    # and returns matching sentences with their tokens and frequencies
    print(f"[sentences API] Received pattern: {pattern}")
    results = lookup_all(pattern)
    print(f"[sentences API] Found {len(results)} matches")

    # Build the JSON response
    response = jsonify(
        {
            "pattern": pattern,  # Echo back the pattern for reference
            "results": results,  # List of matching sentences with tokens
            "count": len(results),  # Total number of matches found
        }
    )
    response.headers["Cache-Control"] = "no-store"
    return response
