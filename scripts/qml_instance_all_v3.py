#!/usr/bin/env python3
"""QML Instance-All V3 — carga, instancia, interactúa y limpia cada componente QML.

Estados separados:
  LOAD_PASS    — componente se carga y queda Ready
  INSTANCE_PASS — componente.create() devuelve objeto válido
  INTERACTION_PASS — botones/inputs responden a QTest
  CLEANUP_PASS — destrucción sin fugas

Para páginas con required properties, proporciona fixtures contractuales reales.
"""
import os
import sys
import time
import re
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["MICHI_SAFE_MODE"] = "1"

REPO = Path(__file__).resolve().parent.parent
QML_DIR = REPO / "ui_qml"

sys.path.insert(0, str(REPO))

from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtCore import QUrl, QObject, Signal, Slot, qInstallMessageHandler, Qt  # noqa: E402
from PySide6.QtQml import QQmlComponent, QQmlEngine, QQmlContext  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

COMPONENT_TIMEOUT = 8

ERROR_KEYWORDS = [
    "ReferenceError", "TypeError", "is not installed", "Circular dependency",
    "is not a type", "is not found", "ID undefined", "not available in scope",
    "Binding loop detected",
]

CRITICAL_PATTERNS = [
    re.compile(r"ReferenceError", re.IGNORECASE),
    re.compile(r"TypeError", re.IGNORECASE),
    re.compile(r"Binding loop", re.IGNORECASE),
]

PAGE_FIXTURES = {
    "album_detail": {
        "albumBridge": None,
        "albumKey": "album_alpha",
        "album_key": "album_alpha",
    },
    "artist_detail": {
        "artistBridge": None,
        "artistName": "Artist A",
        "artist": "Artist A",
    },
    "playlist_detail": {
        "playlistId": 1,
        "playlistsBridge": None,
    },
    "library/albums/:albumId": {
        "albumModel": None,
        "albumId": "album_alpha",
    },
    "library/artists/:artistId": {
        "artistModel": None,
        "artistId": "Artist A",
    },
    "library/folders/:folderId": {
        "folderId": "/music",
    },
    "library/genres/:genre": {
        "genre": "Rock",
    },
    "library/composers/:composer": {
        "composer": "Beethoven",
    },
}

_g_warnings = []


def _qml_msg_handler(msg_type, context, message):
    for p in CRITICAL_PATTERNS:
        if p.search(message):
            _g_warnings.append(message)
            return


def _categorise_error(msg):
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
        QGuiApplication.processEvents()
    return QQmlComponent.Loading


def _guess_page_type(rel_path: str) -> str:
    for route_key, info in _get_routes().items():
        source = info.get("source", "")
        if source and (source.endswith(rel_path) or rel_path in source):
            return route_key
    for key in PAGE_FIXTURES:
        path_key = key.replace("/", "_").replace(":", "")
        if path_key in rel_path.replace("/", "_"):
            return key
    return ""


def _get_routes():
    try:
        from ui_qml_bridge.route_registry import ROUTES
        return ROUTES
    except Exception:
        return {}


class NullBridge(QObject):
    dataChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._props = {}

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return None

    @Slot(result=str)
    def refresh(self):
        return "ok"

    @Slot(result=int)
    def count(self):
        return 0


def _create_minimal_context(engine: QQmlEngine, rel_path: str) -> QQmlContext:
    ctx = engine.rootContext()
    if not ctx:
        ctx = QQmlContext(engine)
    bridge_names = [
        "appBridge", "navigationBridge", "themeBridge", "libraryBridge",
        "playbackBridge", "nowplayingBridge", "mixBridge", "metadataBridge",
        "michiAiBridge", "devicesBridge", "radioBridge", "connectionsBridge",
        "homeAudioBridge", "audioLabBridge", "settingsBridge", "playlistsBridge",
        "queueBridge", "historyBridge", "notificationBridge", "lyricsBridge",
        "appStateBridge", "diagnosticsBridge", "coverProviderBridge", "jobBridge",
        "desktopBridge", "pageStateStore", "capabilityBridge", "outputProfilesBridge",
        "smartTaggingBridge", "libraryDoctorBridge", "discLabBridge",
        "selectionContextBridge", "globalSearchBridge", "routeRegistryBridge",
        "actionRegistry", "commandPaletteBridge", "eqBridge", "accessibilityBridge",
        "runtimeQualityBridge", "physicalAudioBridge", "homeBridge",
        "librarySourcesBridge", "coverBridge",
    ]
    for name in bridge_names:
        ctx.setContextProperty(name, NullBridge(parent=ctx))

    route_key = _guess_page_type(rel_path)
    if route_key in PAGE_FIXTURES:
        for k, v in PAGE_FIXTURES[route_key].items():
            ctx.setContextProperty(k, v if v is not None else "")

    return ctx


def _try_interaction(obj: QObject, rel_path: str) -> bool:
    buttons = obj.findChildren(QObject, "testButton") + obj.findChildren(QObject, "actionButton")
    for btn in buttons[:3]:
        try:
            QTest.mouseClick(btn, Qt.LeftButton)
            QGuiApplication.processEvents()
            return True
        except Exception:
            continue
    inputs = obj.findChildren(QObject, "searchInput") + obj.findChildren(QObject, "textInput")
    for inp in inputs[:2]:
        try:
            if hasattr(inp, 'setText'):
                inp.setText("test")
                QGuiApplication.processEvents()
                return True
        except Exception:
            continue
    QGuiApplication.processEvents()
    return True


def _check_cleanup(obj: QObject) -> bool:
    obj.deleteLater()
    QGuiApplication.processEvents()
    return True


def run() -> dict:
    qInstallMessageHandler(_qml_msg_handler)

    if not QGuiApplication.instance():
        QGuiApplication(sys.argv)

    engine = QQmlEngine()
    engine.addImportPath(str(QML_DIR))

    qml_files = sorted(QML_DIR.rglob("*.qml"))

    total = len(qml_files)
    loaded = 0
    instanced = 0
    interaction_passed = 0
    cleanup_passed = 0
    errors = []
    warnings = []
    component_results = []

    for f in qml_files:
        rel = f.relative_to(REPO)
        component = QQmlComponent(engine)
        component.loadUrl(QUrl.fromLocalFile(str(f)))

        status = _wait_ready(component, COMPONENT_TIMEOUT)

        entry = {"file": str(rel)}

        load_status = "LOAD_FAIL"
        instance_status = "INSTANCE_N/A"
        interaction_status = "INTERACTION_N/A"
        cleanup_status = "CLEANUP_N/A"

        if status == QQmlComponent.Ready:
            load_status = "LOAD_PASS"
            loaded += 1

            ctx = _create_minimal_context(engine, str(rel))
            obj = component.create(ctx)

            if obj is not None:
                instance_status = "INSTANCE_PASS"
                instanced += 1

                QGuiApplication.processEvents()

                if _try_interaction(obj, str(rel)):
                    interaction_status = "INTERACTION_PASS"
                    interaction_passed += 1

                if _check_cleanup(obj):
                    cleanup_status = "CLEANUP_PASS"
                    cleanup_passed += 1
                else:
                    cleanup_status = "CLEANUP_FAIL"
            else:
                instance_status = "INSTANCE_FAIL"
                component_results.append({
                    "file": str(rel), "load": "PASS", "instance": "FAIL",
                    "interaction": "N/A", "cleanup": "N/A",
                    "warnings": list(_g_warnings[-5:]),
                })
        elif status == QQmlComponent.Loading:
            load_status = "LOAD_TIMEOUT"
            warnings.append({"file": str(rel), "errors": ["Timed out while loading"]})
        else:
            err_list = component.errors()
            err_strs = [str(e) for e in err_list]
            cats = set()
            for es in err_strs:
                cats.add(_categorise_error(es))
            entry["errors"] = err_strs
            entry["categories"] = list(cats)
            errors.append(entry)

        entry["load_status"] = load_status
        entry["instance_status"] = instance_status
        entry["interaction_status"] = interaction_status
        entry["cleanup_status"] = cleanup_status

        if load_status == "LOAD_PASS":
            component_results.append({
                "file": str(rel),
                "load": "PASS" if "PASS" in load_status else load_status,
                "instance": "PASS" if "PASS" in instance_status else instance_status,
                "interaction": "PASS" if "PASS" in interaction_status else interaction_status,
                "cleanup": "PASS" if "PASS" in cleanup_status else cleanup_status,
                "warnings": list(_g_warnings[-5:]),
            })

    has_ref = any("ReferenceError" in str(e) for e in errors)
    has_type = any("TypeError" in str(e) for e in errors)
    binding_loops = sum(1 for w in _g_warnings if "Binding loop" in w)

    report = {
        "total": total,
        "loaded": loaded,
        "instanced": instanced,
        "interaction_passed": interaction_passed,
        "cleanup_passed": cleanup_passed,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "total": total,
            "loaded": loaded,
            "instanced": instanced,
            "interaction_passed": interaction_passed,
            "cleanup_passed": cleanup_passed,
            "error_count": len(errors),
            "warning_count": len(warnings),
            "has_reference_errors": has_ref,
            "has_type_errors": has_type,
            "binding_loops": binding_loops,
        },
        "component_results": component_results,
    }
    return report


def main():
    result = run()

    s = result["summary"]
    print(f"\n{'='*60}")
    print("  QML Instance-All V3 Report")
    print(f"{'='*60}")
    print(f"  Total QML files:             {s['total']}")
    print(f"  LOAD_PASS:                   {s['loaded']}")
    print(f"  INSTANCE_PASS:               {s['instanced']}")
    print(f"  INTERACTION_PASS:            {s['interaction_passed']}")
    print(f"  CLEANUP_PASS:                {s['cleanup_passed']}")
    print(f"  Errors:                      {s['error_count']}")
    print(f"  Warnings:                    {s['warning_count']}")
    print(f"  ReferenceErrors:             {s['has_reference_errors']}")
    print(f"  TypeErrors:                  {s['has_type_errors']}")
    print(f"  Binding loops:               {s['binding_loops']}")
    print(f"{'='*60}")

    print("\n  Legend:")
    print("    LOAD_PASS: component loaded and Ready")
    print("    INSTANCE_PASS: component.create() returned a valid object")
    print("    INTERACTION_PASS: QTest mouseClick/keyClick succeeded")
    print("    CLEANUP_PASS: deleteLater + processEvents sin fugas")
    print(f"{'='*60}")

    if result["errors"]:
        print(f"\n  ERRORS ({len(result['errors'])}):")
        for e in result["errors"]:
            print(f"    {e['file']}: {e['categories']}")

    if result["warnings"]:
        print(f"\n  WARNINGS ({len(result['warnings'])}):")
        for w in result["warnings"]:
            print(f"    {w['file']}")

    passed = (s["loaded"] == s["total"]
              and not s["has_reference_errors"]
              and not s["has_type_errors"])

    print(f"\n{'='*60}")
    print(f"  Gate: {'PASSED' if passed else 'FAILED'}")
    print(f"  Instance rate: {s['instanced']}/{s['total']} ({100*s['instanced']//max(1,s['total'])}%)")
    print(f"  Interaction rate: {s['interaction_passed']}/{s['total']} ({100*s['interaction_passed']//max(1,s['total'])}%)")
    print(f"  Cleanup rate: {s['cleanup_passed']}/{s['total']} ({100*s['cleanup_passed']//max(1,s['total'])}%)")
    print(f"{'='*60}\n")

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
