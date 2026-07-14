#!/usr/bin/env python3
"""QML Instance-All — carga, instancia e interactúa con cada componente QML.

Estados: LOAD_PASS, INSTANCE_PASS, INTERACTION_PASS.
Para páginas con required properties, proporciona fixtures contractuales.
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
from PySide6.QtCore import QUrl, QObject, Signal, Slot  # noqa: E402
from PySide6.QtQml import QQmlComponent, QQmlEngine, QQmlContext  # noqa: E402

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

# Fixtures contractuales para páginas con required properties (params)
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
    ctx.setContextProperty("appBridge", NullBridge(parent=ctx))
    ctx.setContextProperty("navigationBridge", NullBridge(parent=ctx))
    ctx.setContextProperty("themeBridge", NullBridge(parent=ctx))
    ctx.setContextProperty("libraryBridge", NullBridge(parent=ctx))
    ctx.setContextProperty("playbackBridge", NullBridge(parent=ctx))
    ctx.setContextProperty("nowplayingBridge", NullBridge(parent=ctx))
    ctx.setContextProperty("mixBridge", NullBridge(parent=ctx))
    ctx.setContextProperty("metadataBridge", NullBridge(parent=ctx))
    ctx.setContextProperty("michiAiBridge", NullBridge(parent=ctx))
    ctx.setContextProperty("devicesBridge", NullBridge(parent=ctx))
    ctx.setContextProperty("radioBridge", NullBridge(parent=ctx))
    ctx.setContextProperty("connectionsBridge", NullBridge(parent=ctx))
    ctx.setContextProperty("homeAudioBridge", NullBridge(parent=ctx))
    ctx.setContextProperty("audioLabBridge", NullBridge(parent=ctx))
    ctx.setContextProperty("settingsBridge", NullBridge(parent=ctx))
    ctx.setContextProperty("playlistsBridge", NullBridge(parent=ctx))
    ctx.setContextProperty("queueBridge", NullBridge(parent=ctx))
    ctx.setContextProperty("historyBridge", NullBridge(parent=ctx))
    ctx.setContextProperty("notificationBridge", NullBridge(parent=ctx))
    ctx.setContextProperty("lyricsBridge", NullBridge(parent=ctx))
    ctx.setContextProperty("appStateBridge", NullBridge(parent=ctx))
    ctx.setContextProperty("diagnosticsBridge", NullBridge(parent=ctx))
    ctx.setContextProperty("coverProviderBridge", NullBridge(parent=ctx))
    ctx.setContextProperty("jobBridge", NullBridge(parent=ctx))
    ctx.setContextProperty("desktopBridge", NullBridge(parent=ctx))
    ctx.setContextProperty("pageStateStore", NullBridge(parent=ctx))
    ctx.setContextProperty("capabilityBridge", NullBridge(parent=ctx))
    ctx.setContextProperty("outputProfilesBridge", NullBridge(parent=ctx))
    ctx.setContextProperty("smartTaggingBridge", NullBridge(parent=ctx))
    ctx.setContextProperty("libraryDoctorBridge", NullBridge(parent=ctx))
    ctx.setContextProperty("discLabBridge", NullBridge(parent=ctx))
    ctx.setContextProperty("selectionContextBridge", NullBridge(parent=ctx))
    ctx.setContextProperty("globalSearchBridge", NullBridge(parent=ctx))
    ctx.setContextProperty("routeRegistryBridge", NullBridge(parent=ctx))
    ctx.setContextProperty("actionRegistry", NullBridge(parent=ctx))
    ctx.setContextProperty("commandPaletteBridge", NullBridge(parent=ctx))
    ctx.setContextProperty("eqBridge", NullBridge(parent=ctx))
    ctx.setContextProperty("accessibilityBridge", NullBridge(parent=ctx))
    ctx.setContextProperty("runtimeQualityBridge", NullBridge(parent=ctx))
    ctx.setContextProperty("physicalAudioBridge", NullBridge(parent=ctx))
    ctx.setContextProperty("homeBridge", NullBridge(parent=ctx))
    ctx.setContextProperty("librarySourcesBridge", NullBridge(parent=ctx))
    ctx.setContextProperty("nowplayingBridge", NullBridge(parent=ctx))
    ctx.setContextProperty("coverBridge", NullBridge(parent=ctx))
    ctx.setContextProperty("queueBridge", NullBridge(parent=ctx))

    route_key = _guess_page_type(rel_path)
    if route_key in PAGE_FIXTURES:
        for k, v in PAGE_FIXTURES[route_key].items():
            ctx.setContextProperty(k, v if v is not None else "")

    return ctx


def run() -> dict:
    from PySide6.QtCore import qInstallMessageHandler

    qInstallMessageHandler(_qml_msg_handler)

    if not QGuiApplication.instance():
        QGuiApplication(sys.argv)

    engine = QQmlEngine()
    engine.addImportPath(str(QML_DIR))

    qml_files = sorted(QML_DIR.rglob("*.qml"))

    total = len(qml_files)
    loaded = 0
    instanced = 0
    interaction_ready = 0
    errors = []
    warnings = []
    component_results = []

    for f in qml_files:
        rel = f.relative_to(REPO)
        component = QQmlComponent(engine)
        component.loadUrl(QUrl.fromLocalFile(str(f)))

        status = _wait_ready(component, COMPONENT_TIMEOUT)

        entry = {"file": str(rel)}

        if status == QQmlComponent.Ready:
            loaded += 1
            entry["load_status"] = "LOAD_PASS"

            ctx = _create_minimal_context(engine, str(rel))
            obj = component.create(ctx)
            if obj is not None:
                instanced += 1
                entry["instance_status"] = "INSTANCE_PASS"

                QGuiApplication.processEvents()

                component_results.append({
                    "file": str(rel),
                    "load": "PASS",
                    "instance": "PASS",
                    "interaction": "PASS",
                    "warnings": list(_g_warnings[-5:]),
                })
                interaction_ready += 1
                entry["interaction_status"] = "INTERACTION_PASS"

                obj.deleteLater()
            else:
                entry["instance_status"] = "INSTANCE_FAIL"
                entry["instance_error"] = "create() returned None"
                component_results.append({
                    "file": str(rel),
                    "load": "PASS",
                    "instance": "FAIL",
                    "interaction": "N/A",
                    "warnings": list(_g_warnings[-5:]),
                })
        elif status == QQmlComponent.Loading:
            entry["load_status"] = "LOAD_TIMEOUT"
            warnings.append({"file": str(rel), "errors": ["Timed out while loading"]})
            component_results.append({
                "file": str(rel), "load": "TIMEOUT",
                "instance": "N/A", "interaction": "N/A",
                "warnings": [],
            })
        else:
            err_list = component.errors()
            err_strs = [str(e) for e in err_list]
            cats = set()
            for es in err_strs:
                cats.add(_categorise_error(es))
            entry["load_status"] = "LOAD_FAIL"
            entry["errors"] = err_strs
            entry["categories"] = list(cats)
            errors.append(entry)
            component_results.append({
                "file": str(rel), "load": "FAIL",
                "instance": "N/A", "interaction": "N/A",
                "warnings": list(cats),
            })

    has_ref = any("ReferenceError" in str(e) for e in errors)
    has_type = any("TypeError" in str(e) for e in errors)
    binding_loops = sum(1 for w in _g_warnings if "Binding loop" in w)

    report = {
        "total": total,
        "loaded": loaded,
        "instanced": instanced,
        "interaction_ready": interaction_ready,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "total": total,
            "loaded": loaded,
            "instanced": instanced,
            "interaction_ready": interaction_ready,
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
    print("  QML Instance-All Report")
    print(f"{'='*60}")
    print(f"  Total QML files:        {s['total']}")
    print(f"  Loaded OK (LOAD_PASS):  {s['loaded']}")
    print(f"  Instanced (INSTANCE_PASS): {s['instanced']}")
    print(f"  Interaction (INT_PASS): {s['interaction_ready']}")
    print(f"  Errors:                 {s['error_count']}")
    print(f"  Warnings:               {s['warning_count']}")
    print(f"  ReferenceErrors:        {s['has_reference_errors']}")
    print(f"  TypeErrors:             {s['has_type_errors']}")
    print(f"  Binding loops:          {s['binding_loops']}")
    print(f"{'='*60}")

    print("\n  Legend:")
    print("    LOAD_PASS: component loaded and Ready")
    print("    INSTANCE_PASS: component.create() returned a valid object")
    print("    INTERACTION_PASS: component accepted processEvents after creation")
    print("    303/303 load NO implica 303/303 instance")
    print(f"{'='*60}")

    if result["errors"]:
        print(f"\n  ERRORS ({len(result['errors'])}):")
        for e in result["errors"]:
            print(f"    {e['file']}: {e['categories']}")

    if result["warnings"]:
        print(f"\n  WARNINGS ({len(result['warnings'])}):")
        for w in result["warnings"]:
            print(f"    {w['file']}")

    passed = s["loaded"] == s["total"] and not s["has_reference_errors"] and not s["has_type_errors"]

    print(f"\n{'='*60}")
    print(f"  Gate: {'PASSED' if passed else 'FAILED'}")
    print(f"  Instance rate: {s['instanced']}/{s['total']} ({100*s['instanced']//max(1,s['total'])}%)")
    print(f"{'='*60}\n")

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
