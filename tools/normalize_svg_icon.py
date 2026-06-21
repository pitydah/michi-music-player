#!/usr/bin/env python3
"""Normalize an SVG icon: remove black backgrounds, set currentColor, fix viewBox."""
import sys
import shutil
import xml.etree.ElementTree as ET

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)

BLACK_COLORS = {"#000", "#000000", "black", "rgb(0,0,0)", "rgb(0, 0, 0)"}


def normalize_svg(input_path: str, output_path: str, family: str = "sidebar"):
    """Normalize an SVG icon file."""
    tree = ET.parse(input_path)
    root = tree.getroot()

    changed = False

    # Remove black background rects
    to_remove = []
    for rect in root.iter(f"{{{SVG_NS}}}rect"):
        fill = (rect.get("fill") or "").lower().replace(" ", "")
        if fill in BLACK_COLORS:
            w = rect.get("width", "100%")
            h = rect.get("height", "100%")
            if w in ("100%", "512", "256", "128") and h in ("100%", "512", "256", "128"):
                to_remove.append(rect)
    for rect in to_remove:
        root.remove(rect)
        changed = True
        print("  Removed black background rect")

    # Ensure viewBox
    if "viewBox" not in root.attrib:
        w = root.get("width", "24")
        h = root.get("height", "24")
        root.set("viewBox", f"0 0 {w} {h}")
        changed = True
        print(f"  Added viewBox: 0 0 {w} {h}")

    # Convert fixed strokes to currentColor
    fixed_strokes = {"#fff", "#ffffff", "white", "rgb(255,255,255)", "rgb(255, 255, 255)"}
    for elem in root.iter():
        stroke = (elem.get("stroke") or "").lower().replace(" ", "")
        if stroke in fixed_strokes and family != "app":
            elem.set("stroke", "currentColor")
            changed = True
            print(f"  Converted stroke {stroke} → currentColor")

    if not changed:
        print("  No changes needed")
        return False

    # Create backup
    backup = input_path + ".bak"
    shutil.copy2(input_path, backup)
    print(f"  Backup: {backup}")

    # Write
    tree.write(output_path, encoding="unicode", xml_declaration=True)
    print(f"  Written: {output_path}")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python tools/normalize_svg_icon.py <input.svg> --family <family> --out <output.svg>")
        sys.exit(1)

    inp = sys.argv[1]
    family = "sidebar"
    out = inp

    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--family" and i + 1 < len(sys.argv):
            family = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--out" and i + 1 < len(sys.argv):
            out = sys.argv[i + 1]
            i += 2
        else:
            i += 1

    normalize_svg(inp, out, family)
