#!/usr/bin/env python3
"""QML Compile-All v11 — loads every .qml file as QQmlComponent and reports status.

Usage:
    QT_QPA_PLATFORM=offscreen python scripts/qml_compile_all_v11.py 2>&1 | tail -10

Gate: 100% loaded, Errors = 0.
"""
import sys
import time
import argparse
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine


REPO = Path(__file__).resolve().parent.parent
QML_DIR = REPO / "ui_qml"

COMPONENT_TIMEOUT = 10

DEPENDENCY_KEYWORDS = [
    "module", "is not installed", "Circular dependency",
    "is not a type", "is not found",
]
SYNTAX_KEYWORDS = [
    "Expected token", "Unexpected token", "Syntax error",
    "invalid version", "Duplicate property name", "Duplicate signal name",
    "ID undefined", "not available in scope",
]


def _categorise_error(msg: str) -> str:
    for kw in DEPENDENCY_KEYWORDS:
        if kw in msg:
            return "dependencia_ausente"
    for kw in SYNTAX_KEYWORDS:
        if kw in msg:
            return "sintaxis_rota"
    if "ReferenceError" in msg:
        return "reference_error"
    if "TypeError" in msg:
        return "type_error"
    return "other"


def _wait_ready(component, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        s = component.status()
        if s != QQmlComponent.Loading:
            return s
        QCoreApplication.processEvents()
    return QQmlComponent.Loading


def run():
    if not QCoreApplication.instance():
        QCoreApplication(sys.argv)

    engine = QQmlEngine()
    engine.addImportPath(str(QML_DIR))

    qml_files = sorted(QML_DIR.rglob("*.qml"))
    total = len(qml_files)
    loaded = 0
    errors = []
    warnings = []

    for f in qml_files:
        rel = f.relative_to(REPO)
        component = QQmlComponent(engine)
        component.loadUrl(QUrl.fromLocalFile(str(f)))

        status = _wait_ready(component, COMPONENT_TIMEOUT)

        if status == QQmlComponent.Ready:
            loaded += 1
            continue

        if status == QQmlComponent.Loading:
            warnings.append({
                "file": str(rel),
                "type": "timeout",
                "errors": ["Timed out while loading component"],
            })
            continue

        err_list = component.errors()
        err_strs = [str(e) for e in err_list]

        categories = set()
        for es in err_strs:
            cat = _categorise_error(es)
            categories.add(cat)

        entry = {
            "file": str(rel),
            "status": "Error",
            "errors": err_strs,
            "categories": list(categories),
        }

        if status == QQmlComponent.Error:
            errors.append(entry)
        else:
            warnings.append({
                "file": str(rel),
                "type": "unknown",
                "errors": err_strs,
            })

    summary = {
        "total": total,
        "loaded": loaded,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "dependencia_ausente": sum(1 for e in errors if "dependencia_ausente" in e["categories"]),
        "sintaxis_rota": sum(1 for e in errors if "sintaxis_rota" in e["categories"]),
    }

    return {
        "total": total,
        "loaded": loaded,
        "errors": errors,
        "warnings": warnings,
        "summary": summary,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quiet", action="store_true", help="Only print summary")
    args = parser.parse_args()

    result = run()
    total = result["total"]
    loaded = result["loaded"]
    errs = result["errors"]
    warns = result["warnings"]
    s = result["summary"]

    if not args.quiet:
        print(f"\n{'=' * 60}")
        print("  QML Compile-All v11 Report")
        print(f"{'=' * 60}")
        print(f"  Total QML files:  {total}")
        print(f"  Loaded OK:         {loaded}")
        print(f"  Errors:            {len(errs)}")
        print(f"  Warnings:          {len(warns)}")
        print(f"  ─ Dependencia ausente: {s['dependencia_ausente']}")
        print(f"  ─ Sintaxis rota:       {s['sintaxis_rota']}")
        print(f"{'=' * 60}")

        if errs:
            print(f"\n  ERRORS ({len(errs)}):")
            for e in errs:
                cats = ", ".join(e["categories"])
                print(f"    [{cats}] {e['file']}")
                for err_str in e["errors"][:2]:
                    print(f"      -> {err_str[:160]}")
                if len(e["errors"]) > 2:
                    print(f"      ... and {len(e['errors']) - 2} more error(s)")

        if warns:
            print(f"\n  WARNINGS ({len(warns)}):")
            for w in warns:
                print(f"    {w['file']}")
                for ws in w["errors"][:2]:
                    print(f"      -> {ws[:160]}")

        cat_count = {}
        for e in errs:
            for c in e["categories"]:
                cat_count[c] = cat_count.get(c, 0) + 1
        if cat_count:
            print("\n  Error categories:")
            for cat, cnt in sorted(cat_count.items(), key=lambda x: -x[1]):
                print(f"    {cat}: {cnt}")

    print(f"\n{'=' * 60}")
    passed = loaded == total and len(errs) == 0
    if not args.quiet:
        print(f"  Gate: {'PASSED' if passed else 'FAILED'}")
        if not passed:
            if loaded != total:
                print(f"    -> {total - loaded} file(s) not loaded ({len(errs)} errors)")
    print(f"  Total={total}  Loaded={loaded}  Errors={len(errs)}")
    print(f"{'=' * 60}\n")

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
