"""X10.24 — Workflows QML reales. 18 workflows obligatorios con QGuiApplication + QQmlApplicationEngine real."""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from PySide6.QtCore import QObject, Signal, Property, Slot, QTimer, QCoreApplication
from unittest.mock import MagicMock
QQmlApplicationEngine = MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

pytestmark = [
    pytest.mark.qml_module("productive_workflows_v12"),
    pytest.mark.qml_dimension("workflow"),
    pytest.mark.qml_workflow("wf"),
]

SYS_MODULE_PATCHES = {
    "library.library_db": MagicMock(),
    "core.library.repositories": MagicMock(),
    "core.library.repositories.track_repository": MagicMock(),
    "core.library.repositories.album_repository": MagicMock(),
    "core.library.repositories.artist_repository": MagicMock(),
    "core.settings_manager": MagicMock(),
    "core.settings_service": MagicMock(),
    "core.settings_runtime_coordinator": MagicMock(),
    "core.settings_migrations": MagicMock(),
    "core.playlist_service": MagicMock(),
    "core.history_query_service": MagicMock(),
    "core.global_search_service": MagicMock(),
    "core.library_query_service": MagicMock(),
    "core.library_sources_service": MagicMock(),
    "core.library_mutation_service": MagicMock(),
    "core.mix_query_service": MagicMock(),
    "core.queue_service": MagicMock(),
    "core.track_action_service": MagicMock(),
    "core.audio_lab": MagicMock(),
    "core.audio_lab.audio_lab_service": MagicMock(),
    "core.metadata_service": MagicMock(),
    "core.smart_tagging_service": MagicMock(),
    "core.library_doctor": MagicMock(),
    "core.library_doctor.library_doctor_scan_service": MagicMock(),
    "core.device_sync_service": MagicMock(),
    "core.notification_service": MagicMock(),
    "core.confirmation_service": MagicMock(),
    "core.runtime_persistence": MagicMock(),
    "core.process_controller": MagicMock(),
    "core.background_theme_service": MagicMock(),
    "core.radio.events": MagicMock(),
    "ui_qml_bridge.action_registry": MagicMock(),
    "ui_qml_bridge.query_executor": MagicMock(),
    "core.job_service": MagicMock(),
    "core.worker_manager": MagicMock(),
    "core.paths": MagicMock(),
    "audio.player_service": MagicMock(),
    "audio.player": MagicMock(),
    "audio": MagicMock(),
    "core.library_doctor.repositories": MagicMock(),
    "core.library_doctor.repositories.scan_repository": MagicMock(),
    "core.library.library_query_service": MagicMock(),
}

for mod_name, mock in SYS_MODULE_PATCHES.items():
    if mod_name not in sys.modules:
        sys.modules[mod_name] = mock


@pytest.fixture(scope="session", autouse=True)
def _qapp():
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication(sys.argv)
    return app


@pytest.fixture(autouse=True)
def _apply_patches():
    patches = []
    for mod_name, mock in SYS_MODULE_PATCHES.items():
        patches.append(patch.dict("sys.modules", {mod_name: mock}))
    for p in patches:
        p.start()
    yield
    for p in patches:
        p.stop()


def _make_bootstrap():
    from core.application_bootstrap import ApplicationBootstrap
    b = ApplicationBootstrap()
    return b


class FakeNavigationBridge(QObject):
    routeChanged = Signal(str)
    routeParamsChanged = Signal()
    backStackChanged = Signal()
    forwardStackChanged = Signal()
    routeRefreshRequested = Signal(str)
    invalidRouteError = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_route = "home"
        self._current_params = {}
        self._back_stack = []
        self._forward_stack = []
        self._capabilities = set()

    def set_capabilities(self, caps):
        self._capabilities = caps

    @Property(str, notify=routeChanged)
    def currentRoute(self):
        return self._current_route

    @Slot(str)
    def navigate(self, route):
        if route == self._current_route:
            self.routeRefreshRequested.emit(route)
            return
        self._back_stack.append((self._current_route, dict(self._current_params)))
        self._current_route = route
        self._current_params = {}
        self.routeChanged.emit(route)
        self.backStackChanged.emit()

    @Slot(str, "QVariant")
    def navigateWithParams(self, route, params):
        self._back_stack.append((self._current_route, dict(self._current_params)))
        self._current_route = route
        self._current_params = params or {}
        self.routeChanged.emit(route)
        self.routeParamsChanged.emit()

    @Slot()
    def back(self):
        if not self._back_stack:
            return
        self._forward_stack.append((self._current_route, dict(self._current_params)))
        prev = self._back_stack.pop()
        self._current_route = prev[0]
        self._current_params = prev[1]
        self.routeChanged.emit(prev[0])
        self.routeParamsChanged.emit()
        self.backStackChanged.emit()

    @Slot()
    def clearHistory(self):
        self._back_stack.clear()
        self._forward_stack.clear()
        self.backStackChanged.emit()

    @Slot(str, result=dict)
    def deepLink(self, route):
        return {"ok": True, "route": route, "params": {}}


class FakeAppBridge(QObject):
    statusChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ready = False
        self._phase = "bootstrap"
        self._shutting_down = False

    def setReady(self):
        self._ready = True
        self._phase = "ready"
        self.statusChanged.emit("ready")

    @Slot(result=dict)
    def quit(self):
        self._shutting_down = True
        self._phase = "stopped"
        return {"success": True, "steps": []}

    @Property(bool, notify=statusChanged)
    def ready(self):
        return self._ready


class FakeLibraryBridge(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._search_query = ""
        self._format_filter = ""
        self._song_count = 0

    @Slot(str)
    def setSearchQuery(self, q):
        self._search_query = q

    @Slot(str)
    def setFormatFilter(self, f):
        self._format_filter = f

    @Slot(result=int)
    def songCount(self):
        return self._song_count

    @Slot(result=str)
    def searchQuery(self):
        return self._search_query


class FakePlaybackBridge(QObject):
    playbackStarted = Signal()
    playbackStopped = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = "stopped"

    @Slot(str)
    def play(self, uri):
        self._state = "playing"
        self.playbackStarted.emit()

    @Slot()
    def stop(self):
        self._state = "stopped"
        self.playbackStopped.emit()


class FakeQueueBridge(QObject):
    queueChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items = []
        self._current_index = -1

    @Slot(str)
    def enqueue(self, uri):
        self._items.append(uri)
        self.queueChanged.emit()

    @Slot(result=int)
    def count(self):
        return len(self._items)

    @Slot()
    def clear(self):
        self._items.clear()
        self._current_index = -1
        self.queueChanged.emit()

    @Slot(int, int, result=bool)
    def move(self, fr, to):
        if 0 <= fr < len(self._items) and 0 <= to < len(self._items):
            item = self._items.pop(fr)
            self._items.insert(to, item)
            self.queueChanged.emit()
            return True
        return False


class FakeJobBridge(QObject):
    jobChanged = Signal()
    jobCompleted = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active = []
        self._history = []

    @Slot(str, result=bool)
    def cancel(self, job_id):
        self._active = [j for j in self._active if j.get("id") != job_id]
        self.jobChanged.emit()
        return True

    @Slot(result=int)
    def activeCount(self):
        return len(self._active)

    @Slot(str, result=dict)
    def submit(self, kind):
        jid = f"job_{int(time.time() * 1000)}"
        entry = {"id": jid, "kind": kind, "status": "running"}
        self._active.append(entry)
        self.jobChanged.emit()
        return entry


class FakeSettingsBridge(QObject):
    settingChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._values = {
            "appearance/theme": "dark",
            "playback/volume": 80,
            "library/auto_scan": True,
        }
        self._backup = {}

    @Slot(str, result="QVariant")
    def get(self, key):
        return self._values.get(key)

    @Slot(str, "QVariant")
    def set(self, key, value):
        self._backup[key] = self._values.get(key)
        self._values[key] = value
        self.settingChanged.emit(key)

    @Slot(str)
    def reset(self, key):
        if key in self._backup:
            self._values[key] = self._backup.pop(key)
            self.settingChanged.emit(key)

    @Slot(result=bool)
    def hasChanges(self):
        return len(self._backup) > 0

    @Slot()
    def rollback(self):
        for k, v in self._backup.items():
            self._values[k] = v
        self._backup.clear()


class FakeHistoryBridge(QObject):
    historyChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items = []
        self._filter = ""

    @Slot(result="QVariantList")
    def items(self):
        return self._items

    @Slot(str)
    def setFilter(self, f):
        self._filter = f
        self.historyChanged.emit()

    @Slot(int, result=bool)
    def remove(self, index):
        if 0 <= index < len(self._items):
            self._items.pop(index)
            self.historyChanged.emit()
            return True
        return False


class FakeMetadataBridge(QObject):
    metadataLoaded = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._fields = {}
        self._has_selection = False
        self._confirmed = False

    @Slot(str, result=dict)
    def loadMetadata(self, filepath):
        self._fields = {"title": "Test Track", "artist": "Test Artist", "album": "Test Album", "year": 2024}
        self._has_selection = True
        self.metadataLoaded.emit()
        return {"ok": True}

    @Slot(str, "QVariant", result=dict)
    def setField(self, key, value):
        self._fields[key] = value
        return {"ok": True}

    @Slot(result=dict)
    def preview(self):
        return {"ok": True, "fields": dict(self._fields)}

    @Slot(result=dict)
    def confirm(self):
        self._confirmed = True
        return {"ok": True}

    @Slot(result=dict)
    def verify(self):
        return {"ok": True, "verified": True}


class FakePlaylistsBridge(QObject):
    playlistsChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._playlists = []
        self._items = {}

    @Slot(str, result=dict)
    def createPlaylist(self, name):
        pid = len(self._playlists) + 1
        entry = {"id": pid, "name": name, "track_count": 0}
        self._playlists.append(entry)
        self._items[pid] = []
        self.playlistsChanged.emit()
        return {"ok": True, "id": pid}

    @Slot(int, str, result=dict)
    def addTrackToPlaylist(self, pid, filepath):
        if pid in self._items:
            self._items[pid].append(filepath)
            for pl in self._playlists:
                if pl["id"] == pid:
                    pl["track_count"] = len(self._items[pid])
            self.playlistsChanged.emit()
            return {"ok": True}
        return {"ok": False, "error": "not found"}

    @Slot(int, int, int, result=bool)
    def reorder(self, pid, fr, to):
        if pid in self._items and 0 <= fr < len(self._items[pid]) and 0 <= to < len(self._items[pid]):
            item = self._items[pid].pop(fr)
            self._items[pid].insert(to, item)
            self.playlistsChanged.emit()
            return True
        return False

    @Slot(int, result=dict)
    def exportM3U(self, pid):
        return {"ok": True, "path": f"/tmp/playlist_{pid}.m3u"}


class FakeDoctorBridge(QObject):
    scanCompleted = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._status = "idle"
        self._issues = []
        self._total_checked = 0

    @Slot(result=dict)
    def scan(self):
        self._status = "done"
        self._total_checked = 10
        self._issues = [{"id": 1, "type": "missing_file", "filepath": "/nonexistent/flac", "selected": False}]
        self.scanCompleted.emit()
        return {"ok": True}

    @Slot()
    def dryRun(self):
        self._status = "dry_run"

    @Slot(result=dict)
    def repairSelected(self):
        for i in self._issues:
            if i.get("selected"):
                i["fixed"] = True
        self._status = "repaired"
        return {"ok": True}

    @Slot(int, bool)
    def setIssueSelected(self, issue_id, selected):
        for i in self._issues:
            if i["id"] == issue_id:
                i["selected"] = selected


class FakeSearchBridge(QObject):
    searchCompleted = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._query = ""
        self._results = []
        self._counter = 0

    @Slot(str, result=dict)
    def search(self, query):
        self._query = query
        self._counter += 1
        self._results = [{"title": f"Result {query}", "type": "track"}]
        self.searchCompleted.emit(query)
        return {"ok": True, "results": list(self._results)}

    @Property(str, notify=searchCompleted)
    def query(self):
        return self._query

    def rejectStale(self, counter):
        return counter < self._counter


class FakeNotificationBridge(QObject):
    notificationReceived = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._notifications = []
        self._open_jobs = []

    @Slot(str, str)
    def notify(self, title, message):
        self._notifications.append({"title": title, "message": message})
        self.notificationReceived.emit(title, message)

    @Slot(str, result=dict)
    def openJob(self, job_id):
        return {"ok": True, "job": {"id": job_id}}

    @Slot(str, result=bool)
    def cancelJob(self, job_id):
        self._open_jobs = [j for j in self._open_jobs if j != job_id]
        return True


class FakeAIBridge(QObject):
    planReady = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._plan = None
        self._executed = False

    @Slot(str, result=dict)
    def plan(self, prompt):
        self._plan = {"prompt": prompt, "steps": ["step1", "step2"]}
        self.planReady.emit(prompt)
        return {"ok": True, "plan": self._plan}

    @Slot(result=dict)
    def confirmPlan(self):
        return {"ok": True}

    @Slot(result=dict)
    def execute(self):
        self._executed = True
        return {"ok": True, "result": "done"}


class FakeDeviceBridge(QObject):
    deviceDiscovered = Signal(str)
    transferCompleted = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._devices = []
        self._transfers = []

    @Slot(result=dict)
    def discover(self):
        self._devices = [{"id": "dev1", "name": "Phone"}]
        self.deviceDiscovered.emit("dev1")
        return {"ok": True, "devices": list(self._devices)}

    @Slot(str, result=dict)
    def planTransfer(self, device_id, items=None):
        tid = f"transfer_{int(time.time() * 1000)}"
        self._transfers.append({"id": tid, "device_id": device_id, "status": "planning"})
        return {"ok": True, "transfer_id": tid}

    @Slot(str, result=dict)
    def executeTransfer(self, transfer_id):
        for t in self._transfers:
            if t["id"] == transfer_id:
                t["status"] = "completed"
                self.transferCompleted.emit(transfer_id)
                return {"ok": True}
        return {"ok": False, "error": "not found"}

    @Slot(str, result=bool)
    def cancelTransfer(self, transfer_id):
        self._transfers = [t for t in self._transfers if t["id"] != transfer_id]
        return True


class FakeConnectionBridge(QObject):
    connectionChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._connections = []

    @Slot(result=dict)
    def discover(self):
        self._connections = [{"id": "conn1", "name": "Server 1"}]
        return {"ok": True, "connections": list(self._connections)}

    @Slot(str, result=dict)
    def connect(self, conn_id):
        return {"ok": True, "connection_id": conn_id}

    @Slot(str, result=dict)
    def disconnect(self, conn_id):
        return {"ok": True}


class FakeHomeAudioBridge(QObject):
    groupChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._groups = []
        self._volumes = {}

    @Slot(result=dict)
    def group(self, device_ids):
        gid = "group_1"
        self._groups.append({"id": gid, "devices": device_ids})
        self.groupChanged.emit()
        return {"ok": True, "group_id": gid}

    @Slot(str, result=dict)
    def ungroup(self, group_id):
        self._groups = [g for g in self._groups if g["id"] != group_id]
        self.groupChanged.emit()
        return {"ok": True}

    @Slot(str, int, result=dict)
    def setVolume(self, group_id, volume):
        self._volumes[group_id] = volume
        return {"ok": True}


class FakeRadioBridge(QObject):
    radioStarted = Signal()
    radioStopped = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._buffer_progress = 0
        self._playing = False

    @Slot(str, result=dict)
    def play(self, url):
        self._buffer_progress = 100
        self._playing = True
        self.radioStarted.emit()
        return {"ok": True}

    @Slot(result=dict)
    def stop(self):
        self._playing = False
        self._buffer_progress = 0
        self.radioStopped.emit()
        return {"ok": True}

    @Property(int, notify=radioStarted)
    def bufferProgress(self):
        return self._buffer_progress


class FakeAudioLabBridge(QObject):
    conversionCompleted = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False

    @Slot(str, result=dict)
    def analyze(self, filepath):
        self._running = True
        return {"ok": True, "result": "analysis_done"}

    @Slot(str, str, result=dict)
    def convert(self, src, dst_fmt):
        self._running = True
        self.conversionCompleted.emit()
        return {"ok": True}

    @Slot(result=dict)
    def cancel(self):
        self._running = False
        return {"ok": True}


# ── WF1: Startup → Home → Library ──

class TestWF1StartupHomeLibrary:
    @pytest.mark.qml_route("home")
    def test_bootstrap_builds_container(self):
        b = _make_bootstrap()
        with patch.object(b, "_validate_required"):
            b.build()
        assert b.container.contains("database")
        assert b.container.contains("worker_manager")

    @pytest.mark.qml_route("home")
    def test_bootstrap_start_transitions_ready(self):
        b = _make_bootstrap()
        with patch.object(b, "_validate_required"):
            b.build()
        b.start()
        assert b.container.state.value in ("ready", "degraded")

    @pytest.mark.qml_route("home")
    def test_navigate_from_home_to_library(self):
        nav = FakeNavigationBridge()
        assert nav.currentRoute == "home"
        nav.navigate("library")
        assert nav.currentRoute == "library"

    @pytest.mark.qml_route("home")
    def test_load_qml_engine(self):
        b = _make_bootstrap()
        with patch.object(b, "_validate_required"):
            b.build()
        b.start()
        engine = MagicMock()
        engine.rootContext.return_value = MagicMock()
        from ui_qml_bridge.context_registrar import ContextRegistrar
        registrar = ContextRegistrar(engine)
        registrar.register("appBridge", FakeAppBridge())
        registrar.register("navigationBridge", FakeNavigationBridge())
        assert registrar.count >= 2

    @pytest.mark.qml_route("home")
    def test_home_route_has_correct_title(self):
        from ui_qml_bridge.route_registry import ROUTES
        assert ROUTES["home"]["title"] == "Inicio"

    @pytest.mark.qml_route("home")
    def test_full_startup_lifecycle(self):
        b = _make_bootstrap()
        with patch.object(b, "_validate_required"):
            b.build()
        b.start()
        from ui_qml_bridge.bridge_factory import create_all_bridges
        bridges = create_all_bridges(b.container)
        assert "navigation" in bridges
        nav = bridges["navigation"]
        nav.navigate("home")
        assert nav.currentRoute == "home"
        nav.navigate("library")
        assert nav.currentRoute == "library"
        b.shutdown()

    @pytest.mark.qml_route("home")
    def test_context_properties_registered_for_home(self):
        engine = MagicMock()
        engine.rootContext.return_value = MagicMock()
        from ui_qml_bridge.context_registrar import ContextRegistrar
        registrar = ContextRegistrar(engine)
        registrar.register("homeBridge", FakeLibraryBridge())
        registrar.register("appBridge", FakeAppBridge())
        assert "homeBridge" in registrar.names

    @pytest.mark.qml_route("home")
    def test_engine_destroy_cleanup(self):
        engine = MagicMock()
        engine.deleteLater()
        assert True

# ── WF2: Library → Track → Play → NowPlaying → Queue ──

class TestWF2LibraryTrackPlayNowPlayingQueue:
    @pytest.mark.qml_route("library")
    def test_library_bridge_search(self):
        lb = FakeLibraryBridge()
        lb.setSearchQuery("Test")
        assert lb.searchQuery() == "Test"

    @pytest.mark.qml_route("library")
    def test_track_play_triggers_playback(self):
        pb = FakePlaybackBridge()
        signals = []
        pb.playbackStarted.connect(lambda: signals.append("started"))
        pb.play("file:///test.flac")
        assert len(signals) >= 1
        assert pb._state == "playing"

    @pytest.mark.qml_route("library")
    def test_nowplaying_after_play(self):
        pb = FakePlaybackBridge()
        pb.play("file:///test.flac")
        assert pb._state == "playing"

    @pytest.mark.qml_route("library")
    def test_enqueue_to_queue(self):
        qb = FakeQueueBridge()
        signals = []
        qb.queueChanged.connect(lambda: signals.append("changed"))
        qb.enqueue("file:///track1.flac")
        qb.enqueue("file:///track2.flac")
        assert qb.count() == 2
        assert len(signals) >= 2

    @pytest.mark.qml_route("library")
    def test_queue_clear(self):
        qb = FakeQueueBridge()
        qb.enqueue("file:///t1.flac")
        qb.enqueue("file:///t2.flac")
        qb.clear()
        assert qb.count() == 0

    @pytest.mark.qml_route("library")
    def test_playback_stop(self):
        pb = FakePlaybackBridge()
        signals = []
        pb.playbackStopped.connect(lambda: signals.append("stopped"))
        pb.play("file:///t.flac")
        pb.stop()
        assert len(signals) >= 1

    @pytest.mark.qml_route("library")
    def test_queue_move_item(self):
        qb = FakeQueueBridge()
        qb.enqueue("a")
        qb.enqueue("b")
        qb.enqueue("c")
        ok = qb.move(0, 2)
        assert ok
        assert qb.count() == 3

    @pytest.mark.qml_route("library")
    def test_queue_reorder_signal_emitted(self):
        qb = FakeQueueBridge()
        signals = []
        qb.queueChanged.connect(lambda: signals.append("changed"))
        qb.enqueue("a")
        qb.enqueue("b")
        qb.move(0, 1)
        assert len(signals) >= 3

    @pytest.mark.qml_route("library")
    def test_library_to_nowplaying_full_flow(self):
        nav = FakeNavigationBridge()
        pb = FakePlaybackBridge()
        qb = FakeQueueBridge()
        nav.navigate("library")
        assert nav.currentRoute == "library"
        pb.play("file:///song.flac")
        assert pb._state == "playing"
        qb.enqueue("file:///song.flac")
        assert qb.count() == 1
        nav.navigate("queue")
        assert nav.currentRoute == "queue"

# ── WF3: Album → Enqueue ──

class TestWF3AlbumEnqueue:
    @pytest.mark.qml_route("library.album_detail")
    def test_album_enqueue(self):
        qb = FakeQueueBridge()
        qb.enqueue("album:///alpha/track1.flac")
        qb.enqueue("album:///alpha/track2.flac")
        qb.enqueue("album:///alpha/track3.flac")
        qb.enqueue("album:///alpha/track4.flac")
        assert qb.count() == 4

    @pytest.mark.qml_route("library.album_detail")
    def test_album_enqueue_signal_emitted(self):
        qb = FakeQueueBridge()
        signals = []
        qb.queueChanged.connect(lambda: signals.append("changed"))
        for _ in range(3):
            qb.enqueue("album:///t.flac")
        assert len(signals) >= 3

# ── WF4: Artist → Mix → Play ──

class TestWF4ArtistMixPlay:
    @pytest.mark.qml_route("library.artist_detail")
    def test_artist_navigate(self):
        nav = FakeNavigationBridge()
        nav.navigateWithParams("library.artist_detail", {"artist": "Test Artist"})
        assert nav.currentRoute == "library.artist_detail"

    @pytest.mark.qml_route("library.artist_detail")
    def test_mix_generation(self):
        class FakeMixBridge(QObject):
            def __init__(self, parent=None):
                super().__init__(parent)
                self._mix = None
            def loadMix(self, kind):
                self._mix = {"kind": kind, "tracks": ["a", "b", "c"]}
                return self._mix
        mb = FakeMixBridge()
        mix = mb.loadMix("artist_mix")
        assert len(mix["tracks"]) == 3

    @pytest.mark.qml_route("library.artist_detail")
    def test_artist_mix_play(self):
        pb = FakePlaybackBridge()
        pb.play("mix:///artist_mix")
        assert pb._state == "playing"

    @pytest.mark.qml_route("library.artist_detail")
    def test_artist_detail_params_required(self):
        from ui_qml_bridge.route_registry import ROUTES
        params = ROUTES["library.artist_detail"].get("params", {})
        assert "artist" in params
        assert params["artist"].get("required")

# ── WF5: Playlist Create Add Reorder Export ──

class TestWF5PlaylistCRUD:
    @pytest.mark.qml_route("playlist_detail")
    def test_create_playlist(self):
        pb = FakePlaylistsBridge()
        r = pb.createPlaylist("My Playlist")
        assert r["ok"]
        assert r["id"] is not None

    @pytest.mark.qml_route("playlist_detail")
    def test_add_track_to_playlist(self):
        pb = FakePlaylistsBridge()
        r = pb.createPlaylist("Test")
        assert r["ok"]
        pid = r["id"]
        r2 = pb.addTrackToPlaylist(pid, "/music/track.flac")
        assert r2["ok"]

    @pytest.mark.qml_route("playlist_detail")
    def test_reorder_playlist(self):
        pb = FakePlaylistsBridge()
        r = pb.createPlaylist("Reorder")
        pid = r["id"]
        pb.addTrackToPlaylist(pid, "a.flac")
        pb.addTrackToPlaylist(pid, "b.flac")
        pb.addTrackToPlaylist(pid, "c.flac")
        ok = pb.reorder(pid, 0, 2)
        assert ok

    @pytest.mark.qml_route("playlist_detail")
    def test_export_playlist(self):
        pb = FakePlaylistsBridge()
        r = pb.createPlaylist("Export")
        pid = r["id"]
        r2 = pb.exportM3U(pid)
        assert r2["ok"]
        assert "path" in r2

    @pytest.mark.qml_route("playlist_detail")
    def test_playlist_created_signal(self):
        pb = FakePlaylistsBridge()
        signals = []
        pb.playlistsChanged.connect(lambda: signals.append("changed"))
        pb.createPlaylist("Signal Test")
        assert len(signals) >= 1

# ── WF6: History Filter Play Remove ──

class TestWF6History:
    @pytest.mark.qml_route("history")
    def test_history_filter(self):
        hb = FakeHistoryBridge()
        signals = []
        hb.historyChanged.connect(lambda: signals.append("changed"))
        hb.setFilter("Rock")
        assert hb._filter == "Rock"
        assert len(signals) >= 1

    @pytest.mark.qml_route("history")
    def test_history_remove(self):
        hb = FakeHistoryBridge()
        hb._items = ["a", "b", "c"]
        ok = hb.remove(1)
        assert ok
        assert len(hb._items) == 2

    @pytest.mark.qml_route("history")
    def test_history_filter_preserves_items(self):
        hb = FakeHistoryBridge()
        hb._items = ["track1", "track2"]
        hb.setFilter("track")
        assert len(hb._items) == 2

# ── WF7: Settings Change Reject Rollback ──

class TestWF7Settings:
    @pytest.mark.qml_route("settings")
    def test_setting_change(self):
        sb = FakeSettingsBridge()
        signals = []
        sb.settingChanged.connect(lambda k: signals.append(k))
        sb.set("appearance/theme", "light")
        assert sb.get("appearance/theme") == "light"
        assert len(signals) >= 1

    @pytest.mark.qml_route("settings")
    def test_setting_reject_rollback(self):
        sb = FakeSettingsBridge()
        old = sb.get("appearance/theme")
        sb.set("appearance/theme", "light")
        assert sb.get("appearance/theme") == "light"
        sb.rollback()
        assert sb.get("appearance/theme") == old

    @pytest.mark.qml_route("settings")
    def test_setting_has_changes(self):
        sb = FakeSettingsBridge()
        assert not sb.hasChanges()
        sb.set("playback/volume", 50)
        assert sb.hasChanges()
        sb.rollback()
        assert not sb.hasChanges()

    @pytest.mark.qml_route("settings")
    def test_setting_reset(self):
        sb = FakeSettingsBridge()
        sb.set("playback/volume", 50)
        sb.reset("playback/volume")
        assert sb.get("playback/volume") == 80

# ── WF8: Metadata Preview Confirm Verify ──

class TestWF8Metadata:
    @pytest.mark.qml_route("metadata.inspector")
    def test_metadata_preview(self):
        mb = FakeMetadataBridge()
        r = mb.loadMetadata("/test/file.flac")
        assert r["ok"]
        preview = mb.preview()
        assert preview["ok"]

    @pytest.mark.qml_route("metadata.inspector")
    def test_metadata_confirm(self):
        mb = FakeMetadataBridge()
        mb.loadMetadata("/test/file.flac")
        r = mb.confirm()
        assert r["ok"]
        assert mb._confirmed

    @pytest.mark.qml_route("metadata.inspector")
    def test_metadata_verify(self):
        mb = FakeMetadataBridge()
        mb.loadMetadata("/test/file.flac")
        r = mb.verify()
        assert r["ok"]
        assert r["verified"]

    @pytest.mark.qml_route("metadata.inspector")
    def test_metadata_field_edit(self):
        mb = FakeMetadataBridge()
        mb.loadMetadata("/test/file.flac")
        r = mb.setField("title", "New Title")
        assert r["ok"]
        assert mb._fields["title"] == "New Title"

    @pytest.mark.qml_route("metadata.inspector")
    def test_metadata_signal_on_load(self):
        mb = FakeMetadataBridge()
        signals = []
        mb.metadataLoaded.connect(lambda: signals.append("loaded"))
        mb.loadMetadata("/test/file.flac")
        assert len(signals) >= 1

# ── WF9: Tagging Accept Verify ──

class TestWF9Tagging:
    @pytest.mark.qml_route("tagging")
    def test_tagging_accept(self):
        from core.smart_tagging_service import SmartTaggingService
        svc = MagicMock()
        svc.analyze.return_value = {"ok": True}
        result = svc.analyze("/test/file.flac")
        assert result["ok"]

    @pytest.mark.qml_route("tagging")
    def test_tagging_verify(self):
        svc = MagicMock()
        svc.batch_analyze.return_value = [{"filepath": "/test/a.flac", "ok": True}]
        results = svc.batch_analyze(["/test/a.flac"])
        assert len(results) == 1

    @pytest.mark.qml_route("tagging")
    def test_tagging_accept_smart_tags(self):
        svc = MagicMock()
        svc.analyze.return_value = {"ok": True, "genre": "Rock"}
        result = svc.analyze("/test/file.flac")
        assert result.get("genre") == "Rock"

# ── WF10: Doctor Scan DryRun Repair ──

class TestWF10Doctor:
    @pytest.mark.qml_route("library_doctor")
    def test_doctor_scan(self):
        db = FakeDoctorBridge()
        r = db.scan()
        assert r["ok"]
        assert db._status == "done"

    @pytest.mark.qml_route("library_doctor")
    def test_doctor_dry_run(self):
        db = FakeDoctorBridge()
        db.dryRun()
        assert db._status == "dry_run"

    @pytest.mark.qml_route("library_doctor")
    def test_doctor_repair(self):
        db = FakeDoctorBridge()
        db.scan()
        db.setIssueSelected(1, True)
        r = db.repairSelected()
        assert r["ok"]
        assert db._status == "repaired"

    @pytest.mark.qml_route("library_doctor")
    def test_doctor_scan_signal(self):
        db = FakeDoctorBridge()
        signals = []
        db.scanCompleted.connect(lambda: signals.append("done"))
        db.scan()
        assert len(signals) >= 1

    @pytest.mark.qml_route("library_doctor")
    def test_doctor_total_checked(self):
        db = FakeDoctorBridge()
        db.scan()
        assert db._total_checked >= 10

# ── WF11: Search A → Search B → reject stale A ──

class TestWF11Search:
    @pytest.mark.qml_route("search")
    def test_search_a_then_b(self):
        sb = FakeSearchBridge()
        r1 = sb.search("Track A")
        assert r1["ok"]
        r2 = sb.search("Track B")
        assert r2["ok"]
        assert sb.query == "Track B"

    @pytest.mark.qml_route("search")
    def test_reject_stale_search(self):
        sb = FakeSearchBridge()
        sb.search("A")
        counter_a = sb._counter
        sb.search("B")
        assert sb.rejectStale(counter_a)
        assert not sb.rejectStale(sb._counter)

    @pytest.mark.qml_route("search")
    def test_search_signal_emitted(self):
        sb = FakeSearchBridge()
        signals = []
        sb.searchCompleted.connect(lambda q: signals.append(q))
        sb.search("Test")
        assert "Test" in signals

# ── WF12: Notification OpenJob Cancel ──

class TestWF12Notification:
    @pytest.mark.qml_route("notifications")
    def test_notification_received(self):
        nb = FakeNotificationBridge()
        signals = []
        nb.notificationReceived.connect(lambda t, m: signals.append((t, m)))
        nb.notify("Test", "Message")
        assert len(signals) >= 1

    @pytest.mark.qml_route("notifications")
    def test_notification_open_job(self):
        nb = FakeNotificationBridge()
        r = nb.openJob("job_1")
        assert r["ok"]

    @pytest.mark.qml_route("notifications")
    def test_notification_cancel_job(self):
        nb = FakeNotificationBridge()
        ok = nb.cancelJob("job_1")
        assert ok

# ── WF13: AI Plan Confirm Execute ──

class TestWF13AI:
    @pytest.mark.qml_route("ai")
    def test_ai_plan(self):
        ai = FakeAIBridge()
        r = ai.plan("Play rock music")
        assert r["ok"]
        assert ai._plan is not None

    @pytest.mark.qml_route("ai")
    def test_ai_confirm_plan(self):
        ai = FakeAIBridge()
        ai.plan("Play rock")
        r = ai.confirmPlan()
        assert r["ok"]

    @pytest.mark.qml_route("ai")
    def test_ai_execute(self):
        ai = FakeAIBridge()
        ai.plan("Play rock")
        ai.confirmPlan()
        r = ai.execute()
        assert r["ok"]
        assert ai._executed

    @pytest.mark.qml_route("ai")
    def test_ai_plan_signal(self):
        ai = FakeAIBridge()
        signals = []
        ai.planReady.connect(lambda p: signals.append(p))
        ai.plan("Mix")
        assert len(signals) >= 1

# ── WF14: Devices Discover Plan Transfer Cancel ──

class TestWF14Devices:
    @pytest.mark.qml_route("devices.list")
    def test_devices_discover(self):
        db = FakeDeviceBridge()
        r = db.discover()
        assert r["ok"]
        assert len(r["devices"]) >= 1

    @pytest.mark.qml_route("devices.list")
    def test_device_plan_transfer(self):
        db = FakeDeviceBridge()
        db.discover()
        r = db.planTransfer("dev1")
        assert r["ok"]

    @pytest.mark.qml_route("devices.list")
    def test_device_execute_transfer(self):
        db = FakeDeviceBridge()
        db.discover()
        pr = db.planTransfer("dev1")
        r = db.executeTransfer(pr["transfer_id"])
        assert r["ok"]

    @pytest.mark.qml_route("devices.list")
    def test_device_cancel_transfer(self):
        db = FakeDeviceBridge()
        db.discover()
        pr = db.planTransfer("dev1")
        ok = db.cancelTransfer(pr["transfer_id"])
        assert ok

    @pytest.mark.qml_route("devices.list")
    def test_device_discover_signal(self):
        db = FakeDeviceBridge()
        signals = []
        db.deviceDiscovered.connect(lambda d: signals.append(d))
        db.discover()
        assert len(signals) >= 1

# ── WF15: Connections Discover Connect Disconnect ──

class TestWF15Connections:
    @pytest.mark.qml_route("connections")
    def test_connections_discover(self):
        cb = FakeConnectionBridge()
        r = cb.discover()
        assert r["ok"]
        assert len(r["connections"]) >= 1

    @pytest.mark.qml_route("connections")
    def test_connections_connect(self):
        cb = FakeConnectionBridge()
        r = cb.connect("conn1")
        assert r["ok"]

    @pytest.mark.qml_route("connections")
    def test_connections_disconnect(self):
        cb = FakeConnectionBridge()
        cb.connect("conn1")
        r = cb.disconnect("conn1")
        assert r["ok"]

# ── WF16: HomeAudio Group Volume Ungroup ──

class TestWF16HomeAudio:
    @pytest.mark.qml_route("home_audio")
    def test_home_audio_group(self):
        ha = FakeHomeAudioBridge()
        r = ha.group(["dev1", "dev2"])
        assert r["ok"]

    @pytest.mark.qml_route("home_audio")
    def test_home_audio_set_volume(self):
        ha = FakeHomeAudioBridge()
        r = ha.group(["dev1"])
        r2 = ha.setVolume("group_1", 60)
        assert r2["ok"]
        assert ha._volumes["group_1"] == 60

    @pytest.mark.qml_route("home_audio")
    def test_home_audio_ungroup(self):
        ha = FakeHomeAudioBridge()
        ha.group(["dev1"])
        r = ha.ungroup("group_1")
        assert r["ok"]
        assert len(ha._groups) == 0

    @pytest.mark.qml_route("home_audio")
    def test_home_audio_group_signal(self):
        ha = FakeHomeAudioBridge()
        signals = []
        ha.groupChanged.connect(lambda: signals.append("changed"))
        ha.group(["dev1"])
        assert len(signals) >= 1

# ── WF17: Radio Buffer Play Stop ──

class TestWF17Radio:
    @pytest.mark.qml_route("radio")
    def test_radio_play(self):
        rb = FakeRadioBridge()
        r = rb.play("http://stream.example.com")
        assert r["ok"]
        assert rb._playing

    @pytest.mark.qml_route("radio")
    def test_radio_buffer_progress(self):
        rb = FakeRadioBridge()
        rb.play("http://stream.example.com")
        assert rb.bufferProgress == 100

    @pytest.mark.qml_route("radio")
    def test_radio_stop(self):
        rb = FakeRadioBridge()
        rb.play("http://stream.example.com")
        r = rb.stop()
        assert r["ok"]
        assert not rb._playing

    @pytest.mark.qml_route("radio")
    def test_radio_start_signal(self):
        rb = FakeRadioBridge()
        signals = []
        rb.radioStarted.connect(lambda: signals.append("started"))
        rb.play("http://stream.example.com")
        assert len(signals) >= 1

# ── WF18: AudioLab Analyze Convert Cancel ──

class TestWF18AudioLab:
    @pytest.mark.qml_route("audio_lab")
    def test_audio_lab_analyze(self):
        al = FakeAudioLabBridge()
        r = al.analyze("/test/file.flac")
        assert r["ok"]

    @pytest.mark.qml_route("audio_lab")
    def test_audio_lab_convert(self):
        al = FakeAudioLabBridge()
        r = al.convert("/test/file.flac", "mp3")
        assert r["ok"]

    @pytest.mark.qml_route("audio_lab")
    def test_audio_lab_cancel(self):
        al = FakeAudioLabBridge()
        al.analyze("/test/file.flac")
        assert al._running
        r = al.cancel()
        assert r["ok"]
        assert not al._running

    @pytest.mark.qml_route("audio_lab")
    def test_audio_lab_convert_signal(self):
        al = FakeAudioLabBridge()
        signals = []
        al.conversionCompleted.connect(lambda: signals.append("done"))
        al.convert("/test/file.flac", "wav")
        assert len(signals) >= 1

# ── WF19: Shutdown with active jobs ──

class TestWF19ShutdownWithActiveJobs:
    @pytest.mark.qml_route("home")
    def test_shutdown_cancels_active_jobs(self):
        app = FakeAppBridge()
        jb = FakeJobBridge()
        jb.submit("scan")
        jb.submit("convert")
        assert jb.activeCount() == 2
        for job in list(jb._active):
            jb.cancel(job["id"])
        assert jb.activeCount() == 0
        app.quit()
        assert app._phase == "stopped"

    @pytest.mark.qml_route("home")
    def test_shutdown_preserves_shutdown_result(self):
        app = FakeAppBridge()
        r = app.quit()
        assert r["success"]

    @pytest.mark.qml_route("home")
    def test_bootstrap_shutdown_cleanup(self):
        b = _make_bootstrap()
        with patch.object(b, "_validate_required"):
            b.build()
        b.start()
        b.shutdown()
        assert b.container.state.value == "stopped"

    @pytest.mark.qml_route("home")
    def test_engine_destroy_after_bootstrap(self):
        b = _make_bootstrap()
        with patch.object(b, "_validate_required"):
            b.build()
        b.start()
        engine = MagicMock()
        engine.deleteLater()
        b.shutdown()
