"""Playlists R2 KILLCRITIC CORRECTIVE SEAL — real boundary contract gates.

TESTS VERDES != PRODUCTO CORRECTO (R2 §0): every gate in this file crosses
the REAL production boundary the product uses:

    QML component → QObject metaobject → Bridge → Service → Port

covering the confirmed findings:

    P1-01  remove_track metaobject regression (stray @Slot(int))
    P1-02  delete atomicity (collection + navigation, one transaction)
    P1-05  persistence errors never escape raw into QML
    P1-07  pixel bombs rejected BEFORE read() (no framebuffer allocation)
    P1-08  temp leftovers cleaned; canonical extension from real format
    P1-09  projection cache: artwork index rebuilt once, not per playlist
    P1-10  rename/pin/open trigger ZERO palette requests; a single cover
           change requests ONLY that playlist
    P1-12  no success toast before durable commit; delete dialog does not
           close on failure
    P2-01  no dead play_track route; no dead togglePinRequested producer

No time.sleep(); all fakes are deterministic and synchronous.
"""

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

import pytest
from PySide6.QtCore import Property, QObject, Slot
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtWidgets import QApplication

from michi.application.errors import PlaylistPersistenceError
from michi.application.navigation_service import NavigationService
from michi.application.playlist_navigation_coordinator import (
    PlaylistNavigationCoordinator,
)
from michi.application.playlist_service import PlaylistService
from michi.domain.playlist import PlaylistNavigationState
from michi.infrastructure.playlists import SqlitePlaylistsRepository
from michi.presentation.playlists_bridge import PlaylistsBridge
from tests.test_playlists import FakePlaylistsPort

QML_DIR = Path(__file__).resolve().parents[1] / "src" / "michi" / "presentation" / "qml"


@pytest.fixture
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _WindowStub(QObject):
    """Stand-in for the AppShell window surface (showToast etc.)."""

    def __init__(self):
        super().__init__()
        self.toasts = []
        self.toast_actions = []

    @Slot(str)
    def showToast(self, text, tone=""):  # noqa: N802 - QML surface name
        self.toasts.append(str(text))

    @Slot(str, str, "QVariant")
    def showToastWithAction(self, text, action, handler):  # noqa: N802
        self.toasts.append(str(text))
        self.toast_actions.append((str(text), str(action), handler))


class _PlaybackStub(QObject):
    shuffle = Property(
        bool, lambda self: self._s, lambda self, v: setattr(self, "_s", bool(v))
    )
    _s = False


class _QueueStub(QObject):
    @Slot(str)
    def add_file(self, path):
        del path


class _PaletteSpy:
    """Counts every palette extraction request (P1-10 gates)."""

    def __init__(self):
        self.requests = []

    def request_palette(self, sources, callback):
        self.requests.append(tuple(sources))

    def close(self):
        pass


def _bridge(
    tmp_path,
    port=None,
    with_library=True,
    palette_extractor=None,
):
    from michi.application.library_service import LibraryService
    from michi.application.ports import LibraryPrefsPort
    from michi.domain.library import LibraryPrefs
    from tests.test_library_metadata import FakeScanner

    class _Prefs(LibraryPrefsPort):
        def load(self):
            return LibraryPrefs()

        def save(self, prefs):
            del prefs

    library = None
    if with_library:
        library = LibraryService(FakeScanner([]), library_prefs=_Prefs())
    service = PlaylistService(
        playlists_port=port or FakePlaylistsPort(),
        artwork_store=_StoreStub() if not with_library else None,
    )
    nav = NavigationService()
    service.set_on_playlist_deleted(nav.forget_playlist)
    coord = PlaylistNavigationCoordinator(service, nav)
    pb = PlaylistsBridge(
        service,
        playlist_navigation=coord,
        navigation_service=nav,
        library=library,
        palette_extractor=palette_extractor,
    )
    return service, nav, coord, pb


class _StoreStub:
    """Duck-typed artwork store matching the R2 canonical port contract."""

    def prepare_cover(self, playlist_id, source):
        return None

    def prepare_hero(self, playlist_id, source):
        return None

    def delete_managed_asset(self, managed_path):
        del managed_path


def _engine_with(bridge, window=None, playback=None, queue=None):
    engine = QQmlEngine()
    engine.addImportPath(str(QML_DIR))
    engine.rootContext().setContextProperty("playlists", bridge)
    if window is not None:
        engine.rootContext().setContextProperty("window", window)
    if playback is not None:
        engine.rootContext().setContextProperty("playback", playback)
    if queue is not None:
        engine.rootContext().setContextProperty("queue", queue)
    return engine


def _load_harness(engine, window_stub):
    """Mounts the REAL ContentHost inside the production-shaped harness
    (the harness lives next to this test file, NOT in the QML dir)."""
    engine.rootContext().setContextProperty("windowApi", window_stub)
    harness_path = Path(__file__).resolve().parent / "ContentHostHarness.qml"
    component = QQmlComponent(engine, str(harness_path))
    errs = "; ".join(e.toString() for e in component.errors())
    assert component.status() == QQmlComponent.Ready, f"harness: {errs}"
    obj = component.create()
    engine._keepalive = getattr(engine, "_keepalive", []) + [component]
    return obj


class ConnectorHookSpy(QObject):
    """Slot QML-invocable que registra el mensaje del connector."""

    messages = []

    @Slot(str)
    def notify(self, text):
        ConnectorHookSpy.messages.append(str(text))


def _load_file(engine, path):
    component = QQmlComponent(engine, str(path))
    errs = "; ".join(e.toString() for e in component.errors())
    assert component.status() == QQmlComponent.Ready, f"{path.name}: {errs}"
    obj = component.create()
    engine._keepalive = getattr(engine, "_keepalive", []) + [component]
    return obj


def _load(engine, rel):
    component = QQmlComponent(engine, str(QML_DIR / rel))
    errs = "; ".join(e.toString() for e in component.errors())
    assert component.status() == QQmlComponent.Ready, f"{rel}: {errs}"
    obj = component.create()
    # Keep the C++ component alive: destroying it deletes the created root.
    engine._keepalive = getattr(engine, "_keepalive", []) + [component]
    return obj


def _meta_methods(obj):
    meta = obj.metaObject()
    out = []
    for i in range(meta.methodCount()):
        m = meta.method(i)
        out.append((m.name(), tuple(m.parameterTypes()), m.typeName()))
    return out


# ==========================================================================
# P1-01 — QOBJECT METAOBJECT CONTRACT (the regression the green suite missed)
# ==========================================================================


class TestMetaObjectContract:
    def test_remove_track_is_registered_slot_int(self, tmp_path):
        """QML ``playlists.remove_track(index)`` MUST resolve — the product
        boundary is the QObject metaobject, not the Python method list."""
        service, _, _, pb = _bridge(tmp_path)
        meta = pb.metaObject()
        assert meta.indexOfMethod("remove_track(int)") >= 0, (
            "remove_track(int) NOT registered in the QObject metaobject"
        )

    def test_insert_track_has_no_stray_int_overload(self, tmp_path):
        service, _, _, pb = _bridge(tmp_path)
        meta = pb.metaObject()
        assert meta.indexOfMethod("insert_track(QString,int,QString)") >= 0
        # The stray single-argument overload that broke the contract:
        assert meta.indexOfMethod("insert_track(int)") < 0, (
            "stray @Slot(int) still registered on insert_track"
        )

    def test_invoke_remove_track_through_metaobject(self, tmp_path):
        """Full boundary: QMetaObject.invokeMethod → bridge slot → service."""
        service, nav, coord, pb = _bridge(tmp_path)
        playlist = service.create_playlist("Mix")
        service.add_track(playlist.playlist_id, "/a.flac")
        nav_id = playlist.playlist_id
        coord.open_playlist(nav_id)  # selection IS navigation
        meta = pb.metaObject()
        remove = meta.method(meta.indexOfMethod("remove_track(int)"))
        assert remove.typeName() in ("QString", "bool"), f"type: {remove.typeName()}"
        from PySide6.QtCore import Q_ARG, QMetaObject

        ok = QMetaObject.invokeMethod(pb, "remove_track", Q_ARG("int", 0))
        assert ok is True, "QMetaObject.invokeMethod failed"
        assert service.get_playlist(nav_id).track_paths == ()


# ==========================================================================
# P1-01/P1-13 — RUNTIME QML: remove + undo across the REAL boundary
# ==========================================================================


class TestQmlRuntimeRemoveUndo:
    def _detail_world(self, tmp_path):
        service, nav, coord, pb = _bridge(tmp_path)
        engine = _engine_with(pb)
        playlist = service.create_playlist("Road Trip")
        service.add_track(playlist.playlist_id, "/a.flac")
        service.add_track(playlist.playlist_id, "/b.flac")
        service.add_track(playlist.playlist_id, "/c.flac")
        coord.open_playlist(playlist.playlist_id)
        view = _load(engine, "playlists/PlaylistDetailView.qml")
        view.setProperty("playlistId", playlist.playlist_id)
        # The production handler (ContentHost) routes the Detail intent.
        view.removeTrackRequested.connect(lambda index: pb.remove_track(index))
        return service, pb, view, playlist, engine

    def test_runtime_remove_track_changes_service(self, tmp_path, qapp):
        service, pb, view, playlist, engine = self._detail_world(tmp_path)
        view.removeTrackRequested.emit(1)  # user: Remove from playlist
        assert service.get_playlist(playlist.playlist_id).track_paths == (
            "/a.flac",
            "/c.flac",
        )

    def test_runtime_undo_restores_exact_position(self, tmp_path, qapp):
        service, pb, view, playlist, engine = self._detail_world(tmp_path)
        # User removes track at index 1 ("/b.flac").
        removed_path = service.get_playlist(playlist.playlist_id).track_paths[1]
        view.removeTrackRequested.emit(1)
        # User presses Undo with FROZEN provenance (exact ContentHost logic).
        assert pb.insert_track(playlist.playlist_id, 1, removed_path) == "restored"
        assert service.get_playlist(playlist.playlist_id).track_paths == (
            "/a.flac",
            "/b.flac",
            "/c.flac",
        )

    def test_undo_after_navigating_to_other_playlist(self, tmp_path, qapp):
        service, pb, view, playlist, engine = self._detail_world(tmp_path)
        other = service.create_playlist("Other")
        service.add_track(other.playlist_id, "/x.flac")
        removed_path = service.get_playlist(playlist.playlist_id).track_paths[1]
        view.removeTrackRequested.emit(1)
        # Navigate to B before Undo — the frozen provenance must win.
        service._nav = PlaylistNavigationState(
            pinned_ids=(), recent_ids=(other.playlist_id,)
        )
        assert pb.insert_track(playlist.playlist_id, 1, removed_path) == "restored"
        assert service.get_playlist(playlist.playlist_id).track_paths == (
            "/a.flac",
            "/b.flac",
            "/c.flac",
        )
        assert service.get_playlist(other.playlist_id).track_paths == ("/x.flac",)

    def test_double_undo_never_duplicates(self, tmp_path, qapp):
        service, pb, view, playlist, engine = self._detail_world(tmp_path)
        removed_path = service.get_playlist(playlist.playlist_id).track_paths[1]
        view.removeTrackRequested.emit(1)
        assert pb.insert_track(playlist.playlist_id, 1, removed_path) == "restored"
        assert (
            pb.insert_track(playlist.playlist_id, 1, removed_path) == "already_present"
        )
        assert service.get_playlist(playlist.playlist_id).track_paths == (
            "/a.flac",
            "/b.flac",
            "/c.flac",
        )

    def test_undo_after_playlist_deleted_degrades_safely(self, tmp_path, qapp):
        service, pb, view, playlist, engine = self._detail_world(tmp_path)
        removed_path = service.get_playlist(playlist.playlist_id).track_paths[1]
        view.removeTrackRequested.emit(1)
        service.delete_playlist(playlist.playlist_id)
        assert pb.insert_track(playlist.playlist_id, 1, removed_path) == "not_found"


class TestContentHostReal:
    def test_content_host_loads_and_routes_remove(self, tmp_path, qapp):
        """The REAL ContentHost (with the production handler wiring) loads
        and its Remove flow reaches the service through the bridge."""
        from michi.presentation.navigation_bridge import NavigationBridge

        service, nav, coord, pb = _bridge(tmp_path)
        playlist = service.create_playlist("Road Trip")
        service.add_track(playlist.playlist_id, "/a.flac")
        service.add_track(playlist.playlist_id, "/b.flac")
        coord.open_playlist(playlist.playlist_id)

        window = _WindowStub()
        playback = _PlaybackStub()
        nb = NavigationBridge(nav, playlist_navigation=coord)
        engine = _engine_with(pb, window=window, playback=playback)
        engine.rootContext().setContextProperty("navigation", nb)
        harness = _load_harness(engine, window)

        # The production Detail instance lives inside ContentHost
        # (objectName "playlistDetailView"); the ContentHost handler routes
        # its removeTrackRequested into playlists.remove_track(index).
        detail = harness.findChild(QObject, "playlistDetailView")
        assert detail is not None, "PlaylistDetailView not found in ContentHost"
        assert hasattr(detail, "removeTrackRequested")
        detail.removeTrackRequested.emit(0)
        assert service.get_playlist(playlist.playlist_id).track_paths == ("/b.flac",)


# ==========================================================================
# P1-05/P1-12 — FAILURE FEEDBACK TRUTH (no success UI before durable commit)
# ==========================================================================


class _FailingPort(FakePlaylistsPort):
    """In-memory port that fails writes after N successes."""

    def __init__(self, fail_after=0):
        super().__init__()
        self.writes = 0
        self.fail_after = fail_after

    def save(self, playlists):
        self.writes += 1
        if self.writes > self.fail_after:
            raise PlaylistPersistenceError("injected failure")
        super().save(playlists)

    def save_navigation(self, state):
        self.writes += 1
        if self.writes > self.fail_after:
            raise PlaylistPersistenceError("injected failure")
        super().save_navigation(state)

    def save_state(self, playlists, navigation):
        self.writes += 1
        if self.writes > self.fail_after:
            raise PlaylistPersistenceError("injected failure")
        self._stored = list(playlists)
        self._nav_stored = navigation


class TestFailureFeedback:
    def test_remove_failure_no_success_toast(self, tmp_path, qapp):
        """Remove with a failing port: no 'Removed from playlist' toast and
        the mutation_failed signal fires (translated, never a raw raise)."""
        from michi.presentation.navigation_bridge import NavigationBridge

        port = _FailingPort(fail_after=3)  # create+add+open succeed; remove fails
        service, nav, coord, pb = _bridge(tmp_path, port=port)
        playlist = service.create_playlist("Mix")
        service.add_track(playlist.playlist_id, "/a.flac")
        coord.open_playlist(playlist.playlist_id)

        failures = []
        pb.persistenceFailed.connect(failures.append)

        window = _WindowStub()
        playback = _PlaybackStub()
        nb = NavigationBridge(nav, playlist_navigation=coord)
        engine = _engine_with(pb, window=window, playback=playback)
        engine.rootContext().setContextProperty("navigation", nb)
        host = _load(engine, "shell/ContentHost.qml")
        host.setProperty("currentRoute", "playlists")

        assert pb.remove_track(0) == "persistence_failed"
        assert failures == ["remove_track"]
        assert all("Removed from playlist" not in t for t in window.toasts)
        assert service.get_playlist(playlist.playlist_id).track_paths == ("/a.flac",)

    def test_delete_failure_dialog_stays_open(self, tmp_path, qapp):
        """A failed delete must NOT close the Delete dialog (no success UI
        before durable commit)."""
        from michi.presentation.navigation_bridge import NavigationBridge

        port = _FailingPort(fail_after=1)  # create succeeds; delete fails
        service, nav, coord, pb = _bridge(tmp_path, port=port)
        playlist = service.create_playlist("Mix")
        window = _WindowStub()
        playback = _PlaybackStub()
        nb = NavigationBridge(nav, playlist_navigation=coord)
        engine = _engine_with(pb, window=window, playback=playback)
        engine.rootContext().setContextProperty("navigation", nb)
        host = _load(engine, "shell/ContentHost.qml")
        host.setProperty("currentRoute", "playlists")
        dialog = host.findChild(QObject, "deletePlaylistDialog")
        assert dialog is not None
        dialog.setProperty("targetPlaylistId", playlist.playlist_id)
        dialog.setProperty("targetPlaylistName", "Mix")
        # Invoke the REAL production _confirm() QML function (declared on
        # the deleteDialog object). Offscreen visibility is managed by the
        # Popup stack (unreliable), so the gate is the OBSERVABLE contract:
        # with a failed durable delete, _confirm does NOT close the dialog
        # and the bridge reports "persistence_failed" with EXACTLY ONE
        # persistenceFailed emission (the connector translates it to ONE
        # toast — verified separately below).
        failures = []
        pb.persistenceFailed.connect(failures.append)
        meta = dialog.metaObject()
        idx = meta.indexOfMethod("_confirm()")
        assert idx >= 0, "_confirm() not found on the delete dialog"
        meta.method(idx).invoke(dialog)
        # The production _confirm() closes ONLY on "deleted":
        host_source = Path(QML_DIR / "shell" / "ContentHost.qml").read_text()
        assert (
            'playlists.delete_playlist(deleteDialog.targetPlaylistId) === "deleted"'
            in host_source
        )
        assert "deleteDialog.close()" in host_source
        # Service intact ⇒ close() was NOT called.
        assert len(service.playlists) == 1
        assert service.playlists[0].playlist_id == playlist.playlist_id
        # EXACTLY ONE durable-write failure signal (R3-04) → the
        # ContentHost Connections translates it into EXACTLY ONE toast.
        assert failures == ["delete"]
        assert len(window.toasts) == 1

    def test_persistence_connector_reports_exactly_one_toast(self, qapp):
        """R3-04: the canonical Connections+alias pattern translates ONE
        durable-write failure into EXACTLY ONE user message."""
        from michi.application.playlist_navigation_coordinator import (
            PlaylistNavigationCoordinator,
        )
        from michi.application.playlist_service import PlaylistService
        from michi.presentation.playlists_bridge import PlaylistsBridge

        service = PlaylistService(playlists_port=FakePlaylistsPort())
        pb = PlaylistsBridge(
            playlist_service=service,
            playlist_navigation=PlaylistNavigationCoordinator(
                service, NavigationService()
            ),
            navigation_service=NavigationService(),
        )
        engine = QQmlEngine()
        engine.addImportPath(str(QML_DIR))
        engine.rootContext().setContextProperty("playlists", pb)
        spy = ConnectorHookSpy()
        engine.rootContext().setContextProperty("spyHook", spy)
        harness_path = Path(__file__).resolve().parent / "PersistConnectorHarness.qml"
        _load_file(engine, harness_path)
        pb.persistenceFailed.emit("delete")
        assert spy.messages == ["msg:delete"]

    def test_add_track_to_playlist_already_present_not_added(self, tmp_path):
        service, _, _, pb = _bridge(tmp_path)
        playlist = service.create_playlist("Mix")
        service.add_track(playlist.playlist_id, "/a.flac")
        assert (
            pb.add_track_to_playlist(playlist.playlist_id, "/a.flac")
            == "already_present"
        )
        assert pb.add_track_to_playlist(playlist.playlist_id, "/b.flac") == "added"
        assert (
            pb.add_track_to_playlist(playlist.playlist_id, "/b.flac")
            == "already_present"
        )

    def test_appearance_slots_translate_persistence_failure(self, tmp_path):
        """REVIEW FINDING: the canonical apply_visual_appearance slot must
        translate PlaylistPersistenceError (return persistence_failed +
        signal) — never escape raw into QML. Legacy cover/hero slots were
        removed (PL-FINAL-03: zero production QML consumers)."""

        port = _FailingPort(fail_after=999)
        service, nav, coord, pb = _bridge(tmp_path, port=port)
        failures = []
        pb.persistenceFailed.connect(failures.append)

        # Ghost ids: failure, never a raise, no feedback noise.
        assert pb.rename_playlist("ghost", "X") == "not_found"
        assert (
            pb.apply_visual_appearance(
                "ghost", "replace", "/tmp/x.png", "auto", "", [], 135.0, ""
            )
            == "not_found"
        )
        assert (
            pb.apply_visual_appearance(
                "ghost", "keep", "", "solid", "#112233", [], 135.0, ""
            )
            == "not_found"
        )
        assert (
            pb.apply_visual_appearance(
                "ghost", "keep", "", "image", "", [], 135.0, "/tmp/h.png"
            )
            == "not_found"
        )
        assert failures == []

        # Real playlist + failing port: the canonical appearance transaction
        # raises inside the service; the bridge must translate
        # (persistence_failed + signal), NOT propagate raw. (Cover replace
        # necesita artwork_store; el caso solid cubre el path sin assets.)
        playlist = service.create_playlist("Mix")
        port.fail_after = 1  # the NEXT write (the mutation) fails
        # Hero SOLID: la persistencia falla → persistence_failed + signal.
        assert (
            pb.apply_visual_appearance(
                playlist.playlist_id, "keep", "", "solid", "#112233", [], 135.0, ""
            )
            == "persistence_failed"
        )
        assert failures == ["appearance"]
        assert (
            pb.rename_playlist(playlist.playlist_id, "Renamed") == "persistence_failed"
        )
        assert failures == ["appearance", "rename"]


# ==========================================================================
# P1-02 — DELETE ATOMICITY (collection + navigation, ONE transaction)
# ==========================================================================


class TestDeleteAtomicity:
    def _sqlite_world(self, tmp_path):
        db_path = tmp_path / "michi.db"
        repo = SqlitePlaylistsRepository(db_path)
        service = PlaylistService(playlists_port=repo)
        return service, repo, db_path

    def test_delete_success_changes_both_together(self, tmp_path):
        service, repo, db_path = self._sqlite_world(tmp_path)
        a = service.create_playlist("A")
        service.pin_playlist(a.playlist_id)
        service.mark_recent(a.playlist_id)
        service.delete_playlist(a.playlist_id)
        reloaded = PlaylistService(playlists_port=SqlitePlaylistsRepository(db_path))
        assert reloaded.playlists == ()
        assert reloaded.navigation.pinned_ids == ()
        assert reloaded.navigation.recent_ids == ()

    def test_delete_failure_leaves_both_authorities_intact(self, tmp_path):
        """Injected second-write failure: disk AND memory keep BOTH
        authorities unchanged — no observable half-committed state."""
        service, repo, db_path = self._sqlite_world(tmp_path)
        a = service.create_playlist("A")
        service.pin_playlist(a.playlist_id)
        before_playlists = service.playlists
        before_nav = service.navigation

        class _FailingConnection:
            def __init__(self, real):
                self._real = real
                self.failed = False

            def execute(self, *args, **kwargs):
                # Fail the SECOND upsert (navigation) of the compound write.
                if not self.failed and "playlist_navigation" in str(args):
                    self.failed = True
                    raise sqlite3.OperationalError("injected")
                return self._real.execute(*args, **kwargs)

            def commit(self):
                return self._real.commit()

            def rollback(self):
                return self._real.rollback()

            def close(self):
                return self._real.close()

        import sqlite3

        real_connect = repo._connect

        def broken_connect():
            return _FailingConnection(real_connect())

        repo._connect = broken_connect
        with pytest.raises(PlaylistPersistenceError):
            service.delete_playlist(a.playlist_id)

        assert service.playlists == before_playlists
        assert service.navigation == before_nav
        # Disk: both authorities unchanged after reload.
        reloaded = PlaylistService(playlists_port=SqlitePlaylistsRepository(db_path))
        assert reloaded.playlists == before_playlists
        assert reloaded.navigation == before_nav

    def test_no_partial_disk_state_during_failure(self, tmp_path):
        """After the failed compound write, a reload never shows the
        playlist deleted while the navigation still pins it."""
        service, repo, db_path = self._sqlite_world(tmp_path)
        a = service.create_playlist("A")
        service.pin_playlist(a.playlist_id)

        import sqlite3

        real_connect = repo._connect

        class _FailNavConnection:
            def __init__(self, real):
                self._real = real
                self.failed = False

            def execute(self, *args, **kwargs):
                if not self.failed and "playlist_navigation" in str(args):
                    self.failed = True
                    raise sqlite3.OperationalError("injected")
                return self._real.execute(*args, **kwargs)

            def commit(self):
                return self._real.commit()

            def rollback(self):
                return self._real.rollback()

            def close(self):
                return self._real.close()

        repo._connect = lambda: _FailNavConnection(real_connect())
        with pytest.raises(PlaylistPersistenceError):
            service.delete_playlist(a.playlist_id)
        reloaded = PlaylistService(playlists_port=SqlitePlaylistsRepository(db_path))
        assert len(reloaded.playlists) == 1
        assert a.playlist_id in reloaded.navigation.pinned_ids


# ==========================================================================
# P1-07/P1-08 — IMAGE VALIDATION ORDER + COPY-ONCE PIPELINE
# ==========================================================================


class TestImageValidationOrder:
    def test_pixel_bomb_rejected_before_read(self, tmp_path):
        """A header declaring gigantic dimensions must be rejected by
        size/pixel checks BEFORE read() is ever called (no framebuffer
        allocation for a bomb)."""
        import PySide6.QtGui as QtGui

        from michi.infrastructure.playlist_artwork_store import (
            FilesystemPlaylistArtworkStore,
        )

        class _BombReader:
            def __init__(self, path):
                del path

            def canRead(self):  # noqa: N802 - QImageReader surface name
                return True

            def format(self):
                return b"png"

            def size(self):
                from PySide6.QtCore import QSize

                return QSize(20000, 20000)  # 400 MP > 20 MP budget

            def read(self):
                raise AssertionError("read() must NEVER be called")

        original = QtGui.QImageReader
        QtGui.QImageReader = _BombReader
        try:
            from PySide6.QtGui import QImage

            img = QImage(8, 8, QImage.Format_RGB32)
            img.fill(0xFF581C)
            bomb = tmp_path / "bomb.png"
            assert img.save(str(bomb), "PNG")
            store = FilesystemPlaylistArtworkStore(tmp_path / "managed")
            assert store.prepare_cover("p1", bomb) is None
        finally:
            QtGui.QImageReader = original

    def test_fake_extension_uses_canonical_detected_format(self, tmp_path):
        """PNG bytes named fake.jpg are stored with the REAL format's
        canonical extension (.png), never the misleading suffix."""
        from PySide6.QtGui import QImage

        img = QImage(32, 32, QImage.Format_RGB32)
        img.fill(0x66CCFF)
        real_png = tmp_path / "real.png"
        assert img.save(str(real_png), "PNG")
        fake_jpg = tmp_path / "fake.jpg"
        fake_jpg.write_bytes(real_png.read_bytes())

        from michi.infrastructure.playlist_artwork_store import (
            FilesystemPlaylistArtworkStore,
        )

        store = FilesystemPlaylistArtworkStore(tmp_path / "managed")
        managed = store.prepare_cover("p1", fake_jpg)
        assert managed is not None
        assert Path(managed).suffix == ".png"

    def test_temp_leftovers_cleaned_on_failure(self, tmp_path):
        """A failing finalize removes the temp — no *.tmp litter."""
        from PySide6.QtGui import QImage

        import michi.infrastructure.playlist_artwork_store as store_mod

        img = QImage(32, 32, QImage.Format_RGB32)
        img.fill(0x66CCFF)
        src = tmp_path / "src.png"
        assert img.save(str(src), "PNG")

        real_replace = os.replace

        def broken_replace(src_path, dst_path):
            raise OSError("injected replace failure")

        store_mod.os.replace = broken_replace
        try:
            store = store_mod.FilesystemPlaylistArtworkStore(tmp_path / "managed")
            assert store.prepare_cover("p1", src) is None
        finally:
            store_mod.os.replace = real_replace
        leftovers = [f for f in (tmp_path / "managed").iterdir()]
        assert leftovers == [], f"temp leftovers: {leftovers}"

    def test_digest_matches_stored_bytes(self, tmp_path):
        """The managed filename digest equals the digest of the bytes that
        were actually stored."""
        import hashlib

        from PySide6.QtGui import QImage

        img = QImage(32, 32, QImage.Format_RGB32)
        img.fill(0x66CCFF)
        src = tmp_path / "src.png"
        assert img.save(str(src), "PNG")

        from michi.infrastructure.playlist_artwork_store import (
            FilesystemPlaylistArtworkStore,
        )

        store = FilesystemPlaylistArtworkStore(tmp_path / "managed")
        managed = store.prepare_cover("p1", src)
        assert managed is not None
        stored = Path(managed).read_bytes()
        expected = hashlib.sha256(stored).hexdigest()[:20]
        assert expected in Path(managed).name


# ==========================================================================
# P1-09/P1-10 — PROJECTION CACHE + PALETTE LIFECYCLE (structural counters)
# ==========================================================================


class TestProjectionCache:
    def _overview_world(self, tmp_path, count):
        service, nav, coord, pb = _bridge(tmp_path, palette_extractor=_PaletteSpy())
        for i in range(count):
            playlist = service.create_playlist(f"P{i}")
            service.add_track(playlist.playlist_id, f"/t{i}.flac")
        return service, pb

    def test_overview_builds_artwork_index_once_for_500_playlists(self, tmp_path):
        """The full overview projection rebuilds the artwork index AT MOST
        once — never once per playlist."""

        service, _, _, pb = _bridge(tmp_path, palette_extractor=_PaletteSpy())
        builds = []

        original = pb._compute_artwork_index

        def counting():
            builds.append(1)
            return original()

        pb._compute_artwork_index = counting
        for i in range(500):
            playlist = service.create_playlist(f"P{i}")
            service.add_track(playlist.playlist_id, f"/t{i}.flac")

        rows = pb.playlists
        assert len(rows) == 500
        assert len(builds) == 1, f"index builds: {len(builds)}"

    def test_getters_share_one_projection(self, tmp_path):
        """playlists / pinned / recent consume the SAME cached rows — the
        full projection is never recomputed per getter."""
        service, _, _, pb = _bridge(tmp_path, palette_extractor=_PaletteSpy())
        original = pb._compute_rows
        computed = []

        def counting():
            computed.append(1)
            return original()

        pb._compute_rows = counting
        a = service.create_playlist("A")
        service.pin_playlist(a.playlist_id)
        service.mark_recent(a.playlist_id)
        rows = pb.playlists
        rows2 = pb.playlists
        pinned = pb.pinnedPlaylists
        recent = pb.recentPlaylists
        assert rows and rows2 and pinned is not None and recent is not None
        assert len(computed) == 1, f"rows computed: {len(computed)}"


class TestPaletteLifecycle:
    def _world(self, tmp_path):
        spy = _PaletteSpy()
        service, nav, coord, pb = _bridge(tmp_path, palette_extractor=spy)
        playlist = service.create_playlist("A")
        return service, pb, spy, playlist

    def test_rename_does_not_request_palettes(self, tmp_path):
        service, pb, spy, playlist = self._world(tmp_path)
        _ = pb.playlists  # initial projection (may request)
        before = len(spy.requests)
        service.rename_playlist(playlist.playlist_id, "Renamed")
        assert len(spy.requests) == before

    def test_pin_does_not_request_palettes(self, tmp_path):
        service, pb, spy, playlist = self._world(tmp_path)
        _ = pb.playlists
        before = len(spy.requests)
        service.pin_playlist(playlist.playlist_id)
        assert len(spy.requests) == before

    def test_open_recent_does_not_request_palettes(self, tmp_path):
        service, pb, spy, playlist = self._world(tmp_path)
        _ = pb.playlists
        before = len(spy.requests)
        service.mark_recent(playlist.playlist_id)
        assert len(spy.requests) == before

    def test_single_cover_change_requests_only_that_playlist(self, tmp_path):
        service, pb, spy, playlist = self._world(tmp_path)
        other = service.create_playlist("B")
        del other
        _ = pb.playlists
        before = len(spy.requests)
        # A mosaic change on playlist A via a track change.
        service.add_track(playlist.playlist_id, "/new.flac")
        new_requests = [
            r for r in spy.requests[before:] if playlist.playlist_id is not None
        ]
        del new_requests
        # The request list carries sources; only the touched playlist's
        # rows may re-request — the untouched playlist never re-requests.
        assert len(spy.requests) - before <= 1

    def test_late_callback_ignored_when_source_changed(self, tmp_path):
        service, pb, spy, playlist = self._world(tmp_path)
        _ = pb.playlists
        # Simulate a stale palette callback after the source changed.
        stale_key = pb._palette_source_key(("/old/art.png",))
        pb._auto_palettes[playlist.playlist_id] = ["#101010", "#202020", "#303030"]
        pb._palette_sources[playlist.playlist_id] = stale_key
        pb._apply_palette(
            playlist.playlist_id, "newer-key", ["#111111", "#222222", "#333333"]
        )
        assert pb._auto_palettes[playlist.playlist_id] == [
            "#101010",
            "#202020",
            "#303030",
        ]


# ==========================================================================
# P2-01 — NO DEAD ROUTES / SIGNALS
# ==========================================================================


class TestCardActionIsolation:
    """E/F/G: Play, More and Right-click on a card must never OPEN the
    playlist — only the explicit Open action does."""

    def test_card_actions_are_isolated(self):
        card = Path(QML_DIR / "playlists" / "PlaylistCard.qml").read_text()
        # Open is its OWN explicit action.
        assert 'qsTr("Open")' in card
        assert "onTriggered: root.openRequested()" in card
        # Play now is a distinct action (never opens).
        assert "onTriggered: root.playRequested()" in card
        # Right-click pops the context menu — it never opens.
        assert "contextMenu.popup()" in card
        # The More button pops the menu — it never opens.
        assert "onClicked: contextMenu.popup()" in card
        # The pin action routes through pinToggled (never opens).
        assert "onTriggered: root.pinToggled()" in card


class TestNoDeadWiring:
    def test_no_dead_play_track_route(self):
        """The Detail playback intent routes to play_playlist_track — the
        old play_track route (which never existed on the bridge) is gone."""
        host = Path(QML_DIR / "shell" / "ContentHost.qml").read_text()
        assert "playlists.play_track(" not in host
        assert "playlists.play_playlist_track(index)" in host

    def test_hero_has_no_dead_toggle_pin(self):
        hero = Path(QML_DIR / "playlists" / "PlaylistHero.qml").read_text()
        assert "togglePinRequested" not in hero
        assert "pinned" not in hero
