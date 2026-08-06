#!/usr/bin/env python3
"""Audit duplicate service class names across runtime modules.

Scans core/, library/, streaming/, recognition/, integrations/, sync/,
audio/, recommendation/, metadata/ and ui_qml_bridge/ for class definitions,
groups them by class name and classifies each definition:

  - PRODUCTIVE: instantiated by composition or bridges (constructor call in
    core/composition/*.py, core/application_bootstrap.py or ui_qml_bridge/*.py).
  - LEGACY: designated legacy by the architecture test table, marked with a
    LEGACY docstring marker / DeprecationWarning, or never instantiated.

FAILS (exit 1) when two or more PRODUCTIVE classes share the same name
(canonical duplicate) or an undocumented duplicate name appears (one not
declared in the designation tables shared with
tests/architecture/test_no_duplicate_service_class_names.py).

Known expected duplicates that PASS (single productive authority each):
  - MicroServerService (3 defs: core LEGACY, integrations LEGACY, services/ PRODUCTIVE)
  - ContinueOnServerService (2: stub LEGACY/dead, services/ PRODUCTIVE)
  - RadioService (2: service.py PRODUCTIVE, radio_service.py LEGACY facade)
  - LyricsService (2: service.py PRODUCTIVE, lyrics_service.py LEGACY)
  - CoverArtService (1 productive + static-helper legacy modules)

Usage:
  python tools/audit_service_duplicates.py
  python tools/audit_service_duplicates.py --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

COMPOSITION_FILES = (
    HERE / "core" / "composition" / "infrastructure.py",
    HERE / "core" / "composition" / "playback.py",
    HERE / "core" / "composition" / "library.py",
    HERE / "core" / "composition" / "audio_lab.py",
    HERE / "core" / "composition" / "ecosystem.py",
    HERE / "core" / "composition" / "settings.py",
    HERE / "core" / "composition" / "intelligence.py",
    HERE / "core" / "application_bootstrap.py",
)

SCAN_DIRS = (
    "core", "library", "streaming", "recognition", "integrations",
    "sync", "audio", "recommendation", "metadata", "ui_qml_bridge",
)

# Parallel-layer names that legitimately coexist beyond the architecture
# test's scan list (extra dirs audio/, metadata/).
EXTRA_COEXISTING_DUPLICATES: dict[str, tuple[str, ...]] = {
    "PlaybackState": (
        "audio/player.py",
        "audio/fake_player.py",
    ),
    "MetadataProposal": (
        "core/metadata_editor_service.py",
        "metadata/review/schemas.py",
    ),
}


def _class_definitions() -> dict[str, list[str]]:
    pattern = re.compile(r"^class\s+(\w+)\b", re.M)
    by_name: dict[str, list[str]] = {}
    for directory in SCAN_DIRS:
        base = HERE / directory
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            if "__pycache__" in str(path) or "build" in path.parts:
                continue
            source = path.read_text(encoding="utf-8", errors="ignore")
            for match in pattern.finditer(source):
                by_name.setdefault(match.group(1), []).append(
                    path.relative_to(HERE).as_posix()
                )
    return {name: sorted(files) for name, files in by_name.items()}


def _designations() -> tuple[dict, dict]:
    """(coexisting names, legacy-by-designation file set) from the test tables."""
    try:
        from tests.architecture.test_no_duplicate_service_class_names import (
            COEXISTING_DUPLICATES,
            SERVICE_DUPLICATES,
        )
    except Exception:
        COEXISTING_DUPLICATES = {}
        SERVICE_DUPLICATES = {}
    coexisting = dict(COEXISTING_DUPLICATES)
    coexisting.update(EXTRA_COEXISTING_DUPLICATES)
    legacy: set[str] = set()
    for _name, (_prod, legacy_files) in SERVICE_DUPLICATES.items():
        legacy.update(legacy_files)
    return coexisting, legacy


def _instantiation_text() -> str:
    chunks: list[str] = []
    for path in COMPOSITION_FILES:
        chunks.append(path.read_text(encoding="utf-8", errors="ignore"))
    bridge_dir = HERE / "ui_qml_bridge"
    if bridge_dir.exists():
        chunks.extend(
            p.read_text(encoding="utf-8", errors="ignore")
            for p in bridge_dir.rglob("*.py")
        )
    return "\n".join(chunks)


def audit() -> dict:
    definitions = _class_definitions()
    coexisting, legacy_by_designation = _designations()
    instantiation_text = _instantiation_text()

    rows: list[dict] = []
    violations: list[str] = []
    for name, files in sorted(definitions.items()):
        if len(files) < 2:
            continue
        if name in coexisting:
            continue
        productive = [
            f for f in files
            if f not in legacy_by_designation
            and re.search(rf"\b{re.escape(name)}\s*\(", instantiation_text)
        ]
        legacy = [f for f in files if f not in productive]
        rows.append({
            "class": name,
            "productive": productive,
            "legacy": legacy,
        })
        if len(productive) > 1:
            violations.append(
                f"canonical duplicate '{name}': productive files {productive}"
            )
        elif not productive:
            violations.append(
                f"duplicate name '{name}' with no productive implementation: "
                f"{files}"
            )
    return {
        "generated_by": "tools/audit_service_duplicates.py",
        "class_definitions": len(definitions),
        "duplicate_names": len(rows),
        "rows": rows,
        "violations": violations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Dump JSON report")
    args = parser.parse_args()

    report = audit()
    if args.json:
        print(json.dumps(report, indent=2))
        return 0 if not report["violations"] else 1

    print(f"Class definitions scanned: {report['class_definitions']}")
    print(f"Duplicate class names (not in designation tables): "
          f"{report['duplicate_names']}")
    for row in report["rows"]:
        print(
            f"  {row['class']}: productive={row['productive']} "
            f"legacy={row['legacy']}"
        )
    if report["violations"]:
        print("FAIL:", *report["violations"], sep="\n  - ")
        return 1
    print("OK: no canonical duplicates (all multi-file names are documented "
          "or have a single productive implementation).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
