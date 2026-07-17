#!/usr/bin/env python3
"""Audit objectName conventions, duplicates, and missing objectNames."""

import argparse
import json
import os
import re
import sys
from collections import Counter

UI_QML = os.path.join(os.path.dirname(__file__), "..", "ui_qml")

OBJECT_NAME_RE = re.compile(r"objectName\s*:\s*[\"']([^\"']+)[\"']")

CONTROL_TYPES = [
    "Button", "Slider", "ComboBox", "TextField", "TextArea",
    "SpinBox", "Switch", "CheckBox", "RadioButton", "Dial",
    "ProgressBar", "RangeSlider", "Tumbler", "DelayButton",
    "TabButton", "ToolButton", "MenuButton", "RoundButton",
    "ItemDelegate", "LabelDelegate",
    "MichiButton", "MichiIconButton", "MichiSlider", "MichiProgressBar",
    "MichiDoubleSpinBox",
]
CONTROL_PATTERN = re.compile(r"^\s*(" + "|".join(re.escape(c) for c in CONTROL_TYPES) + r")\s*\{?")

CONVENTION_RE = re.compile(r"^[a-z]+\.[a-z]+\.[a-zA-Z]+$")


def convention_violation(name):
    return name and not CONVENTION_RE.match(name)


def scan_files(base_dir, findings, name_map, control_no_name):
    for root, _dirs, files in os.walk(base_dir):
        for f in files:
            if not f.endswith(".qml"):
                continue
            path = os.path.join(root, f)
            rel = os.path.relpath(path, os.path.dirname(UI_QML))
            try:
                with open(path, encoding="utf-8") as fh:
                    lines = fh.readlines()
            except (OSError, UnicodeDecodeError):
                continue

            for lineno, line in enumerate(lines, 1):
                m = OBJECT_NAME_RE.search(line)
                if m:
                    name = m.group(1)
                    if convention_violation(name):
                        findings.append({
                            "type": "convention_violation",
                            "file": rel,
                            "line": lineno,
                            "objectName": name,
                            "expected": "page.section.control",
                        })
                    if name in name_map:
                        prev = name_map[name]
                        if prev["file"] != rel:
                            findings.append({
                                "type": "duplicate_objectName",
                                "file": rel,
                                "line": lineno,
                                "objectName": name,
                                "also_in": prev["file"],
                            })
                    else:
                        name_map[name] = {"file": rel, "line": lineno}

            control_blocks = _find_control_blocks(path, lines)
            for cb in control_blocks:
                has_on = OBJECT_NAME_RE.search(cb["text"])
                if not has_on:
                    control_no_name.append({
                        "file": rel,
                        "line": cb["line"],
                        "control": cb["type"],
                    })


def _find_control_blocks(path, lines):
    blocks = []
    for lineno, line in enumerate(lines, 1):
        m = CONTROL_PATTERN.match(line)
        if m:
            blocks.append({"type": m.group(1), "line": lineno, "text": line})
    return blocks


def main():
    parser = argparse.ArgumentParser(description="Audit objectName conventions, duplicates, and missing")
    parser.add_argument("--format", choices=["json", "text"], default="text")
    parser.add_argument("--baseline", type=str, help="Baseline JSON file for regression detection")
    args = parser.parse_args()

    base = os.path.abspath(UI_QML)
    pages_dir = os.path.join(base, "pages")
    components_dir = os.path.join(base, "components")

    findings = []
    name_map = {}
    control_no_name = []

    for d in [pages_dir, components_dir]:
        if os.path.isdir(d):
            scan_files(d, findings, name_map, control_no_name)

    report = {
        "convention_violations": [f for f in findings if f["type"] == "convention_violation"],
        "duplicate_objectNames": [f for f in findings if f["type"] == "duplicate_objectName"],
        "controls_without_objectName": control_no_name,
    }

    total = (
        len(report["convention_violations"])
        + len(report["duplicate_objectNames"])
        + len(report["controls_without_objectName"])
    )

    if args.format == "json":
        print(json.dumps(report, indent=2))
    else:
        if total == 0:
            print("✓ All objectNames follow convention, no duplicates, all controls have objectName.")
        else:
            for v in report["convention_violations"]:
                print(f"CONVENTION: {v['file']}:{v['line']}  objectName=\"{v['objectName']}\" (expected {v['expected']})")
            for d in report["duplicate_objectNames"]:
                print(f"DUPLICATE: {d['file']}:{d['line']}  objectName=\"{d['objectName']}\" also in {d['also_in']}")
            for n in report["controls_without_objectName"]:
                print(f"NO_OBJECTNAME: {n['file']}:{n['line']}  {n['control']}")

    if args.baseline:
        with open(args.baseline) as f:
            baseline_data = json.load(f)
        baseline_fp = baseline_data.get("fingerprints", {})
        current_fp = Counter()
        for v in report["convention_violations"]:
            current_fp[f"{v['file']}:convention_violation:{v['objectName']}"] += 1
        for d in report["duplicate_objectNames"]:
            current_fp[f"{d['file']}:duplicate_objectName:{d['objectName']}"] += 1
        for n in report["controls_without_objectName"]:
            current_fp[f"{n['file']}:no_objectName:{n['control']}"] += 1
        new_regressions = False
        for key, count in sorted(current_fp.items()):
            baseline_count = baseline_fp.get(key, 0)
            if count > baseline_count:
                new_regressions = True
                print(f"  REGRESSION: {key} count {count} > baseline {baseline_count}", file=sys.stderr)
        if new_regressions:
            print("REGRESSION DETECTED", file=sys.stderr)
            sys.exit(1)
        else:
            print(f"OK: {sum(current_fp.values())} occurrences ({len(current_fp)} fingerprints, baseline: {len(baseline_fp)})")
            sys.exit(0)

    if args.format == "text" and total:
        print(f"\nTotal: {total} violations found", file=sys.stderr)
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
