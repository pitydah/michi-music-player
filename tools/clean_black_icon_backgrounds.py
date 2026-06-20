#!/usr/bin/env python3
"""Clean black backgrounds from PNG icons — flood-fill border-connected black to transparent."""
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent.parent

SRC_DIRS = [
    HERE / "icons" / "sidebar_clean",
    HERE / "icons" / "nowplaying_clean",
]

DEST_DIR = HERE / "icons" / "sidebar_clean"

THRESHOLD = 38  # Max channel value to be considered "black"


def flood_fill_edges(img: Image.Image):
    """Convert border-connected black pixels to transparent."""
    data = img.load()
    w, h = img.size

    # Collect edge black pixels
    stack = []
    visited = set()

    for x in range(w):
        for y in [0, h - 1]:
            r, g, b, a = data[x, y]
            if a > 0 and r < THRESHOLD and g < THRESHOLD and b < THRESHOLD:
                stack.append((x, y))
                visited.add((x, y))

    for y in range(h):
        for x in [0, w - 1]:
            r, g, b, a = data[x, y]
            if a > 0 and r < THRESHOLD and g < THRESHOLD and b < THRESHOLD:
                stack.append((x, y))
                visited.add((x, y))

    # Flood fill
    while stack:
        x, y = stack.pop()
        r, g, b, a = data[x, y]
        if a > 0 and r < THRESHOLD and g < THRESHOLD and b < THRESHOLD:
            data[x, y] = (r, g, b, 0)
            for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in visited:
                    stack.append((nx, ny))
                    visited.add((nx, ny))


def main():
    found = False
    for src_dir in SRC_DIRS:
        if not src_dir.exists():
            print(f"  skip: {src_dir} (not found)")
            continue

        dest = DEST_DIR if src_dir.name == "sidebar_clean" else (
                HERE / "icons" / "nowplaying_clean")
        dest.mkdir(parents=True, exist_ok=True)

        for png in sorted(src_dir.glob("*.png")):
            img = Image.open(png).convert("RGBA")
            original = img.copy()
            flood_fill_edges(img)

            if list(img.getdata()) != list(original.getdata()):
                out = dest / png.name
                img.save(out)
                print(f"  cleaned: {png.name} → {out}")
                found = True

    if not found:
        print("No icons needed cleaning.")
    else:
        print("Done. Original files preserved.")


if __name__ == "__main__":
    main()
