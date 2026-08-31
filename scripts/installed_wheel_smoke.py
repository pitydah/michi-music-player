"""Smoke the installed wheel, including the premium Library QML resources."""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine

import michi


def main() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QGuiApplication.instance() or QGuiApplication([])
    qml = Path(michi.__file__).resolve().parent / "presentation/qml"
    required = (
        "views/LibraryView.qml",
        "views/LibraryViewOptionsPopup.qml",
        "primitives/MichiMaterial.qml",
        "theme/MichiBreakpoints.qml",
        "assets/paper-editorial-01.svg",
    )
    missing = [relative for relative in required if not (qml / relative).is_file()]
    if missing:
        raise RuntimeError(f"wheel is missing resources: {missing}")

    engine = QQmlEngine()
    engine.addImportPath(str(qml))
    component = QQmlComponent(engine, str(qml / "primitives/MichiMaterial.qml"))
    errors = "; ".join(error.toString() for error in component.errors())
    if component.status() != QQmlComponent.Ready:
        raise RuntimeError(f"installed QML failed to compile: {errors}")
    material = component.create()
    if material is None:
        raise RuntimeError("installed MichiMaterial could not instantiate")
    material.deleteLater()
    app.processEvents()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
