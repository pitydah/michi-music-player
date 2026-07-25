from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine


REPO = Path(__file__).resolve().parents[3]
QML_ROOT = REPO / "ui_qml"


class MockBridge(QObject):
    pass


class MockLibraryBridge(QObject):
    stateChanged = Signal()
    dataChanged = Signal()
    searchTextChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = "INITIALIZING"
        self._song_count = 0
        self._album_count = 0
        self._artist_count = 0
        self._error_message = ""
        self._active_format_filter = ""
        self._track_model = None
        self._album_model = None
        self._artist_model = None
        self._folder_model = None

    @Property(str, notify=stateChanged)
    def state(self):
        return self._state

    @Property(int, notify=stateChanged)
    def songCount(self):
        return self._song_count

    @Property(int, notify=stateChanged)
    def albumCount(self):
        return self._album_count

    @Property(int, notify=stateChanged)
    def artistCount(self):
        return self._artist_count

    @Property(str, notify=stateChanged)
    def errorMessage(self):
        return self._error_message

    @Property(str, notify=dataChanged)
    def activeFormatFilter(self):
        return self._active_format_filter


class MockNavigationBridge(QObject):
    routeChanged = Signal(str)
    routeRefreshRequested = Signal(str)
    routeParamsChanged = Signal()
    breadcrumbChanged = Signal()
    navigationBlocked = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_route = "home"
        self._current_params = {}
        self._history = []
        self._can_go_back = False
        self._can_go_forward = False

    @Property(str, notify=routeChanged)
    def currentRoute(self):
        return self._current_route

    @Property("QVariantMap", notify=routeParamsChanged)
    def currentParams(self):
        return self._current_params

    @Property("QVariantList", notify=routeChanged)
    def history(self):
        return self._history

    @Property(bool, notify=routeChanged)
    def canGoBack(self):
        return self._can_go_back

    @Property(bool, notify=routeChanged)
    def canGoForward(self):
        return self._can_go_forward


class MockAudioLabBridge(QObject):
    jobCompleted = Signal(str, str, object)
    jobFailed = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)

    @Slot(str, result=object)
    def startAnalysis(self, filepath: str):
        return None

    @Slot(str, result=object)
    def previewComparison(self, file_a: str, file_b: str):
        return None

    @Slot(str)
    def cancelJob(self, job_id: str):
        pass


class MockNotificationBridge(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)

    @Slot(str)
    @Slot(str, str)
    def showMessage(self, message: str, kind: str = "info"):
        pass


class MockQueueBridge(QObject):
    pass


class MockNowPlayingBridge(QObject):
    pass


class MockActionRegistry(QObject):
    pass


class MockAIBridge(QObject):
    pass


class MockMetadataBridge(QObject):
    pass


class MockPlaylistsBridge(QObject):
    pass


class MockSettingsBridge(QObject):
    pass


class MockCoverProviderBridge(QObject):
    pass


class MockMixBridge(QObject):
    pass


class MockHomeBridge(QObject):
    pass


class MockConnectionsBridge(QObject):
    pass


class MockHomeAudioBridge(QObject):
    pass


class MockMichiLink(QObject):
    pass


class MockSyncBridge(QObject):
    pass


class MockSearchController(QObject):
    pass


class MockCommandPaletteBridge(QObject):
    pass


class MockEqBridge(QObject):
    pass


BRIDGE_DEFAULTS: dict[str, type[QObject]] = {
    "navigationBridge": MockNavigationBridge,
    "queueBridge": MockQueueBridge,
    "notificationBridge": MockNotificationBridge,
    "nowplayingBridge": MockNowPlayingBridge,
    "actionRegistry": MockActionRegistry,
    "audioLabBridge": MockAudioLabBridge,
    "metadataBridge": MockMetadataBridge,
    "playlistsBridge": MockPlaylistsBridge,
    "settingsBridge": MockSettingsBridge,
    "libraryBridge": MockLibraryBridge,
    "coverProviderBridge": MockCoverProviderBridge,
    "mixBridge": MockMixBridge,
    "homeBridge": MockHomeBridge,
    "connectionsBridge": MockConnectionsBridge,
    "homeAudioBridge": MockHomeAudioBridge,
    "michiLink": MockMichiLink,
    "syncBridge": MockSyncBridge,
    "searchController": MockSearchController,
    "commandPaletteBridge": MockCommandPaletteBridge,
    "eqBridge": MockEqBridge,
}


def create_qml_engine() -> QQmlEngine:
    app = QGuiApplication.instance()
    if not app:
        QGuiApplication(sys.argv)

    engine = QQmlEngine()
    engine.addImportPath(str(QML_ROOT))
    return engine


def register_bridges(
    engine: QQmlEngine,
    overrides: dict[str, QObject | None] | None = None,
) -> dict[str, QObject]:
    overrides = overrides or {}
    bridges: dict[str, QObject] = {}

    for name, cls in BRIDGE_DEFAULTS.items():
        if name in overrides:
            if overrides[name] is not None:
                bridges[name] = overrides[name]
                engine.rootContext().setContextProperty(name, overrides[name])
        else:
            instance = cls()
            bridges[name] = instance
            engine.rootContext().setContextProperty(name, instance)

    return bridges


def resolve_qml_source(source_path: str) -> Path:
    stripped = source_path.removeprefix("../")
    return QML_ROOT / stripped


def load_qml_component(
    qml_source: str | Path,
    engine: QQmlEngine | None = None,
    bridges: dict[str, QObject] | None = None,
    initial_properties: dict[str, Any] | None = None,
    timeout_ms: int = 8000,
) -> dict[str, Any]:
    if engine is None:
        engine = create_qml_engine()

    if bridges is not None:
        for name, bridge in bridges.items():
            engine.rootContext().setContextProperty(name, bridge)

    path = resolve_qml_source(qml_source) if isinstance(qml_source, str) else Path(qml_source)

    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(path)))

    deadline = time.monotonic() + (timeout_ms / 1000)
    while time.monotonic() < deadline:
        status = component.status()
        if status != QQmlComponent.Loading:
            break

    status = component.status()
    errors = []
    if component.errors():
        for err in component.errors():
            errors.append({
                "url": str(err.url()) if err.url() else "",
                "line": err.line(),
                "column": err.column(),
                "description": err.description(),
            })

    obj = None
    obj_name = ""
    if status == QQmlComponent.Ready:
        obj = component.createWithInitialProperties(initial_properties or {})
        if obj is not None:
            obj_name = obj.objectName()

    status_str = {
        QQmlComponent.Null: "Null",
        QQmlComponent.Ready: "Ready",
        QQmlComponent.Loading: "Loading",
        QQmlComponent.Error: "Error",
    }.get(status, f"Unknown({status})")

    return {
        "ok": status == QQmlComponent.Ready and obj is not None,
        "route": str(qml_source),
        "source": str(path),
        "status": status_str,
        "object_name": obj_name,
        "errors": errors,
        "component": component,
        "object": obj,
        "engine": engine,
    }
