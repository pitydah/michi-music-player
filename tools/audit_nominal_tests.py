#!/usr/bin/env python3
"""Audit nominal tests in tests/architecture/ and tests/integration/.

FASE 11 (P0 stabilization) — debt report, NEVER a CI failure (exit 0
always). Flags test functions whose assertions only check:

  - TEXT EXISTENCE: ``assert "x" in source`` (a literal membership test,
    often against a read file/source string — no behavioral link).
  - METHOD NAME: ``assert hasattr(obj, "name")`` without exercising behavior.
  - FIXED COUNTS: ``assert len(x) == N`` against a literal N with no
    semantic derivation (e.g. comparing to another computed value is NOT
    flagged).
  - IMPORTABILITY: test functions with no assertions at all (import
    succeeds = pass).
  - ``assert result is not None`` as the only meaningful check.

Report: per-pattern counts + the flagged list. WARNING only — the mandate
says these tests are to be MARKED (debt), not failed.

Usage:
  python tools/audit_nominal_tests.py
  python tools/audit_nominal_tests.py --json
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent

SCAN_DIRS = ("architecture", "integration")


def _analyze_function(fn: ast.FunctionDef, source: str) -> list[str]:
    """Nominal-test pattern names found in one test function."""
    weak: list[str] = []
    asserts = [s for s in ast.walk(fn) if isinstance(s, ast.Assert)]
    for stmt in asserts:
        test = stmt.test
        # Text existence: assert "literal" in <anything>
        if isinstance(test, ast.Compare) and test.ops \
                and isinstance(test.ops[0], ast.In) \
                and isinstance(test.left, ast.Constant) \
                and isinstance(test.left.value, str):
            weak.append(f"text-existence@L{stmt.lineno}")
            continue
        # hasattr-only: assert hasattr(x, 'name')
        if isinstance(test, ast.Call) and isinstance(test.func, ast.Name) \
                and test.func.id == "hasattr":
            weak.append(f"hasattr-only@L{stmt.lineno}")
            continue
        # assert result is not None
        if isinstance(test, ast.Compare) and len(test.ops) == 1 \
                and isinstance(test.ops[0], ast.IsNot) \
                and isinstance(test.comparators[0], ast.Constant) \
                and test.comparators[0].value is None:
            weak.append(f"is-not-None@L{stmt.lineno}")
            continue
        # Fixed counts: assert len(x) <op> <literal>
        if isinstance(test, ast.Compare):
            for op, comp in zip(test.ops, test.comparators, strict=False):
                if isinstance(op, (ast.Eq, ast.Gt, ast.GtE, ast.Lt, ast.LtE)) \
                        and isinstance(comp, ast.Constant) \
                        and isinstance(comp.value, (int, float)):
                    left = test.left
                    if isinstance(left, ast.Call) and isinstance(left.func, ast.Name) \
                            and left.func.id == "len":
                        weak.append(f"fixed-count@L{stmt.lineno}")
                        break
    if not asserts:
        weak.append("no-assertions")
    return weak


def audit() -> dict:
    flagged: list[dict] = []
    counts: dict[str, int] = {
        "text-existence": 0,
        "hasattr-only": 0,
        "fixed-count": 0,
        "no-assertions": 0,
        "is-not-None": 0,
    }
    files_scanned = 0
    functions_scanned = 0
    for directory in SCAN_DIRS:
        base = HERE / "tests" / directory
        if not base.exists():
            continue
        for path in sorted(base.rglob("test_*.py")):
            if "__pycache__" in path.parts:
                continue
            files_scanned += 1
            try:
                source_text = path.read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(source_text)
            except (SyntaxError, OSError):
                continue
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                        or not node.name.startswith("test_"):
                    continue
                functions_scanned += 1
                patterns = _analyze_function(node, source_text)
                if not patterns:
                    continue
                for pattern in patterns:
                    name = pattern.split("@")[0]
                    if name in counts:
                        counts[name] += 1
                flagged.append({
                    "file": f"{path.relative_to(HERE).as_posix()}::{node.name}",
                    "patterns": patterns,
                })
    return {
        "generated_by": "tools/audit_nominal_tests.py",
        "files_scanned": files_scanned,
        "functions_scanned": functions_scanned,
        "flagged_functions": len(flagged),
        "pattern_counts": counts,
        "flagged": flagged,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Dump JSON report")
    args = parser.parse_args()

    report = audit()
    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    print(f"Files scanned: {report['files_scanned']} | test functions: "
          f"{report['functions_scanned']} | flagged (nominal patterns): "
          f"{report['flagged_functions']}")
    for pattern, count in report["pattern_counts"].items():
        print(f"  {pattern}: {count}")
    print("Flagged tests (debt report — warning only, never a CI failure):")
    for row in report["flagged"]:
        print(f"  - {row['file']}: {row['patterns']}")
    print("OK: nominal-test debt report (exit 0 by design — F11 mandate H).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
