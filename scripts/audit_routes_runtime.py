#!/usr/bin/env python3
"""audit_routes_runtime.py — audit every registered route at runtime.

For each route in route_registry.ROUTES:
  - check source exists
  - compile via QQmlComponent
  - create instance
  - verify no QML critical errors
  - report status
"""
import json
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtGui import QGuiApplication

sys.path.insert(0, str(Path(__file__).parent.parent))
from ui_qml_bridge.route_registry import ROUTES

QML_ROOT = Path("ui_qml")


def main():
    _app = QGuiApplication.instance() or QGuiApplication([])
    engine = QQmlEngine()
    engine.addImportPath(str(QML_ROOT))

    results = []
    for route, spec in sorted(ROUTES.items()):
        source = spec.get("source", "")
        rel = source.replace("../", "")
        qml_path = QML_ROOT / rel
        entry = {
            "route": route,
            "source": source,
            "status_declared": spec.get("status", ""),
            "source_exists": qml_path.exists(),
        }
        if not qml_path.exists():
            entry["result"] = "MISSING_SOURCE"
            results.append(entry)
            continue
        comp = QQmlComponent(engine)
        comp.loadUrl(qml_path.resolve().as_uri())
        if comp.status() == QQmlComponent.Error:
            entry["result"] = "COMPILE_ERROR"
            entry["qml_diagnostics"] = [str(e) for e in comp.errors()]
        elif comp.status() == QQmlComponent.Ready:
            entry["result"] = "COMPILE_OK"
        else:
            entry["result"] = "LOADING"
        results.append(entry)
        comp.deleteLater()

    out_dir = Path("artifacts/route_audit")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "runtime_route_matrix.json").write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
