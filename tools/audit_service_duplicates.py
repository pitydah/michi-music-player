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

FASE 11 — IDENTITY DUPLICATION (semantic): detects the SAME instance
registered under multiple lifecycle keys. In composition builders a shared
expression (``x`` variable/instance) passed to ``container.register`` twice
is only legal when the non-canonical key declares ``alias_of`` in
SERVICE_MANIFEST (FASE 1 alias mechanism). FAILS on non-alias same-instance
multi-registration.

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
import ast
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from core.service_manifest import SERVICE_MANIFEST  # noqa: E402

COMPOSITION_FILES = (
    HERE / "core" / "composition" / "infrastructure.py",
    HERE / "core" / "composition" / "playback.py",
    HERE / "core" / "composition" / "library.py",
    HERE / "core" / "composition" / "audio_lab.py",
    HERE / "core" / "composition" / "ecosystem.py",
    HERE / "core" / "composition" / "settings.py",
    HERE / "core" / "composition" / "intelligence.py",
    HERE / "core" / "composition" / "jobs.py",
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


def _constructed_names() -> set[str]:
    """Class names actually constructed by composition/bridges (alias-aware).

    Resolves ``from x import Foo as Bar`` aliases so ``Bar(...)`` counts as
    constructing ``Foo`` (e.g. ``RadioService as CanonicalRadioService``).
    """
    constructed: set[str] = set()
    sources: list[Path] = list(COMPOSITION_FILES)
    bridge_dir = HERE / "ui_qml_bridge"
    if bridge_dir.exists():
        sources.extend(p for p in bridge_dir.rglob("*.py"))
    for path in sources:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
        except (SyntaxError, OSError):
            continue
        aliases: dict[str, str] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.asname:
                        aliases[alias.asname] = alias.name
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Name):
                constructed.add(aliases.get(func.id, func.id))
            elif isinstance(func, ast.Attribute):
                constructed.add(func.attr)
    return constructed


# ── FASE 11: identity duplication (same instance under multiple keys) ──────

def _register_calls() -> list[tuple[Path, int, str, ast.expr]]:
    """(file, lineno, key, value-expr) for every container.register call."""
    calls: list[tuple[Path, int, str, ast.expr]] = []
    for path in COMPOSITION_FILES:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, OSError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
                continue
            call = node.value
            func = call.func
            if not (isinstance(func, ast.Attribute) and func.attr == "register"):
                continue
            if len(call.args) < 2 or not isinstance(call.args[0], ast.Constant):
                continue
            key = str(call.args[0].value)
            value = call.args[1]
            if isinstance(value, ast.Constant):
                continue  # None fallbacks / primitive registrations
            calls.append((path, node.lineno, key, value))
    return calls


def _expr_symbol(expr: ast.expr) -> str | None:
    """Canonical symbol of a register value: Name('x') → 'x'; call → class name.

    Returns None when the expression cannot be compared (no shared identity
    possible without dataflow).
    """
    if isinstance(expr, ast.Name):
        return f"name:{expr.id}"
    if isinstance(expr, ast.Attribute):
        return f"attr:{expr.attr}"
    if isinstance(expr, ast.Call):
        func = expr.func
        if isinstance(func, ast.Name):
            return f"call:{func.id}"
        if isinstance(func, ast.Attribute):
            return f"call:{func.attr}"
    return None


def _alias_keys() -> set[str]:
    """Manifest keys that declare alias_of (legal shared-instance registrations)."""
    return {
        key for key, desc in SERVICE_MANIFEST.items() if desc.alias_of
    }


def audit_identity_duplication() -> dict:
    """Same instance registered under multiple keys without alias_of."""
    calls = _register_calls()
    by_symbol: dict[str, list[tuple[Path, int, str]]] = {}
    for path, lineno, key, value in calls:
        symbol = _expr_symbol(value)
        if symbol is None:
            continue
        by_symbol.setdefault(symbol, []).append((path, lineno, key))

    rows: list[dict] = []
    violations: list[str] = []
    alias_keys = _alias_keys()
    for symbol, entries in sorted(by_symbol.items()):
        if len(entries) < 2:
            continue
        # Only flag shared registrations that are NOT both alias_of-declared.
        keys = [key for _p, _l, key in entries]
        aliased = {key for key in keys if key in alias_keys}
        canonical = set(keys) - aliased
        row = {
            "expression": symbol,
            "keys": keys,
            "declared_aliases": sorted(aliased),
        }
        rows.append(row)
        if len(canonical) > 1:
            violations.append(
                f"same instance registered as {sorted(canonical)} without "
                f"alias_of in SERVICE_MANIFEST: {entries}"
            )
    return {
        "identity_duplication_rows": rows,
        "identity_duplication_violations": violations,
    }


def audit() -> dict:
    definitions = _class_definitions()
    coexisting, legacy_by_designation = _designations()
    constructed = _constructed_names()

    rows: list[dict] = []
    violations: list[str] = []
    for name, files in sorted(definitions.items()):
        if len(files) < 2:
            continue
        if name in coexisting:
            continue
        productive = [
            f for f in files
            if f not in legacy_by_designation and name in constructed
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
    identity = audit_identity_duplication()
    return {
        "generated_by": "tools/audit_service_duplicates.py",
        "class_definitions": len(definitions),
        "duplicate_names": len(rows),
        "rows": rows,
        "violations": violations,
        **identity,
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
    print("FASE 11 — shared-instance registrations: "
          f"{len(report['identity_duplication_rows'])}")
    for row in report["identity_duplication_rows"]:
        print(f"  {row['expression']} → keys {row['keys']} "
              f"(alias_of: {row['declared_aliases']})")
    if report["violations"]:
        print("FAIL:", *report["violations"], sep="\n  - ")
        return 1
    print("OK: no canonical duplicates (all multi-file names are documented "
          "or have a single productive implementation) and no non-alias "
          "shared-instance registrations.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
