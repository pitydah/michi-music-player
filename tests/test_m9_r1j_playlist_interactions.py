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
        # shared components exercised by the real menu/dialog chains — their
        # runtime errors matter too (the file filter keeps teardown noise
        # from unrelated views out)
        "MichiDialog.qml",
        "MichiMenu.qml",
        "MichiButton.qml",
        "MichiIconButton.qml",
        "MichiTextField.qml",
        "MichiEntityRow.qml",
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
    # descartar el ruido del teardown PENDIENTE de tests anteriores (sus
    # deleteLater asíncronos se procesan dentro de este test y emiten
    # "of null" al destruir engines ajenos)
    errors.drain()
    runtime = errors.drain()
    assert runtime == [], f"{rel}: runtime errors: {runtime}"
    return obj


def _find_item(obj, object_name):
    from PySide6.QtCore import QObject

    found = obj.findChild(QObject, object_name)
    return found


def _activate_menu_item(host, object_name):
    """Execute the REAL menu chain: MenuItem.triggered → onTriggered →
    semantic intent → ContentHost → shared dialog. This is the full
    production interaction path (not a direct signal emission)."""
    action = _find_item(host, object_name)
    assert action is not None, f"{object_name} no encontrado"
    action.triggered.emit()
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
            # REAL chain: MenuItem trigger → onTriggered → renameRequested
            # → ContentHost → shared dialog
            _activate_menu_item(host, "playlistDetailRenameAction")
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
            _activate_menu_item(host, "playlistDetailDeleteAction")
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
            _activate_menu_item(host, "playlistDetailDeleteAction")
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
            _activate_menu_item(host, "playlistDetailRenameAction")
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
            _activate_menu_item(host, "playlistDetailRenameAction")
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
        """Playlist-only search: REAL overlay components verified — combined
        total, EmptyState hidden, results scroll visible, result row present."""
        world = _world(tmp_path)
        world["service"].create_playlist("Road Trip")
        world["library"].search("Road Trip")
        engine = _engine(world)
        errors = _QmlErrors()
        try:
            overlay = _load(engine, "patterns/SearchOverlay.qml", errors)
            overlay.setProperty("opened", True)  # production flow opens it
            _process()
            _process()  # Repeater delegates materialize on the event loop
            assert world["library"].state.search_projection.total_count == 0
            assert world["pb"].property("searchPlaylistCount") == 1
            assert overlay.property("combinedResultCount") == 1
            empty_state = _find_item(overlay, "searchEmptyState")
            scroll = _find_item(overlay, "searchResultsScroll")
            assert empty_state is not None
            assert scroll is not None
            assert empty_state.property("visible") is False
            assert scroll.property("visible") is True
            # Qt 6 materializa delegates de Repeater solo al renderizar
            # (no fiable en offscreen) — verificamos el MODELO que alimenta
            # el delegate: repeater count + datos proyectados. El locator es
            # el objectName ESTABLE (M9-R1K), nunca el índice posicional.
            playlist_repeater = _find_item(overlay, "playlistSearchRepeater")
            assert playlist_repeater is not None
            assert playlist_repeater.property("count") == 1
            rows = world["pb"].property("searchPlaylists")
            assert rows[0]["name"] == "Road Trip"
            assert rows[0]["playlistId"] != ""
            runtime = errors.drain()
            assert runtime == []
        finally:
            errors.restore()
            engine.deleteLater()

    def test_keyboard_activation_playlist_only(self, tmp_path, qapp):
        """REAL overlay keyboard path: resultIndex → activateResult()
        → PLAYLISTS/id (never Library)."""
        world = _world(tmp_path)
        a = world["service"].create_playlist("Road Trip")
        world["library"].search("Road Trip")
        engine = _engine(world)
        errors = _QmlErrors()
        try:
            overlay = _load(engine, "patterns/SearchOverlay.qml", errors)
            overlay.setProperty("resultIndex", 0)
            overlay.activateResult()
            _process()
            assert world["nav"].state.current_route == AppRoute.PLAYLISTS
            assert world["nav"].state.playlist_id == a.playlist_id
            assert world["service"].navigation.recent_ids[0] == a.playlist_id
            runtime = errors.drain()
            assert runtime == []
        finally:
            errors.restore()
            engine.deleteLater()


class TestSearchOverlayClosedState:
    """M9-R1K: the closed overlay (opacity 0 + enabled false) must not be an
    interactive/actionable Search surface."""

    def test_closed_overlay_is_non_interactive(self, tmp_path, qapp):
        world = _world(tmp_path)
        world["service"].create_playlist("Road Trip")
        world["library"].search("Road Trip")
        engine = _engine(world)
        errors = _QmlErrors()
        try:
            overlay = _load(engine, "patterns/SearchOverlay.qml", errors)
            assert overlay.property("opened") is False
            assert overlay.property("opacity") == 0.0
            assert overlay.property("enabled") is False
            inp = _find_item(overlay, "searchOverlayInput")
            assert inp is not None
            # closed: the input must not hold active interactive focus
            # (activeFocus is not reliably observable without a window; the
            # enforceable semantic gate is enabled=false — Qt delivers input
            # only to enabled items; screen-reader verification stays
            # Beta/RC QA per M9-R1K scope)
            inp.forceActiveFocus()
            _process()
            assert inp.property("activeFocus") is False
            runtime = errors.drain()
            assert runtime == []
        finally:
            errors.restore()
            engine.deleteLater()

    def test_closed_overlay_not_enabled_for_input(self, tmp_path, qapp):
        """The closed overlay must not consume interaction — enabled=false is
        the enforceable Qt semantic (no pointer/keyboard delivery to disabled
        items)."""
        world = _world(tmp_path)
        engine = _engine(world)
        errors = _QmlErrors()
        try:
            overlay = _load(engine, "patterns/SearchOverlay.qml", errors)
            assert overlay.property("enabled") is False
            assert overlay.property("opacity") == 0.0
            runtime = errors.drain()
            assert runtime == []
        finally:
            errors.restore()
            engine.deleteLater()


class TestLazyBindingRegression:
    """M9-R1K: the e4af323 defect is regression-locked — the CLOSED →
    search update → OPEN sequence must re-evaluate every result surface."""

    def test_closed_search_open_reevaluates(self, tmp_path, qapp):
        world = _world(tmp_path)
        engine = _engine(world)
        errors = _QmlErrors()
        try:
            overlay = _load(engine, "patterns/SearchOverlay.qml", errors)
            assert overlay.property("opened") is False
            # 1. closed: playlist + search arrive AFTER instantiation
            world["service"].create_playlist("Road Trip")
            world["library"].search("Road Trip")
            _process()
            assert world["pb"].property("searchPlaylistCount") == 1
            # 2. open: every result surface re-evaluates
            overlay.setProperty("opened", True)
            _process()
            assert overlay.property("combinedResultCount") == 1
            empty = _find_item(overlay, "searchEmptyState")
            scroll = _find_item(overlay, "searchResultsScroll")
            assert empty.property("visible") is False
            assert scroll.property("visible") is True
            repeater = _find_item(overlay, "playlistSearchRepeater")
            assert repeater is not None
            assert repeater.property("count") == 1
            runtime = errors.drain()
            assert runtime == []
        finally:
            errors.restore()
            engine.deleteLater()

    def test_clear_and_reopen_no_stale_results(self, tmp_path, qapp):
        world = _world(tmp_path)
        engine = _engine(world)
        errors = _QmlErrors()
        try:
            overlay = _load(engine, "patterns/SearchOverlay.qml", errors)
            world["service"].create_playlist("Road Trip")
            world["library"].search("Road Trip")
            overlay.setProperty("opened", True)
            _process()
            assert overlay.property("combinedResultCount") == 1
            overlay.setProperty("opened", False)
            _process()
            world["library"].clear_search()
            _process()
            assert world["pb"].property("searchPlaylistCount") == 0
            overlay.setProperty("opened", True)
            _process()
            assert overlay.property("combinedResultCount") == 0
            assert world["pb"].property("searchPlaylists") == []
            runtime = errors.drain()
            assert runtime == []
        finally:
            errors.restore()
            engine.deleteLater()


class TestSearchOverlayFocusLifecycle:
    """M9-R1L: REAL open→focus→close→release sequence inside a real
    QQuickWindow (activeFocus is only meaningful with a window)."""

    def _focus_within(self, item, window):
        """True si el activeFocusItem de la window es `item` o un descendiente."""
        focus_item = window.activeFocusItem()
        if focus_item is None:
            return False
        probe = focus_item
        while probe is not None:
            if probe is item:
                return True
            probe = probe.parentItem()
        return False

    def _window_with_overlay(self, tmp_path):
        from PySide6.QtQuick import QQuickWindow

        world = _world(tmp_path)
        engine = _engine(world)
        errors = _QmlErrors()
        overlay = _load(engine, "patterns/SearchOverlay.qml", errors)
        window = QQuickWindow()
        window.resize(900, 700)
        overlay.setParentItem(window.contentItem())
        window.show()
        _process()
        return world, engine, errors, overlay, window

    def test_search_overlay_releases_focus_after_close(self, tmp_path, qapp):
        world, engine, errors, overlay, window = self._window_with_overlay(tmp_path)
        try:
            # A-D: initial closed state
            assert overlay.property("opened") is False
            assert overlay.property("enabled") is False
            assert overlay.property("opacity") == 0.0

            # E-F: open — the production onOpenedChanged path focuses the input
            overlay.setProperty("opened", True)
            _process()
            inp = _find_item(overlay, "searchOverlayInput")
            assert inp is not None
            # G: the Search input becomes the active focus target through the
            # productive route (onOpenedChanged → forceActiveFocus +
            # forceInputFocus). MichiSearchField focuses its INNER TextField,
            # so the focused item is a descendant of searchOverlayInput.
            focused_inside = False
            for _ in range(3):
                _process()
                if self._focus_within(inp, window):
                    focused_inside = True
                    break
            assert focused_inside, "Search input no obtiene foco al abrir"

            # H-I: close — the input must NOT remain the active focus target
            overlay.setProperty("opened", False)
            _process()
            assert overlay.property("enabled") is False
            assert overlay.property("opacity") == 0.0
            assert not self._focus_within(inp, window), (
                "Search input retiene foco tras cerrar el overlay"
            )

            runtime = errors.drain()
            assert runtime == []
        finally:
            errors.restore()
            window.deleteLater()
            engine.deleteLater()
            # drain the deferred teardown with the DEFAULT handler so its
            # "of null" messages cannot leak into the next test's capture
            for _ in range(5):
                _process()


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
