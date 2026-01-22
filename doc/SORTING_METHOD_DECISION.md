# Sorting Method Decision: Center of Gravity vs Bounding Box

## Background

The reading order reconstruction algorithm needs to group hieroglyphs into vertical columns based on their x-coordinates. Two approaches were evaluated:

1. **Bounding Box (bbox)**: Uses top-left corner coordinates (bbox_x, bbox_y)
2. **Center of Gravity (center)**: Uses center point coordinates (bbox_x + bbox_width/2, bbox_y + bbox_height/2)

## Comparison Methodology

- Generated side-by-side visualizations of all 59 columns in the papyrus
- Compared column groupings for both methods
- Analyzed differences in glyph assignments
- Visual inspection of 6 comparison images (archived in `doc/sorting_comparison_results/`)

## Results

### Statistical Comparison
- Both methods detected 59 columns
- Differences observed in 56 columns
- Differences primarily affected wide glyphs and boundary cases

### Key Observations

**Bounding Box method weaknesses:**
- Wide glyphs misplaced: A glyph with large width has its left edge far from its visual center, causing it to be grouped with the wrong column
- Boundary sensitivity: Glyphs near column boundaries are more likely to be assigned incorrectly
- Less intuitive: Left edge position doesn't represent where the glyph "belongs" visually

**Center of Gravity method strengths:**
- More robust for irregular shapes: Hieroglyphs vary significantly in width
- Handles overlapping glyphs better: Center position is more stable than edge position
- More semantically correct: The center point better represents the glyph's actual location in the column

## Decision

**Chosen method**: Center of Gravity

**Reasons**:
1. **Accuracy**: Visual inspection showed center method produced more accurate column groupings, especially for wide glyphs (e.g., large determinatives)
2. **Semantic correctness**: Center position better represents where a glyph semantically belongs in the reading order
3. **Robustness**: Less sensitive to annotation quality variations in bounding box boundaries

## Limitations

Both methods still produce some errors. No automatic algorithm can perfectly reconstruct reading order for all cases, especially when:
- Glyphs are very close together
- Column boundaries are ambiguous
- Text includes insertions or corrections by the scribe

**Solution**: Manual correction interface planned for frontend to allow human validation and correction of automatic sorting results.
