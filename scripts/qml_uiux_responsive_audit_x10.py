#!/usr/bin/env python3
"""Audit QML pages for responsive design compliance."""

import argparse
import json
import os
import re
import sys

UI_QML = os.path.join(os.path.dirname(__file__), "..", "ui_qml")

LITERAL_MARGIN = re.compile(r"margins\s*:\s*(\d+)\b")
LITERAL_ANCHOR_MARGIN = re.compile(r"(topMargin|bottomMargin|leftMargin|rightMargin)\s*:\s*(\d+)\b")
LITERAL_WIDTH = re.compile(r"\bwidth\s*:\s*(\d+)\b(?![.*\d])")
LITERAL_HEIGHT = re.compile(r"\bheight\s*:\s*(\d+)\b(?!\s*[=:])")
LAYOUT_NO_THEME_SPACING = re.compile(r"spacing\s*:\s*\d+\b")
RESPONSIVE_MARKER = re.compile(
    r"MichiResponsive|breakpointCompact|breakpointRegular|breakpointWide|responsiveWidth"
)

KNOWN_TOKENS = re.compile(
    r"MichiTheme\.spacing\.\w+"
    r"|MichiTheme\.coverSize\w+"
    r"|MichiTheme\.sidebarWidth\w*"
    r"|MichiTheme\.nowPlayingHeight"
    r"|MichiTheme\.headerHeight"
    r"|MichiTheme\.minimumInteractiveSize"
    r"|MichiTheme\.toolbarHeight"
    r"|MichiTheme\.rowHeight\w*"
    r"|MichiTheme\.pageMargin\w*"
)


def scan_file(qml_path):
    violations = []
    try:
        with open(qml_path, encoding="utf-8") as f:
            lines = f.readlines()
    except (OSError, UnicodeDecodeError):
        return violations

    rel = os.path.relpath(qml_path, os.path.dirname(UI_QML))
    has_responsive = False

    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if RESPONSIVE_MARKER.search(stripped):
            has_responsive = True

        if KNOWN_TOKENS.search(stripped):
            continue
        if "import " in stripped or "property " in stripped or "readonly " in stripped:
            continue

        m = LITERAL_MARGIN.search(stripped)
        if m:
            val = int(m.group(1))
            if val > 0:
                violations.append({
                    "file": rel,
                    "line": lineno,
                    "pattern_type": "literal_anchors.margins",
                    "value": val,
                    "detail": stripped.strip()[:80],
                })

        m = LITERAL_ANCHOR_MARGIN.search(stripped)
        if m:
            val = int(m.group(2))
            if val > 0:
                violations.append({
                    "file": rel,
                    "line": lineno,
                    "pattern_type": "literal_anchor_margin",
                    "value": val,
                    "detail": stripped.strip()[:80],
                })

        m = LITERAL_WIDTH.search(stripped)
        if m:
            val = int(m.group(1))
            if val < 300 and val > 10:
                violations.append({
                    "file": rel,
                    "line": lineno,
                    "pattern_type": "literal_fixed_width",
                    "value": val,
                    "detail": stripped.strip()[:80],
                })

        m = LITERAL_HEIGHT.search(stripped)
        if m:
            val = int(m.group(1))
            if val < 200 and val > 10:
                violations.append({
                    "file": rel,
                    "line": lineno,
                    "pattern_type": "literal_fixed_height",
                    "value": val,
                    "detail": stripped.strip()[:80],
                })

        if LAYOUT_NO_THEME_SPACING.search(stripped):
            violations.append({
                "file": rel,
                "line": lineno,
                "pattern_type": "layout_literal_spacing",
                "value": "spacing with literal number",
                "detail": stripped.strip()[:80],
            })

    if not has_responsive:
        violations.insert(0, {
            "file": rel,
            "line": 1,
            "pattern_type": "no_responsive_breakpoint",
            "value": "missing MichiResponsive or breakpoint usage",
            "detail": "page has no breakpoint detection",
        })

    return violations


def main():
    parser = argparse.ArgumentParser(description="Audit QML responsive design compliance")
    parser.add_argument("--format", choices=["json", "text"], default="text")
    parser.add_argument("--baseline", type=str, help="Baseline JSON file for regression detection")
    args = parser.parse_args()

    pages_dir = os.path.join(os.path.abspath(UI_QML), "pages")
    if not os.path.isdir(pages_dir):
        print("[]" if args.format == "json" else "pages/ not found", file=sys.stderr)
        return

    all_violations = []
    for root, _dirs, files in os.walk(pages_dir):
        for f in files:
            if f.endswith(".qml"):
                all_violations.extend(scan_file(os.path.join(root, f)))

    if args.format == "json":
        print(json.dumps(all_violations, indent=2))
    else:
        if not all_violations:
            print("✓ All responsive requirements met.")
        else:
            for v in all_violations:
                print(f"{v['file']}:{v['line']}  [{v['pattern_type']}]  {v['detail']}")

    total = len(all_violations)

    if args.baseline:
        with open(args.baseline) as f:
            baseline = json.load(f)
        baseline_count = len(baseline)
        if total > baseline_count:
            print(f"REGRESSION: {total - baseline_count} new violations (baseline: {baseline_count}, current: {total})", file=sys.stderr)
            sys.exit(1)
        else:
            print(f"OK: {total} violations (baseline: {baseline_count})")
            sys.exit(0)

    if args.format == "text" and total:
        print(f"\nTotal: {total} violations found", file=sys.stderr)
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
