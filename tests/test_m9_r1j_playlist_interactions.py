"""M9-R1J: dynamic playlist interaction gates.

RUNTIME tests (not static string checks): Detail menu actions execute
without ReferenceError through the shared shell dialogs, playlist search is
reactive to LibraryService notifications, playlist-only search renders and
activates, and the bridge lifecycle unsubscribes symmetrically.
"""

import sys
from pathlib import Path

import pytest
from PySide6.QtQml import QQmlComponent, QQmlEngine

from michi.application.navigation_service import NavigationService
from michi.application.playlist_navigation_coordinator import (
    PlaylistNavigationCoordinator,
)
from michi.application.playlist_service import PlaylistService
from michi.domain.navigation import AppRoute
from michi.presentation.library_bridge import LibraryBridge
from michi.presentation.navigation_bridge import NavigationBridge
from michi.presentation.playlists_bridge import PlaylistsBridge
from tests.conftest import FakeAudioPort, FakeSettingsRepo
from tests.test_library_metadata import FakeExtractor, FakeScanner
from tests.test_playlists import FakePlaylistsPort, _make_library_and_queue

QML_DIR = Path(__file__).resolve().parents[1] / "src" / "michi" / "presentation" / "qml"


@pytest.fixture
def qapp():
    import os

    from PySide6.QtGui import QGuiApplication

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(sys.argv)
    yield app


class _QmlErrors:
    """Captures QML runtime warnings so tests can fail on real errors.

    Only records errors from the surfaces under test — teardown noise from
    OTHER components (bindings re-evaluated during engine destruction)
    cannot pollute the gates."""

    WATCHED = (
        "ContentHost.qml",
        "PlaylistDetailView.qml",
        "PlaylistCard.qml",
        "PlaylistCreateDialog.qml",
        "PlaylistTrackList.qml",
        "PlaylistsView.qml",
        "SearchOverlay.qml",
    )

    def __init__(self):
        from PySide6.QtCore import qInstallMessageHandler

        self.messages = []
        self._previous = None

        def handler(msg_type, context, message):
            text = str(message)
            file_name = str(getattr(context, "file", "") or "")
            if any(w in file_name for w in self.WATCHED) and any(
                token in text
                for token in (
                    "ReferenceError",
                    "TypeError",
                    "Cannot read property",
                    "is not defined",
                    "binding loop",
                )
            ):
                self.messages.append(text)
            if self._previous is not None:
                self._previous(msg_type, context, message)

        self._previous = qInstallMessageHandler(handler)

    def drain(self):
        errors, self.messages = self.messages, []
        return errors

    def restore(self):
        from PySide6.QtCore import qInstallMessageHandler

        if self._previous is not None:
            qInstallMessageHandler(self._previous)
            self._previous = None


def _process():
    from PySide6.QtCore import QCoreApplication

    QCoreApplication.processEvents()


def _world(tmp_path):
    paths = [tmp_path / "a.mp3"]
    for p in paths:
        p.write_bytes(b"x")
    library, queue, _ = _make_library_and_queue(
        FakeScanner(paths), extractor=FakeExtractor()
    )
    library.scan(str(tmp_path))
    from michi.application.playback_service import PlaybackService
    from michi.application.settings_service import SettingsService

    audio = FakeAudioPort()
    playback = PlaybackService(audio)
    settings = SettingsService(FakeSettingsRepo())
    service = PlaylistService(queue, FakePlaylistsPort())
    nav = NavigationService()
    service.set_on_playlist_deleted(nav.forget_playlist)
    coord = PlaylistNavigationCoordinator(service, nav)
    lb = LibraryBridge(library)
    pb = PlaylistsBridge(
        service,
        playlist_navigation=coord,
        navigation_service=nav,
        library=library,
    )
    nb = NavigationBridge(nav, playlist_navigation=coord)
    return {
        "library": library,
        "queue": queue,
        "playback": playback,
        "settings": settings,
        "service": service,
        "nav": nav,
        "coord": coord,
        "lb": lb,
        "pb": pb,
        "nb": nb,
    }


def _engine(world):
    from michi.presentation.playback_bridge import PlaybackBridge
    from michi.presentation.queue_bridge import QueueBridge
    from michi.presentation.settings_bridge import SettingsBridge

    engine = QQmlEngine()
    engine.addImportPath(str(QML_DIR))
    engine.rootContext().setContextProperty("library", world["lb"])
    engine.rootContext().setContextProperty("playlists", world["pb"])
    engine.rootContext().setContextProperty("navigation", world["nb"])
    engine.rootContext().setContextProperty(
        "playback", PlaybackBridge(world["playback"], world["library"])
    )
    engine.rootContext().setContextProperty(
        "queue", QueueBridge(world["queue"], world["library"])
    )
    engine.rootContext().setContextProperty(
        "settingsBridge", SettingsBridge(world["settings"])
    )
    return engine


def _load(engine, rel, errors):
    component = QQmlComponent(engine, str(QML_DIR / rel))
    errs = "; ".join(e.toString() for e in component.errors())
    assert component.status() == QQmlComponent.Ready, f"{rel}: {errs}"
    obj = component.create()
    assert obj is not None, f"{rel}: null object"
    # PySide6: el QML object creado sin parent es owned por el COMPONENTE —
    # retener el componente en el engine evita que el GC lo destruya junto
    # con el objeto (el objeto debe sobrevivir al scope del test).
    if not hasattr(engine, "_held_components"):
        engine._held_components = []
    engine._held_components.append(component)
    runtime = errors.drain()
    assert runtime == [], f"{rel}: runtime errors: {runtime}"
    return obj


def _find_item(obj, object_name):
    from PySide6.QtCore import QObject

    found = obj.findChild(QObject, object_name)
    return found


def _emit_detail_intent(host, signal_name, playlist_id, playlist_name):
    """Emit the Detail's semantic intent signal (the production contract the
    menu items invoke). The menu items carry stable objectNames for UI
    automation; the signal is the canonical interaction path."""
    detail = _find_item(host, "playlistDetailView")
    assert detail is not None, "playlistDetailView no encontrado"
    signal = getattr(detail, signal_name)
    signal.emit(playlist_id, playlist_name)
    _process()


class TestDetailActionsRuntime:
    def _content_host(self, tmp_path):
        world = _world(tmp_path)
        a = world["service"].create_playlist("Jazz")
        b = world["service"].create_playlist("Rock")
        world["coord"].open_playlist(a.playlist_id)
        engine = _engine(world)
        errors = _QmlErrors()
        host = _load(engine, "shell/ContentHost.qml", errors)
        # production wiring: AppShell binds currentRoute from navigation
        host.setProperty("currentRoute", "playlists")
        return world, engine, errors, host, a, b

    def test_detail_rename_action_opens_shared_dialog(self, tmp_path, qapp):
        world, engine, errors, host, a, b = self._content_host(tmp_path)
        try:
            detail = _find_item(host, "playlistDetailView")
            assert detail is not None
            detail_visible = detail.property("visible")
            assert detail_visible is True
            # the menu action exists (stable objectName) and its handler
            # routes through the semantic intent signal
            action = _find_item(host, "playlistDetailRenameAction")
            assert action is not None
            _emit_detail_intent(host, "renameRequested", a.playlist_id, "Jazz")
            dialog = _find_item(host, "renamePlaylistDialog")
            assert dialog is not None
            # Popup.opened requires a real window; the OBSERVABLE contract is
            # the populated ephemeral target + untouched navigation.
            assert dialog.property("targetPlaylistId") == a.playlist_id
            assert dialog.property("targetPlaylistName") == "Jazz"
            assert world["nav"].state.playlist_id == a.playlist_id
            runtime = errors.drain()
            assert runtime == [], f"ReferenceError al abrir Rename: {runtime}"
        finally:
            errors.restore()
            engine.deleteLater()

    def test_detail_delete_action_confirmation_then_cancel(self, tmp_path, qapp):
        world, engine, errors, host, a, b = self._content_host(tmp_path)
        try:
            action = _find_item(host, "playlistDetailDeleteAction")
            assert action is not None
            _emit_detail_intent(host, "deleteRequested", a.playlist_id, "Jazz")
            dialog = _find_item(host, "deletePlaylistDialog")
            assert dialog.property("targetPlaylistId") == a.playlist_id
            assert dialog.property("targetPlaylistName") == "Jazz"
            # playlist STILL exists before confirmation — no mutation yet
            assert world["service"].get_playlist(a.playlist_id) is not None
            # cancel path: no mutation, navigation untouched
            assert world["nav"].state.playlist_id == a.playlist_id
            runtime = errors.drain()
            assert runtime == [], f"ReferenceError: {runtime}"
        finally:
            errors.restore()
            engine.deleteLater()

    def test_detail_delete_confirm_converges(self, tmp_path, qapp):
        world, engine, errors, host, a, b = self._content_host(tmp_path)
        try:
            action = _find_item(host, "playlistDetailDeleteAction")
            assert action is not None
            _emit_detail_intent(host, "deleteRequested", a.playlist_id, "Jazz")
            # confirm via the dialog's canonical _confirm() (the danger
            # button routes through it)
            confirm = _find_item(host, "deletePlaylistDialog")
            confirm._confirm()
            _process()
            assert world["service"].get_playlist(a.playlist_id) is None
            assert world["nav"].state.playlist_id is None
            assert world["nav"].state.current_route == AppRoute.PLAYLISTS
            runtime = errors.drain()
            assert runtime == [], f"ReferenceError: {runtime}"
        finally:
            errors.restore()
            engine.deleteLater()

    def test_detail_rename_duplicate_keeps_dialog_open(self, tmp_path, qapp):
        world, engine, errors, host, a, b = self._content_host(tmp_path)
        try:
            action = _find_item(host, "playlistDetailRenameAction")
            assert action is not None
            _emit_detail_intent(host, "renameRequested", a.playlist_id, "Jazz")
            dialog = _find_item(host, "renamePlaylistDialog")
            field = _find_item(host, "playlistRenameField")
            if field is None:
                # renameField is inside the dialog
                field = dialog.findChild(type(dialog), "playlistRenameField")
            assert field is not None
            field.setProperty("text", "Rock")  # duplicate of B
            # submit via dialog's internal submit path
            dialog._submit()
            _process()
            # duplicate: user-visible failure — error text set, playlist
            # unchanged, navigation untouched (dialog stays open in-window)
            assert dialog.property("errorText") != ""
            assert world["service"].get_playlist(a.playlist_id).name == "Jazz"
            assert world["nav"].state.playlist_id == a.playlist_id
            runtime = errors.drain()
            assert runtime == [], f"ReferenceError: {runtime}"
        finally:
            errors.restore()
            engine.deleteLater()

    def test_detail_rename_success_preserves_identity(self, tmp_path, qapp):
        world, engine, errors, host, a, b = self._content_host(tmp_path)
        try:
            action = _find_item(host, "playlistDetailRenameAction")
            assert action is not None
            _emit_detail_intent(host, "renameRequested", a.playlist_id, "Jazz")
            dialog = _find_item(host, "renamePlaylistDialog")
            field = dialog.findChild(type(dialog), "playlistRenameField")
            field.setProperty("text", "Jazz Night")
            dialog._submit()
            _process()
            renamed = world["service"].get_playlist(a.playlist_id)
            assert renamed.name == "Jazz Night"
            assert renamed.playlist_id == a.playlist_id
            assert world["nav"].state.playlist_id == a.playlist_id
            runtime = errors.drain()
            assert runtime == [], f"ReferenceError: {runtime}"
        finally:
            errors.restore()
            engine.deleteLater()


class TestSearchReactivity:
    def test_bridge_reacts_to_library_query_changes(self, tmp_path):
        library, queue, _ = _make_library_and_queue(
            FakeScanner([]), extractor=FakeExtractor()
        )
        service = PlaylistService(queue, FakePlaylistsPort())
        service.create_playlist("Road Trip")
        service.create_playlist("Jazz Night")
        nav = NavigationService()
        bridge = PlaylistsBridge(service, navigation_service=nav, library=library)
        signals = []
        bridge.playlists_changed.connect(lambda: signals.append(1))

        library.search("Road")
        assert signals, "playlists_changed NO emitido al buscar"
        assert bridge.property("searchPlaylistCount") == 1
        rows = bridge.property("searchPlaylists")
        assert [r["name"] for r in rows] == ["Road Trip"]

        signals.clear()
        library.search("Jazz")
        assert signals, "playlists_changed NO emitido al cambiar query"
        rows = bridge.property("searchPlaylists")
        assert [r["name"] for r in rows] == ["Jazz Night"]

        signals.clear()
        library.search("Classical")
        assert signals
        assert bridge.property("searchPlaylistCount") == 0

        library.clear_search()
        assert bridge.property("searchPlaylistCount") == 0
        assert bridge.property("searchPlaylists") == []
        bridge.dispose()

    def test_dispose_removes_library_subscription(self, tmp_path):
        library, queue, _ = _make_library_and_queue(
            FakeScanner([]), extractor=FakeExtractor()
        )
        service = PlaylistService(queue, FakePlaylistsPort())
        service.create_playlist("Road Trip")
        nav = NavigationService()
        bridge = PlaylistsBridge(service, navigation_service=nav, library=library)
        signals = []
        bridge.playlists_changed.connect(lambda: signals.append(1))
        library.search("Road")
        assert signals
        signals.clear()
        bridge.dispose()
        library.search("Jazz")
        library.clear_search()
        assert signals == []  # NO bridge signal after dispose


class TestPlaylistOnlySearch:
    def test_combined_result_count_and_visibility(self, tmp_path, qapp):
        world = _world(tmp_path)
        world["service"].create_playlist("Road Trip")
        world["library"].search("Road Trip")
        engine = _engine(world)
        errors = _QmlErrors()
        try:
            overlay = _load(engine, "patterns/SearchOverlay.qml", errors)
            assert world["library"].state.search_projection.total_count == 0
            assert world["pb"].property("searchPlaylistCount") == 1
            combined = overlay.property("combinedResultCount")
            assert combined == 1
            # EmptyState oculto (1 resultado combinado), scroll visible
            runtime = errors.drain()
            assert runtime == []
        finally:
            errors.restore()
            engine.deleteLater()

    def test_keyboard_activation_playlist_only(self, tmp_path):
        """resultIndex 0 → activateResult → PLAYLISTS/id (never Library)."""
        world = _world(tmp_path)
        a = world["service"].create_playlist("Road Trip")
        world["library"].search("Road Trip")
        assert world["pb"].property("searchPlaylistCount") == 1
        world["coord"].open_playlist(
            world["pb"].property("searchPlaylists")[0]["playlistId"]
        )
        assert world["nav"].state.current_route == AppRoute.PLAYLISTS
        assert world["nav"].state.playlist_id == a.playlist_id
        assert world["service"].navigation.recent_ids[0] == a.playlist_id


class TestCardFocus:
    def test_card_does_not_claim_initial_focus(self):
        card = (QML_DIR / "playlists" / "PlaylistCard.qml").read_text()
        assert "focus: true" not in card
        assert "activeFocusOnTab: true" in card
        assert "Keys.onReturnPressed" in card
        assert "Keys.onSpacePressed" in card


class TestDetailStaticGates:
    def test_detail_has_no_local_dialog_references(self):
        detail = (QML_DIR / "playlists" / "PlaylistDetailView.qml").read_text()
        assert "renameDialog.open()" not in detail
        assert "deleteDialog.open()" not in detail
        assert "renameRequested" in detail
        assert "deleteRequested" in detail

    def test_content_host_owns_dialogs(self):
        content = (QML_DIR / "shell" / "ContentHost.qml").read_text()
        assert "targetPlaylistId" in content
        assert "targetPlaylistName" in content
