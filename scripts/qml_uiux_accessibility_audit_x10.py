#!/usr/bin/env python3
"""Audit QML pages for accessibility requirements."""

import argparse
import json
import os
import re
import sys
from collections import Counter

UI_QML = os.path.join(os.path.dirname(__file__), "..", "ui_qml")

ROOT_PATTERN = re.compile(r"^\s*(Item|Page|Pane|Rectangle|FocusScope|Flickable|Column|Row|Grid)\s*\{?")
ACCESSIBLE_ROLE_RE = re.compile(r"Accessible\.role")
ACCESSIBLE_NAME_RE = re.compile(r"Accessible\.name")
BUTTON_RE = re.compile(r"^\s*(Button|MichiButton|MichiIconButton)\s*\{?")
SLIDER_RE = re.compile(r"^\s*(Slider|MichiSlider)\s*\{?")
DIALOG_RE = re.compile(r"^\s*Dialog\s*\{?")
LIST_GRID_RE = re.compile(r"^\s*(ListView|GridView)\s*\{?")
KEY_NAV_RE = re.compile(r"Keys\.on|KeyNavigation")


def scan_file(qml_path):
    violations = []
    try:
        with open(qml_path, encoding="utf-8") as f:
            lines = f.readlines()
    except (OSError, UnicodeDecodeError):
        return violations

    rel = os.path.relpath(qml_path, os.path.dirname(UI_QML))
    found_root_role = False
    found_root_name = False
    first_non_import = True

    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()

        if first_non_import and ("import " in stripped or not stripped):
            continue
        first_non_import = False

        if ROOT_PATTERN.match(stripped) and not found_root_role:
            scope_content = []
            depth = 0
            for i in range(lineno - 1, min(lineno + 15, len(lines))):
                line_content = lines[i]
                scope_content.append(line_content)
                depth += line_content.count("{") - line_content.count("}")
                if depth <= 0 and i > lineno - 1:
                    break
            scope_text = "".join(scope_content)

            if ACCESSIBLE_ROLE_RE.search(scope_text):
                found_root_role = True
            if ACCESSIBLE_NAME_RE.search(scope_text):
                found_root_name = True
            if not found_root_role:
                violations.append({
                    "file": rel,
                    "line": lineno,
                    "control": "Page/Root",
                    "issue": "missing Accessible.role on root",
                })
            if not found_root_name:
                violations.append({
                    "file": rel,
                    "line": lineno,
                    "control": "Page/Root",
                    "issue": "missing Accessible.name on root",
                })

        if BUTTON_RE.match(stripped):
            block = _collect_block(lines, lineno)
            if not ACCESSIBLE_ROLE_RE.search(block):
                violations.append({
                    "file": rel,
                    "line": lineno,
                    "control": "Button",
                    "issue": "missing Accessible.role Button",
                })
            if not ACCESSIBLE_NAME_RE.search(block):
                violations.append({
                    "file": rel,
                    "line": lineno,
                    "control": "Button",
                    "issue": "missing Accessible.name",
                })

        if SLIDER_RE.match(stripped):
            block = _collect_block(lines, lineno)
            if not ACCESSIBLE_ROLE_RE.search(block):
                violations.append({
                    "file": rel,
                    "line": lineno,
                    "control": "Slider",
                    "issue": "missing Accessible.role Slider",
                })
            if not ACCESSIBLE_NAME_RE.search(block):
                violations.append({
                    "file": rel,
                    "line": lineno,
                    "control": "Slider",
                    "issue": "missing Accessible.name",
                })

        if DIALOG_RE.match(stripped):
            block = _collect_block(lines, lineno)
            if not ACCESSIBLE_ROLE_RE.search(block):
                violations.append({
                    "file": rel,
                    "line": lineno,
                    "control": "Dialog",
                    "issue": "missing Accessible.role Dialog",
                })

        if LIST_GRID_RE.match(stripped):
            block = _collect_block(lines, lineno)
            if not KEY_NAV_RE.search(block):
                violations.append({
                    "file": rel,
                    "line": lineno,
                    "control": "ListView/GridView",
                    "issue": "missing keyboard navigation (Keys.on/KeyNavigation)",
                })

    return violations


def _collect_block(lines, start, max_lines=30):
    block = ""
    depth = 0
    for i in range(start - 1, min(start + max_lines, len(lines))):
        line_content = lines[i]
        block += line_content
        depth += line_content.count("{") - line_content.count("}")
        if depth <= 0 and i > start - 1:
            break
    return block


def main():
    parser = argparse.ArgumentParser(description="Audit QML accessibility requirements")
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
            print("✓ All accessibility requirements met.")
        else:
            for v in all_violations:
                print(f"{v['file']}:{v['line']}  {v['control']}  {v['issue']}")

    total = len(all_violations)

    if args.baseline:
        with open(args.baseline) as f:
            baseline_data = json.load(f)
        baseline_fp = baseline_data.get("fingerprints", {})
        current_fp = Counter()
        for v in all_violations:
            key = f"{v['file']}:{v['control']}:{v.get('issue', '')}"
            current_fp[key] += 1
        new_regressions = False
        for key, count in sorted(current_fp.items()):
            baseline_count = baseline_fp.get(key, 0)
            if count > baseline_count:
                new_regressions = True
                print(f"  REGRESSION: {key} count {count} > baseline {baseline_count}", file=sys.stderr)
        if new_regressions:
            print(f"REGRESSION DETECTED", file=sys.stderr)
            sys.exit(1)
        else:
            print(f"OK: {sum(current_fp.values())} occurrences ({len(current_fp)} fingerprints, baseline: {len(baseline_fp)})")
            sys.exit(0)

    if args.format == "text" and total:
        print(f"\nTotal: {total} violations found", file=sys.stderr)
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
