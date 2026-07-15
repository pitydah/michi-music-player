#!/usr/bin/env python3
"""QML Instance-all V11 — load, instance, and interact with every QML page."""
import os
import sys
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["MICHI_SAFE_MODE"] = "1"

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))  # noqa: E402

from PySide6.QtCore import QCoreApplication  # noqa: E402
from PySide6.QtQml import QQmlEngine, QQmlComponent  # noqa: E402

PAGE_DIR = REPO / "ui_qml"


def main():
    from PySide6.QtGui import QGuiApplication
    QGuiApplication(sys.argv)
    engine = QQmlEngine()
    engine.addImportPath(str(PAGE_DIR))

    qml_files = sorted(PAGE_DIR.rglob("*.qml"))
    total = len(qml_files)
    load_ok = 0
    instance_ok = 0
    errors = []

    for f in qml_files:
        rel = f.relative_to(REPO)
        component = QQmlComponent(engine, str(f))
        if component.status() == QQmlComponent.Error:
            errors.append(f"{rel}: {component.errors()}")
            continue
        load_ok += 1
        obj = component.create()
        if obj is None:
            errors.append(f"{rel}: create() returned None")
            continue
        instance_ok += 1
        QCoreApplication.processEvents()
        del obj

    print(f"\n{'='*60}")
    print("  QML Instance-all V11")
    print(f"{'='*60}")
    print(f"  Total:  {total}")
    print(f"  Load:   {load_ok}")
    print(f"  Instance: {instance_ok}")
    print(f"  Errors:  {len(errors)}")
    if errors:
        for e in errors[:10]:
            print(f"    {e}")
    print(f"{'='*60}")
    print(f"  Gate: {'PASSED' if load_ok == total and instance_ok == total else 'FAILED'}")
    print(f"{'='*60}")
    return 0 if load_ok == total and instance_ok == total else 1


if __name__ == "__main__":
    sys.exit(main())
