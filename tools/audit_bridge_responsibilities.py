#!/usr/bin/env python3
"""Audit bridge responsibilities: SQL, service construction, parallel state.

Scans ui_qml_bridge/*.py and flags three architectural violations
(ADR-001/ADR-003 separation of concerns):

  1. MUTATION SQL in bridges: ``sqlite3.connect`` / ``INSERT INTO`` /
     ``DELETE FROM`` / ``UPDATE <table>`` statements. Read-only SELECT probes
     are allowed (capability_bridge FTS probe is the documented exception).
  2. SERVICE/RESPOSITORY CONSTRUCTION as fallback: ``*Service(...)`` /
     ``*Repository(...)`` constructor calls inside bridge code (bridges must
     receive services via injection, never build their own).
  3. PARALLEL STATE: dict/list attributes named after a registry
     (_history/_cache/_jobs/_active_jobs/_transfer_history/_chat_history/
     _back_stack) that duplicate canonical service state. Bounded performance
     caches, UI-only transcripts and navigation stacks are documented
     exceptions and reported as INFO, not violations.

FAILS (exit 1) when any violation above is found.

Usage:
  python tools/audit_bridge_responsibilities.py
  python tools/audit_bridge_responsibilities.py --json
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

BRIDGE_DIR = HERE / "ui_qml_bridge"

# Read-only probe exceptions: capability_bridge probes FTS5 availability with
# a SELECT against the read connection (no writes, no DDL).
SQL_ALLOWLIST = frozenset({"capability_bridge.py"})

# Documented parallel-state exceptions: (file, attribute) → reason. Every
# entry was verified during the runtime refactor (audit S12):
#   - bounded performance caches (LRU probe/artwork caches)
#   - UI-only transcripts/navigation stacks with no canonical service
#   - worker-task trackers for in-flight WorkerManager tasks (no durable job)
PARALLEL_STATE_ALLOWLIST: dict[tuple[str, str], str] = {
    ("audio_quality_adapter.py", "_cache"):
        "Bounded LRU quality-probe cache (max 200); adapter, not a bridge.",
    ("cover_provider_bridge.py", "_cache"):
        "Bounded LRU artwork cache serving QML; no canonical cache service.",
    ("michi_ai_bridge.py", "_chat_history"):
        "Chat transcript owned by the bridge; engine keeps no transcript.",
    ("navigation_bridge.py", "_back_stack"):
        "UI navigation back-stack (bounded 50); navigation service is route-"
        "state, not a stack store.",
    ("page_state_store.py", "_history"):
        "UI page history (bounded 20); state store by design.",
    ("nowplaying_bridge.py", "_history"):
        "NowPlaying playback history (bounded 50); no canonical persisted "
        "playback-history service.",
    ("nowplaying_bridge.py", "_history_internal_refs"):
        "Internal refs for the NowPlaying history entries.",
    ("devices_bridge.py", "_transfer_history"):
        "Read mirror of device_sync_service.get_history (transfer list UI).",
    ("devices_bridge.py", "_transfer_jobs"):
        "Read mirror of device_sync_service.list_jobs() for the transfer "
        "list UI (refresh-driven; canonical state lives in the service).",
    ("audio_lab_bridge.py", "_active_jobs"):
        "In-flight WorkerManager task tracker (analysis/conversion); "
        "job_service used only for cancel; no durable jobs in this domain.",
    ("conversion_bridge.py", "_jobs"):
        "Conversion jobs owned by the bridge (QProcess conversions; no "
        "container conversion service).",
    ("diagnostics_bridge.py", "_jobs"):
        "Result list of worker submissions for the diagnostics report view.",
}

# Attribute suffixes that identify registry-like state.
_PARALLEL_STATE_RE = re.compile(
    r"^(active_)?(chat_|transfer_|back_|page_)?(history|cache|jobs|stack)$"
)

_MUTATION_SQL_RE = re.compile(
    r"sqlite3\.connect\s*\(|"
    r"\bINSERT\s+INTO\b|\bDELETE\s+FROM\b|\bUPDATE\s+\w+\s+SET\b",
    re.IGNORECASE,
)


def _find_bridge_classes(tree: ast.Module) -> list[ast.ClassDef]:
    return [
        node for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
    ]


def scan_file(path: Path) -> dict:
    source = path.read_text(encoding="utf-8", errors="ignore")
    findings: dict = {"sql": [], "construction": [], "parallel_state": []}

    # 1. Mutation SQL (text scan; SELECT-only probes are read-only).
    if path.name not in SQL_ALLOWLIST:
        for lineno, line in enumerate(source.splitlines(), start=1):
            if _MUTATION_SQL_RE.search(line):
                if "select" in line.lower() and "into" not in line.lower():
                    continue
                findings["sql"].append(f"{lineno}: {line.strip()[:100]}")

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return findings

    # 2. Service/repository construction as fallback.
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = None
        if isinstance(func, ast.Name):
            name = func.id
        elif isinstance(func, ast.Attribute):
            name = func.attr
        if not name:
            continue
        if (name.endswith("Service") or name.endswith("Repository")) \
                and name not in ("Service",) \
                and isinstance(func, ast.Name) and func.id == name:
            findings["construction"].append(
                f"{node.lineno}: {name}(...) constructed in bridge"
            )

    # 3. Parallel state: registry-like dict/list attributes.
    for klass in _find_bridge_classes(tree):
        for node in ast.walk(klass):
            if not isinstance(node, ast.FunctionDef):
                continue
            if node.name != "__init__":
                continue
            for stmt in ast.walk(node):
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.value, ast.expr):
                    stmt = ast.Assign(
                        targets=[stmt.target],
                        value=stmt.value,
                        lineno=stmt.lineno,
                    )
                if not isinstance(stmt, ast.Assign) or len(stmt.targets) != 1:
                    continue
                target = stmt.targets[0]
                if not isinstance(target, ast.Attribute):
                    continue
                if not target.attr.startswith("_"):
                    continue
                suffix = target.attr.lstrip("_")
                if not _PARALLEL_STATE_RE.match(suffix):
                    continue
                value = stmt.value
                if not isinstance(value, (ast.Dict, ast.List, ast.Call)):
                    continue
                if isinstance(value, ast.Call) \
                        and not (isinstance(value.func, ast.Name)
                                 and value.func.id in ("dict", "list", "OrderedDict")):
                    continue
                allow = PARALLEL_STATE_ALLOWLIST.get((path.name, target.attr))
                findings["parallel_state"].append({
                    "lineno": stmt.lineno,
                    "attr": target.attr,
                    "kind": "documented_exception" if allow else "violation",
                    "reason": allow or "undocumented parallel registry",
                })
    return findings


def audit() -> dict:
    sql_violations: list[str] = []
    construction_violations: list[str] = []
    parallel_violations: list[dict] = []
    parallel_info: list[dict] = []
    for path in sorted(BRIDGE_DIR.glob("*.py")):
        if path.name == "bridge_factory.py":
            continue
        findings = scan_file(path)
        for item in findings["sql"]:
            sql_violations.append(f"{path.name}:{item}")
        for item in findings["construction"]:
            construction_violations.append(f"{path.name}:{item}")
        for item in findings["parallel_state"]:
            row = {"file": path.name, **item}
            if item["kind"] == "violation":
                parallel_violations.append(row)
            else:
                parallel_info.append(row)
    return {
        "generated_by": "tools/audit_bridge_responsibilities.py",
        "bridges_scanned": len(list(BRIDGE_DIR.glob("*.py"))) - 1,
        "sql_violations": sql_violations,
        "construction_violations": construction_violations,
        "parallel_state_violations": parallel_violations,
        "parallel_state_documented": parallel_info,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Dump JSON report")
    args = parser.parse_args()

    report = audit()
    if args.json:
        print(json.dumps(report, indent=2))
        return 0 if not (report["sql_violations"]
                         or report["construction_violations"]
                         or report["parallel_state_violations"]) else 1

    print(f"Bridges scanned: {report['bridges_scanned']}")
    for section, label in (
        ("sql_violations", "Mutation SQL in bridges"),
        ("construction_violations", "Service/repository construction in bridges"),
        ("parallel_state_violations", "Parallel state registries in bridges"),
    ):
        items = report[section]
        print(f"{label}: {len(items)}")
        for item in items:
            print(f"  - {item}")
    print("Documented parallel-state exceptions (INFO): "
          f"{len(report['parallel_state_documented'])}")
    for item in report["parallel_state_documented"]:
        print(f"  - {item['file']}:{item['lineno']} {item['attr']} — "
              f"{item['reason']}")

    if report["sql_violations"] or report["construction_violations"] \
            or report["parallel_state_violations"]:
        print("FAIL: bridge responsibility violations found.")
        return 1
    print("OK: no bridge responsibility violations (no mutation SQL, no "
          "service construction, no undocumented parallel state).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
