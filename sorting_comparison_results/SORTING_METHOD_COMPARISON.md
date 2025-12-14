# Column Sorting Method Comparison

## Purpose
Compare two methods for grouping hieroglyphs into columns and decide which one to use.

## The Two Methods

**Bounding Box (bbox)**: Groups glyphs by the x-coordinate of their top-left corner.

**Center of Gravity (center)**: Groups glyphs by the x-coordinate of their center point.

## Review the Images

This folder contains 6 PNG files showing all columns compared side-by-side.

**How to read the images:**
- **Top row**: Bbox method
- **Bottom row**: Center method
- **Green boxes**: All glyphs in that column
- **Red boxes**: Only in bbox (not in center)
- **Blue boxes**: Only in center (not in bbox)

**What to look for:**
1. Which method produces cleaner column divisions?
2. Which method handles wide glyphs better?
3. Which method groups overlapping glyphs more accurately?

## Team Reviews

### Reviewer 1:
**Preferred method**: bbox / center

**Reason**:


---

### Reviewer 2:
**Preferred method**: bbox / center

**Reason**:


---

### Reviewer 3:
**Preferred method**: bbox / center

**Reason**:


---

## Final Decision

**Chosen method**: [To be decided]

**Next steps**: Update `src/sort.py` to use the chosen method as default.

