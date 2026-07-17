#!/usr/bin/env python3
"""Audit QML files for hardcoded tokens instead of MichiTheme usage."""

import argparse
import json
import os
import re
import sys

UI_QML = os.path.join(os.path.dirname(__file__), "..", "ui_qml")

HARDCODED_COLORS = re.compile(
    r"""
    (?<!MichiTheme\.colors\.)
    (
        \#[0-9a-fA-F]{6}\b
        |
        \#[0-9a-fA-F]{3}\b
        |
        rgba\s*\(
        |
        (?<=[\s:=,(])(?<![.\w])
        (white|black|red|green|blue|yellow|cyan|magenta|gray|grey|orange|purple|pink|brown|transparent)
        (?![.\w])
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

LITERAL_RADIUS = re.compile(r"""\bradius\s*:\s*(\d+)\b""")
LITERAL_FONT_SIZE = re.compile(r"""font\.pixelSize\s*:\s*(\d+)\b""")
LITERAL_OPACITY = re.compile(r"""\bopacity\s*:\s*(0\.\d+)\b""")
LITERAL_SPACING = re.compile(r"""\b(spacing|topPadding|bottomPadding|leftPadding|rightPadding)\s*:\s*(\d+)\b""")
LITERAL_MARGIN = re.compile(r"""\b(topMargin|bottomMargin|leftMargin|rightMargin|margins)\s*:\s*(\d+)\b""")

COMMENT = re.compile(r"//.*$", re.MULTILINE)

KNOWN_RADII = {4, 6, 8, 12, 16, 22, 999}
RADIUS_SUGGESTIONS = {
    4: "MichiTheme.radiusXs",
    6: "MichiTheme.radiusXs",
    8: "MichiTheme.radiusSm",
    12: "MichiTheme.radiusMd",
    16: "MichiTheme.radiusLg",
    22: "MichiTheme.radiusXl",
    999: "MichiTheme.radiusPill",
}

KNOWN_FONT_SIZES = {28, 22, 18, 15, 13, 12, 11, 10}
FONT_SUGGESTIONS = {
    28: "MichiTheme.typography.heroTitleSize",
    22: "MichiTheme.typography.pageTitleSize",
    18: "MichiTheme.typography.sectionTitleSize",
    15: "MichiTheme.typography.cardTitleSize",
    13: "MichiTheme.typography.bodySize",
    12: "MichiTheme.typography.captionSize",
    11: "MichiTheme.typography.metaSize",
    10: "MichiTheme.typography.badgeSize",
}

KNOWN_SPACING = {4, 8, 12, 16, 24, 32, 40}
SPACING_SUGGESTIONS = {
    4: "MichiTheme.spacing.xs",
    8: "MichiTheme.spacing.sm",
    12: "MichiTheme.spacing.md",
    16: "MichiTheme.spacing.lg",
    24: "MichiTheme.spacing.xl",
    32: "MichiTheme.spacing.xxl",
    40: "MichiTheme.spacing.page",
}

IGNORE_PATTERNS = re.compile(
    r"MichiTheme\.\w+"
    r"|Qt\.rgba"
    r"|Behavior\s+on"
    r"|property\s+\w+"
    r"|readonly\s+property"
)


def strip_comments(text):
    return COMMENT.sub("", text)


def is_in_theme_context(line):
    return bool(IGNORE_PATTERNS.search(line))


def scan_file(qml_path):
    findings = []
    try:
        with open(qml_path, encoding="utf-8") as f:
            raw = f.read()
    except (OSError, UnicodeDecodeError):
        return findings

    clean = strip_comments(raw)
    lines = clean.split("\n")
    rel = os.path.relpath(qml_path, os.path.dirname(UI_QML))

    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("//"):
            continue
        if is_in_theme_context(stripped):
            continue
        if "import " in stripped:
            continue

        for match in HARDCODED_COLORS.finditer(stripped):
            val = match.group(0)
            if val.lower() in ("white", "black", "red", "green", "blue",
                                "yellow", "cyan", "magenta", "gray", "grey",
                                "orange", "purple", "pink", "brown", "transparent"):
                findings.append({
                    "file": rel,
                    "line": lineno,
                    "pattern_type": "hardcoded_color_name",
                    "value": val,
                    "suggested_token": "MichiTheme.colors.*",
                })
            elif val.startswith("rgba"):
                findings.append({
                    "file": rel,
                    "line": lineno,
                    "pattern_type": "hardcoded_rgba",
                    "value": val.strip(),
                    "suggested_token": "MichiTheme.colors.*",
                })
            else:
                findings.append({
                    "file": rel,
                    "line": lineno,
                    "pattern_type": "hardcoded_hex_color",
                    "value": val,
                    "suggested_token": "MichiTheme.colors.*",
                })

        for match in LITERAL_RADIUS.finditer(stripped):
            val = int(match.group(1))
            if val not in KNOWN_RADII:
                findings.append({
                    "file": rel,
                    "line": lineno,
                    "pattern_type": "literal_radius",
                    "value": val,
                    "suggested_token": "MichiTheme.radius*",
                })
            elif val in RADIUS_SUGGESTIONS and "MichiTheme" not in stripped.split("radius")[0]:
                findings.append({
                    "file": rel,
                    "line": lineno,
                    "pattern_type": "literal_radius",
                    "value": val,
                    "suggested_token": RADIUS_SUGGESTIONS[val],
                })

        for match in LITERAL_FONT_SIZE.finditer(stripped):
            val = int(match.group(1))
            before = stripped.split("font.pixelSize")[0]
            if "MichiTheme" not in before:
                suggestion = FONT_SUGGESTIONS.get(val, "MichiTheme.typography.*")
                findings.append({
                    "file": rel,
                    "line": lineno,
                    "pattern_type": "literal_font_pixelSize",
                    "value": val,
                    "suggested_token": suggestion,
                })

        for match in LITERAL_OPACITY.finditer(stripped):
            val = match.group(1)
            before = stripped.split("opacity")[0]
            if "MichiTheme" not in before:
                findings.append({
                    "file": rel,
                    "line": lineno,
                    "pattern_type": "literal_opacity",
                    "value": val,
                    "suggested_token": "MichiTheme.opacity*",
                })

        for match in LITERAL_SPACING.finditer(stripped):
            val = int(match.group(2))
            before = stripped.split(match.group(1))[0]
            if "MichiTheme" not in before:
                suggestion = SPACING_SUGGESTIONS.get(val, "MichiTheme.spacing.*")
                findings.append({
                    "file": rel,
                    "line": lineno,
                    "pattern_type": "literal_" + match.group(1),
                    "value": val,
                    "suggested_token": suggestion,
                })

        for match in LITERAL_MARGIN.finditer(stripped):
            val = int(match.group(2))
            before = stripped.split(match.group(1))[0]
            if "MichiTheme" not in before:
                suggestion = SPACING_SUGGESTIONS.get(val, "MichiTheme.spacing.*")
                findings.append({
                    "file": rel,
                    "line": lineno,
                    "pattern_type": "literal_" + match.group(1),
                    "value": val,
                    "suggested_token": suggestion,
                })

    return findings


def main():
    parser = argparse.ArgumentParser(description="Audit QML files for hardcoded tokens")
    parser.add_argument("--format", choices=["json", "text"], default="text")
    args = parser.parse_args()

    base = os.path.abspath(UI_QML)
    if not os.path.isdir(base):
        print("[]" if args.format == "json" else "ui_qml/ not found", file=sys.stderr)
        return

    all_findings = []
    for root, _dirs, files in os.walk(base):
        for f in files:
            if f.endswith(".qml"):
                all_findings.extend(scan_file(os.path.join(root, f)))

    if args.format == "json":
        print(json.dumps(all_findings, indent=2))
    else:
        if not all_findings:
            print("✓ No hardcoded token violations found.")
            return
        for finding in all_findings:
            print(
                f"{finding['file']}:{finding['line']}  "
                f"[{finding['pattern_type']}]  "
                f"value={finding['value']}  "
                f"suggested={finding['suggested_token']}"
            )
        sys.exit(1 if all_findings else 0)


if __name__ == "__main__":
    main()
