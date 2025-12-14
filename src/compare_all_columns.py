"""Show all columns side-by-side with differences highlighted."""

import sys
import io
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.patches as patches

from src.database.select import run_select


def group_into_columns(items, tolerance=100.0, x_idx=1):
    """Group glyphs into columns."""
    items = sorted(items, key=lambda r: r[x_idx])
    
    columns = []
    i = 0
    n = len(items)
    
    while i < n:
        x0 = items[i][x_idx]
        current_col = []
        while i < n and items[i][x_idx] <= x0 + tolerance:
            current_col.append(items[i])
            i += 1
        columns.append(current_col)
    
    return columns


def get_glyph_ids(column):
    """Extract glyph IDs from a column."""
    return set([item[0] for item in column])


def compare_all_columns(image_id, tolerance=100.0):
    """Show full image with both methods and highlight differences.
    
    Args:
        image_id: Database ID of papyrus
        tolerance: Column grouping threshold
    """
    # Get image
    rows = run_select(
        "SELECT img, mimetype FROM T_IMAGES WHERE id = %s",
        (image_id,)
    )
    if not rows:
        print(f"No image found for ID {image_id}")
        return
    
    img_bytes, mimetype = rows[0]
    img = Image.open(io.BytesIO(img_bytes))
    
    # Get raw glyphs
    rows = run_select(
        "SELECT id, bbox_x, bbox_y, bbox_width, bbox_height "
        "FROM T_GLYPHES_RAW WHERE id_image = %s",
        (image_id,)
    )
    
    if not rows:
        print(f"No glyphs found for image {image_id}")
        return
    
    # Group by both methods
    print("Grouping with bbox method...")
    bbox_items = [(r[0], r[1], r[2], r[1], r[2], r[3], r[4]) for r in rows]
    bbox_columns = group_into_columns(bbox_items, tolerance=tolerance, x_idx=1)
    
    print("Grouping with center method...")
    center_items = [(r[0], r[1] + r[3]/2, r[2] + r[4]/2, r[1], r[2], r[3], r[4]) for r in rows]
    center_columns = group_into_columns(center_items, tolerance=tolerance, x_idx=1)
    
    print(f"\nBbox method: {len(bbox_columns)} columns")
    print(f"Center method: {len(center_columns)} columns")
    
    # Analyze differences
    differences = []
    max_cols = max(len(bbox_columns), len(center_columns))
    
    for i in range(max_cols):
        if i < len(bbox_columns) and i < len(center_columns):
            bbox_ids = get_glyph_ids(bbox_columns[i])
            center_ids = get_glyph_ids(center_columns[i])
            
            if bbox_ids != center_ids:
                only_in_bbox = len(bbox_ids - center_ids)
                only_in_center = len(center_ids - bbox_ids)
                differences.append({
                    'col': i,
                    'only_bbox': only_in_bbox,
                    'only_center': only_in_center,
                    'total_diff': only_in_bbox + only_in_center
                })
        elif i < len(bbox_columns):
            differences.append({
                'col': i,
                'only_bbox': len(bbox_columns[i]),
                'only_center': 0,
                'total_diff': len(bbox_columns[i])
            })
        else:
            differences.append({
                'col': i,
                'only_bbox': 0,
                'only_center': len(center_columns[i]),
                'total_diff': len(center_columns[i])
            })
    
    print(f"\nColumns with differences: {len(differences)}")
    if differences:
        print("\nTop 10 columns with most differences:")
        for diff in sorted(differences, key=lambda x: x['total_diff'], reverse=True)[:10]:
            print(f"  Column {diff['col']}: {diff['total_diff']} glyphs differ "
                  f"(bbox only: {diff['only_bbox']}, center only: {diff['only_center']})")
    
    # Show ALL columns
    diff_col_indices = sorted([d['col'] for d in differences])
    
    if not diff_col_indices:
        print("\nNo differences found! Both methods produce identical results.")
        return
    
    print(f"\nGenerating side-by-side comparison for all columns...")
    
    # Create multiple images to cover all columns
    max_cols = max(len(bbox_columns), len(center_columns))
    cols_per_image = 10  # Show 10 columns per image for readability
    num_images = (max_cols + cols_per_image - 1) // cols_per_image  # Ceiling division
    
    output_files = []
    
    for img_num in range(num_images):
        start_col = img_num * cols_per_image
        end_col = min(start_col + cols_per_image, max_cols)
        n_cols_in_image = end_col - start_col
        
        print(f"  Creating image {img_num + 1}/{num_images} (columns {start_col}-{end_col-1})...")
        
        fig, axes = plt.subplots(2, n_cols_in_image, figsize=(4*n_cols_in_image, 10))
        
        # Handle axes indexing for different numbers of columns
        if n_cols_in_image == 1:
            axes = axes.reshape(2, 1)
        
        for plot_idx in range(n_cols_in_image):
            col_idx = start_col + plot_idx
            
            # Get bbox column
            bbox_col = bbox_columns[col_idx] if col_idx < len(bbox_columns) else []
            center_col = center_columns[col_idx] if col_idx < len(center_columns) else []
            
            # Get glyph IDs to find differences
            bbox_ids = get_glyph_ids(bbox_col) if bbox_col else set()
            center_ids = get_glyph_ids(center_col) if center_col else set()
            only_in_bbox = bbox_ids - center_ids
            only_in_center = center_ids - bbox_ids
            has_diff = len(only_in_bbox) > 0 or len(only_in_center) > 0
            
            # Get axes for this column
            if n_cols_in_image == 1:
                ax_bbox = axes[0]
                ax_center = axes[1]
            else:
                ax_bbox = axes[0, plot_idx]
                ax_center = axes[1, plot_idx]
            
            # BBOX visualization
            if bbox_col:
                xs = [item[3] for item in bbox_col]
                ys = [item[4] for item in bbox_col]
                min_x = min(xs)
                max_x = max([item[3] + item[5] for item in bbox_col])
                min_y = min(ys)
                max_y = max([item[4] + item[6] for item in bbox_col])
                
                crop_bbox = img.crop((min_x, min_y, max_x, max_y))
                
                ax_bbox.imshow(crop_bbox)
                title_color = 'red' if has_diff else 'black'
                ax_bbox.set_title(f"Col {col_idx} - BBOX\n{len(bbox_col)} glyphs", 
                                 fontsize=10, fontweight='bold', color=title_color)
                ax_bbox.axis('off')
                
                # Draw ALL boxes - green for all, red overlay for differences
                for item in bbox_col:
                    glyph_id = item[0]
                    x, y, w, h = item[3], item[4], item[5], item[6]
                    x_adj = x - min_x
                    y_adj = y - min_y
                    
                    # First draw green box for all glyphs
                    rect_green = patches.Rectangle(
                        (x_adj, y_adj), w, h,
                        linewidth=1, edgecolor='green', facecolor='none', alpha=0.5
                    )
                    ax_bbox.add_patch(rect_green)
                    
                    # Then overlay red box if it's a difference
                    if glyph_id in only_in_bbox:
                        rect_red = patches.Rectangle(
                            (x_adj, y_adj), w, h,
                            linewidth=2, edgecolor='red', facecolor='none', alpha=0.9
                        )
                        ax_bbox.add_patch(rect_red)
            else:
                ax_bbox.text(0.5, 0.5, f"Col {col_idx}\nEmpty", 
                                       ha='center', va='center', fontsize=12)
                ax_bbox.axis('off')
            
            # CENTER visualization
            if center_col:
                xs = [item[3] for item in center_col]
                ys = [item[4] for item in center_col]
                min_x = min(xs)
                max_x = max([item[3] + item[5] for item in center_col])
                min_y = min(ys)
                max_y = max([item[4] + item[6] for item in center_col])
                
                crop_center = img.crop((min_x, min_y, max_x, max_y))
                
                ax_center.imshow(crop_center)
                title_color = 'blue' if has_diff else 'black'
                ax_center.set_title(f"Col {col_idx} - CENTER\n{len(center_col)} glyphs", 
                                   fontsize=10, fontweight='bold', color=title_color)
                ax_center.axis('off')
                
                # Draw ALL boxes - green for all, blue overlay for differences
                for item in center_col:
                    glyph_id = item[0]
                    x, y, w, h = item[3], item[4], item[5], item[6]
                    x_adj = x - min_x
                    y_adj = y - min_y
                    
                    # First draw green box for all glyphs
                    rect_green = patches.Rectangle(
                        (x_adj, y_adj), w, h,
                        linewidth=1, edgecolor='green', facecolor='none', alpha=0.5
                    )
                    ax_center.add_patch(rect_green)
                    
                    # Then overlay blue box if it's a difference
                    if glyph_id in only_in_center:
                        rect_blue = patches.Rectangle(
                            (x_adj, y_adj), w, h,
                            linewidth=2, edgecolor='blue', facecolor='none', alpha=0.9
                        )
                        ax_center.add_patch(rect_blue)
            else:
                ax_center.text(0.5, 0.5, f"Col {col_idx}\nEmpty", 
                                       ha='center', va='center', fontsize=12)
                ax_center.axis('off')
        
        plt.suptitle(f"Image {image_id} - Columns {start_col}-{end_col-1} (Green=all glyphs, Red=bbox only, Blue=center only)", 
                     fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        # Save
        output_file = f"all_columns_{image_id}_part{img_num+1:02d}.png"
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        output_files.append(output_file)
        plt.close()
    
    print(f"\n✓ Generated {num_images} image(s) covering all {max_cols} columns:")
    for f in output_files:
        print(f"  - {f}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m src.compare_all_columns <image_id> [--tolerance N]")
        print("Examples:")
        print("  python -m src.compare_all_columns 2")
        print("  python -m src.compare_all_columns 2 --tolerance 150")
        sys.exit(1)
    
    tolerance = 100.0
    args = []
    
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--tolerance" and i + 1 < len(sys.argv):
            tolerance = float(sys.argv[i + 1])
            i += 2
        else:
            args.append(arg)
            i += 1
    
    image_id = int(args[0])
    compare_all_columns(image_id, tolerance)
