#!/usr/bin/env python3
"""Audit all registered icons for black backgrounds, missing files, and policy violations."""
import sys
from pathlib import Path

HERE = Path(__file__).parent.parent
sys.path.insert(0, str(HERE))

import xml.etree.ElementTree as ET  # noqa: E402
from ui.icon_registry import ICON_REGISTRY  # noqa: E402

SVG_NS = "http://www.w3.org/2000/svg"
BLACK_COLORS = {"#000", "#000000", "black", "rgb(0,0,0)", "rgb(0, 0, 0)"}


def check_svg_background(path: str) -> list[str]:
    """Check an SVG for black background elements. Returns list of warnings."""
    warnings = []
    try:
        tree = ET.parse(path)
        root = tree.getroot()
        for rect in root.iter(f"{{{SVG_NS}}}rect"):
            fill = (rect.get("fill") or "").lower().replace(" ", "")
            if fill in BLACK_COLORS:
                w = rect.get("width", "?")
                h = rect.get("height", "?")
                warnings.append(f"  WARN: black rect found (fill={fill}, w={w}, h={h})")
        for elem in root.iter():
            style = elem.get("style", "")
            if "background" in style.lower() and "#000" in style:
                warnings.append(f"  WARN: background style with black: {style}")
    except ET.ParseError as e:
        warnings.append(f"  ERROR: XML parse failed: {e}")
    except Exception as e:
        warnings.append(f"  ERROR: {e}")
    return warnings


def check_png_alpha(path: str) -> list[str]:
    """Check PNG has alpha channel. Returns list of warnings."""
    warnings = []
    try:
        from PySide6.QtGui import QImage
        img = QImage(path)
        if img.isNull():
            warnings.append("  ERROR: cannot load PNG")
            return warnings
        alpha = False
        for y in range(img.height()):
            for x in range(img.width()):
                if img.pixelColor(x, y).alpha() < 255:
                    alpha = True
                    break
            if alpha:
                break
        if not alpha:
            warnings.append("  WARN: PNG has no alpha channel (fully opaque)")
    except ImportError:
        warnings.append("  WARN: PySide6 not available for PNG check")
    return warnings


def main():
    errors = 0
    warnings = 0
    seen_files = set()

    for key, spec in sorted(ICON_REGISTRY.items()):
        full = HERE / spec.path
        prefix = f"[{spec.family}] {key}"

        if not full.exists():
            print(f"{prefix}: ERROR — file not found: {full}")
            errors += 1
            continue

        seen_files.add(str(full.resolve()))

        if spec.family != "app" and not spec.allow_background:
            if spec.path.endswith(".svg"):
                svg_warns = check_svg_background(str(full))
                for w in svg_warns:
                    print(f"{prefix}:{w}")
                    if "ERROR" in w:
                        errors += 1
                    else:
                        warnings += 1
            elif spec.path.endswith(".png"):
                png_warns = check_png_alpha(str(full))
                for w in png_warns:
                    print(f"{prefix}:{w}")
                    if "ERROR" in w:
                        errors += 1
                    else:
                        warnings += 1

        if (spec.family in ("sidebar", "action", "folder", "tray", "view")
                and spec.path.endswith(".svg") and spec.symbolic):
            try:
                tree = ET.parse(str(full))
                root = tree.getroot()
                text = ET.tostring(root, encoding="unicode").lower()
                if "currentcolor" not in text:
                    print(f"{prefix}: WARN — symbolic SVG without currentColor")
                    warnings += 1
            except Exception:
                pass

    print()
    print(f"Total: {len(ICON_REGISTRY)} icons, "
          f"{errors} errors, {warnings} warnings")
    return 1 if errors > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
