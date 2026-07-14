#!/usr/bin/env python3
"""QML Compile-All — loads every .qml file as QQmlComponent and reports status.

Gate: 100% loaded, 0 ReferenceError, 0 TypeError, 0 component not ready.
"""
import sys
import time
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine


REPO = Path(__file__).resolve().parent.parent
QML_DIR = REPO / "ui_qml"

ERROR_KEYWORDS = [
    "ReferenceError",
    "TypeError",
    "is not installed",
    "Circular dependency",
    "is not a type",
    "is not found",
    "ID undefined",
    "not available in scope",
    "Binding loop detected",
]

COMPONENT_TIMEOUT = 8


def _categorise_error(msg: str) -> str:
    for kw in ERROR_KEYWORDS:
        if kw in msg:
            return kw.replace(" is not installed", "").replace(" is not a type", "")
    return "Other"


def _wait_ready(component, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        s = component.status()
        if s != QQmlComponent.Loading:
            return s
        QCoreApplication.processEvents()
    return QQmlComponent.Loading


def run() -> dict:
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
            is_page = str(f.relative_to(QML_DIR)).startswith("pages/")
            if is_page:
                errs = component.errors()
                if errs:
                    warnings.append({
                        "file": str(rel),
                        "errors": [str(e) for e in errs],
                    })
            continue

        if status == QQmlComponent.Loading:
            warnings.append({
                "file": str(rel),
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
                "errors": err_strs,
            })

    return {
        "total": total,
        "loaded": loaded,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "total": total,
            "loaded": loaded,
            "error_count": len(errors),
            "warning_count": len(warnings),
        },
    }


def main():
    result = run()

    total = result["total"]
    loaded = result["loaded"]
    errs = result["errors"]
    warns = result["warnings"]

    print(f"\n{'=' * 60}")
    print("  QML Compile-All Report")
    print(f"{'=' * 60}")
    print(f"  Total QML files:  {total}")
    print(f"  Loaded OK:         {loaded}")
    print(f"  Errors:            {len(errs)}")
    print(f"  Warnings:          {len(warns)}")
    print(f"{'=' * 60}")

    if errs:
        print(f"\n  ERRORS ({len(errs)}):")
        for e in errs:
            cats = ", ".join(e["categories"])
            print(f"    [{cats}] {e['file']}")
            for err_str in e["errors"][:3]:
                print(f"      -> {err_str[:140]}")
            if len(e["errors"]) > 3:
                print(f"      ... and {len(e['errors']) - 3} more error(s)")

    if warns:
        print(f"\n  WARNINGS ({len(warns)}):")
        for w in warns:
            print(f"    {w['file']}")
            for ws in w["errors"][:2]:
                print(f"      -> {ws[:140]}")

    category_count = {}
    for e in errs:
        for c in e["categories"]:
            category_count[c] = category_count.get(c, 0) + 1

    if category_count:
        print("\n  Error categories:")
        for cat, cnt in sorted(category_count.items(), key=lambda x: -x[1]):
            print(f"    {cat}: {cnt}")

    has_ref = any("ReferenceError" in c for e in errs for c in e["categories"])
    has_type = any("TypeError" in c for e in errs for c in e["categories"])
    not_ready = len(errs)

    passed = (
        loaded == total
        and not has_ref
        and not has_type
        and not_ready == 0
    )

    print(f"\n{'=' * 60}")
    print(f"  Gate: {'PASSED' if passed else 'FAILED'}")
    if not passed:
        if loaded != total:
            print(f"    -> {total - loaded} file(s) not loaded")
        if has_ref:
            print("    -> ReferenceError(s) detected")
        if has_type:
            print("    -> TypeError(s) detected")
        if not_ready:
            print(f"    -> {not_ready} component(s) not ready")
    print(f"{'=' * 60}\n")

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
