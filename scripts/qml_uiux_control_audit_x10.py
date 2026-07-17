#!/usr/bin/env python3
"""Audit QML controls for required attributes (objectName, accessibility, states)."""

import argparse
import json
import os
import re
import sys
from collections import Counter

UI_QML = os.path.join(os.path.dirname(__file__), "..", "ui_qml")

CONTROL_TYPES = [
    "Button", "Slider", "ComboBox", "TextField", "TextArea",
    "SpinBox", "Switch", "CheckBox", "RadioButton", "Dial",
    "ProgressBar", "RangeSlider", "Tumbler", "DelayButton",
    "TabButton", "ToolButton", "MenuButton", "RoundButton",
    "ItemDelegate", "LabelDelegate",
    "MichiButton", "MichiIconButton", "MichiSlider", "MichiProgressBar",
]

CONTROL_PATTERN = re.compile(r"^\s*(" + "|".join(re.escape(c) for c in CONTROL_TYPES) + r")\s*\{?")

OBJECT_NAME_RE = re.compile(r"objectName\s*:\s*[\"']([^\"']+)[\"']")
ACCESSIBLE_ROLE_RE = re.compile(r"Accessible\.role")
ACCESSIBLE_NAME_RE = re.compile(r"Accessible\.name")
HOVER_RE = re.compile(r"\bhover(ed|Active)\b|hovered\s*\{")
PRESSED_RE = re.compile(r"\bpress(ed|Active)\b|pressed\s*\{|\.down\b")
FOCUS_RE = re.compile(r"\bfocus\b|activeFocus\b|focused\s*\{")
DISABLED_RE = re.compile(r"\benabled\s*:\s*false|!.*\.enabled\b|disabled\s*\{")


def scan_file(qml_path):
    findings = []
    try:
        with open(qml_path, encoding="utf-8") as f:
            lines = f.readlines()
    except (OSError, UnicodeDecodeError):
        return findings

    rel = os.path.relpath(qml_path, os.path.dirname(UI_QML))
    block_start = None
    current_type = None
    brace_depth = 0
    block_text = ""

    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()

        m = CONTROL_PATTERN.match(stripped)
        if m:
            if current_type is not None:
                findings.extend(_analyze_block(rel, block_start, current_type, block_text))
            current_type = m.group(1)
            block_start = lineno
            block_text = line
            brace_depth = stripped.count("{") - stripped.count("}")
            if brace_depth < 0:
                brace_depth = 0
            continue

        if current_type is not None:
            block_text += line
            brace_depth += stripped.count("{") - stripped.count("}")
            if brace_depth <= 0 and "{" in stripped:
                findings.extend(_analyze_block(rel, block_start, current_type, block_text))
                current_type = None
                block_text = ""

    if current_type is not None:
        findings.extend(_analyze_block(rel, block_start, current_type, block_text))

    return findings


def _analyze_block(rel, lineno, ctype, text):
    missing = []
    if not OBJECT_NAME_RE.search(text):
        missing.append("objectName")
    if not ACCESSIBLE_ROLE_RE.search(text):
        missing.append("Accessible.role")
    if not ACCESSIBLE_NAME_RE.search(text):
        missing.append("Accessible.name")
    if not HOVER_RE.search(text):
        missing.append("hover_state")
    if not PRESSED_RE.search(text):
        missing.append("pressed_state")
    if not FOCUS_RE.search(text):
        missing.append("focus_state")
    if not DISABLED_RE.search(text):
        missing.append("disabled_state")

    if missing:
        return [{
            "file": rel,
            "control": ctype,
            "line": lineno,
            "missing": missing,
        }]
    return []


def main():
    parser = argparse.ArgumentParser(description="Audit QML controls for required attributes")
    parser.add_argument("--format", choices=["json", "text"], default="text")
    parser.add_argument("--baseline", type=str, help="Baseline JSON file for regression detection")
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
            print("✓ All controls have required attributes.")
        else:
            for f in all_findings:
                print(
                    f"{f['file']}:{f['line']}  "
                    f"{f['control']}  missing: {', '.join(f['missing'])}"
                )

    total = len(all_findings)

    if args.baseline:
        with open(args.baseline) as f:
            baseline_data = json.load(f)
        baseline_fp = baseline_data.get("fingerprints", {})
        current_fp = Counter()
        for v in all_findings:
            key = f"{v['file']}:{v['control']}:{','.join(v.get('missing', []))}"
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
