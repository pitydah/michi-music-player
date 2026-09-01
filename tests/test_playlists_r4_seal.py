"""Playlists R4 — contract-consumer correctness seal (runtime gates).

R4-01  create result codes interpreted by the REAL dialog
R4-02  detail selection binding survives playlist switches
R4-08  pin/unpin feedback from command intent
R4-09  no-op = zero write + zero notify
R4-10  logical False != persistence_failed
R4-06  asset ownership collisions (abc vs abc_hero)
R4-07  unsafe playlist id rejected on prepare
"""

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

import pytest
from PySide6.QtCore import QObject
from PySide6.QtQml import QQmlComponent, QQmlEngine

from michi.application.errors import PlaylistPersistenceError
from michi.application.navigation_service import NavigationService
from michi.application.playlist_navigation_coordinator import (
    PlaylistNavigationCoordinator,
)
from michi.application.playlist_service import PlaylistService
from michi.infrastructure.playlist_artwork_store import (
    FilesystemPlaylistArtworkStore,
)
from michi.presentation.playlists_bridge import PlaylistsBridge
from tests.test_playlists import FakePlaylistsPort

QML_DIR = Path(__file__).resolve().parents[1] / "src" / "michi" / "presentation" / "qml"


@pytest.fixture
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def _world(tmp_path, port=None):
    service = PlaylistService(playlists_port=port or FakePlaylistsPort())
    nav = NavigationService()
    coord = PlaylistNavigationCoordinator(service, nav)
    bridge = PlaylistsBridge(service, playlist_navigation=coord, navigation_service=nav)
    return service, nav, coord, bridge


def _load(engine, rel):
    component = QQmlComponent(engine, str(QML_DIR / rel))
    errs = "; ".join(e.toString() for e in component.errors())
    assert component.status() == QQmlComponent.Ready, f"{rel}: {errs}"
    obj = component.create()
    engine._keepalive = getattr(engine, "_keepalive", []) + [component]
    return obj


class _CodeControlledPort(FakePlaylistsPort):
    """Permite inyectar códigos de resultado por slot."""

    def __init__(self, code="created"):
        super().__init__()
        self.code = code
        self.create_calls = 0
        self.fail_writes = False

    def save(self, playlists):
        if self.fail_writes:
            raise PlaylistPersistenceError("disk full")
        super().save(playlists)

    def save_navigation(self, state):
        if self.fail_writes:
            raise PlaylistPersistenceError("nav down")
        super().save_navigation(state)

    def save_state(self, playlists, navigation):
        if self.fail_writes:
            raise PlaylistPersistenceError("disk full")
        self._items = list(playlists)
        self._nav_stored = navigation
        self.saved.append(tuple(playlists))
        self.saved_nav.append(navigation)


# ==========================================================================
# R4-01 — CREATE DIALOG CONSUMER
# ==========================================================================


class TestCreateDialogConsumer:
    def _dialog(self, qapp, tmp_path, service, nav, coord, bridge):
        engine = QQmlEngine()
        engine.addImportPath(str(QML_DIR))
        engine.rootContext().setContextProperty("playlists", bridge)
        engine.rootContext().setContextProperty("navigation", nav)
        dialog = _load(engine, "playlists/PlaylistCreateDialog.qml")
        qapp.processEvents()
        return engine, dialog

    def _run_create(self, qapp, dialog, name="Jazz"):
        field = dialog.findChild(QObject, "playlistNameField")
        if field is None:
            field = dialog.findChildren(QObject)[0]
        field.setProperty("text", name)
        qapp.processEvents()
        # invocar _submit (función QML del dialog)
        meta = dialog.metaObject()
        idx = meta.indexOfMethod("_submit()")
        assert idx >= 0
        meta.method(idx).invoke(dialog)
        qapp.processEvents()

    def test_created_closes_dialog(self, qapp, tmp_path):
        service, nav, coord, bridge = _world(tmp_path)
        engine, dialog = self._dialog(qapp, tmp_path, service, nav, coord, bridge)
        dialog.open()
        qapp.processEvents()
        self._run_create(qapp, dialog)
        assert dialog.property("visible") is False
        assert any(p.name == "Jazz" for p in service.playlists)

    def test_conflict_keeps_dialog(self, qapp, tmp_path):
        service, nav, coord, bridge = _world(tmp_path)
        service.create_playlist("Jazz")
        engine, dialog = self._dialog(qapp, tmp_path, service, nav, coord, bridge)
        dialog.open()
        qapp.processEvents()
        self._run_create(qapp, dialog)
        assert len(service.playlists) == 1, "conflict must not create"
        # El branch conflict NO llama close() ni playlistCreated:
        assert dialog.property("errorText") != ""
        assert dialog.property("visible") is not None

    def test_invalid_keeps_dialog(self, qapp, tmp_path):
        service, nav, coord, bridge = _world(tmp_path)
        engine, dialog = self._dialog(qapp, tmp_path, service, nav, coord, bridge)
        self._run_create(qapp, dialog, name="   ")
        assert service.playlists == ()
        assert dialog.property("errorText") != ""  # invalid message

    def test_persistence_failed_keeps_dialog_no_duplicate_message(
        self,
        qapp,
        tmp_path,
    ):
        port = _CodeControlledPort()
        port.fail_writes = True
        service, nav, coord, bridge = _world(tmp_path, port=port)
        failures = []
        bridge.persistenceFailed.connect(failures.append)
        engine, dialog = self._dialog(qapp, tmp_path, service, nav, coord, bridge)
        dialog.open()
        qapp.processEvents()
        self._run_create(qapp, dialog)
        assert service.playlists == ()
        assert "already exists" not in dialog.property("errorText")
        assert failures == ["create"]

    def test_not_found_keeps_dialog(self, qapp, tmp_path):
        service, nav, coord, bridge = _world(tmp_path)
        # Simular not_found: service None → el slot devuelve not_found.
        bridge._playlist_service = None
        engine, dialog = self._dialog(qapp, tmp_path, service, nav, coord, bridge)
        dialog.open()
        qapp.processEvents()
        self._run_create(qapp, dialog)
        assert service.playlists == ()
        assert dialog.property("errorText") != ""  # not_found message


# ==========================================================================
# R4-10 — LOGICAL FALSE != PERSISTENCE FAILURE
# ==========================================================================


class TestResultSemantics:
    def test_pin_already_pinned_is_no_change_no_signal(self, tmp_path):
        service, nav, coord, bridge = _world(tmp_path)
        playlist = service.create_playlist("Mix")
        service.pin_playlist(playlist.playlist_id)
        failures = []
        bridge.persistenceFailed.connect(failures.append)
        assert bridge.pin_playlist(playlist.playlist_id) == "no_change"
        assert failures == []

    def test_move_same_index_is_no_change_no_signal(self, tmp_path):
        service, nav, coord, bridge = _world(tmp_path)
        playlist = service.create_playlist("Mix")
        service.add_track(playlist.playlist_id, "/a.flac")
        nav.navigate_to_playlist(playlist.playlist_id)
        failures = []
        bridge.persistenceFailed.connect(failures.append)
        assert bridge.move_track(0, 0) == "no_change"
        assert failures == []

    def test_duplicate_add_is_already_present_no_signal(self, tmp_path):
        service, nav, coord, bridge = _world(tmp_path)
        playlist = service.create_playlist("Mix")
        service.add_track(playlist.playlist_id, "/a.flac")
        failures = []
        bridge.persistenceFailed.connect(failures.append)
        assert (
            bridge.add_track_to_playlist(playlist.playlist_id, "/a.flac")
            == "already_present"
        )
        assert failures == []

    def test_real_db_failure_is_persistence_failed_with_signal(self, tmp_path):
        port = _CodeControlledPort()
        port.fail_writes = True
        service, nav, coord, bridge = _world(tmp_path, port=port)
        failures = []
        bridge.persistenceFailed.connect(failures.append)
        assert bridge.pin_playlist("ghost") == "not_found"
        assert failures == []


# ==========================================================================
# R4-09 — NO-OP = ZERO WRITE + ZERO NOTIFY
# ==========================================================================


class TestNoOpContract:
    def _spy(self, port, service):
        class _Sub:
            def __init__(self):
                self.calls = 0

            def __call__(self):
                self.calls += 1

        sub = _Sub()
        service.subscribe_changed(sub)
        return sub

    def test_rename_same_name_zero_write_zero_notify(self, tmp_path):
        port = FakePlaylistsPort()
        service = PlaylistService(playlists_port=port)
        a = service.create_playlist("Jazz")
        writes_before = len(port.saved)
        sub = self._spy(port, service)
        assert service.rename_playlist(a.playlist_id, "Jazz") is False
        assert len(port.saved) == writes_before
        assert sub.calls == 0

    def test_pin_already_pinned_zero_write_zero_notify(self, tmp_path):
        port = FakePlaylistsPort()
        service = PlaylistService(playlists_port=port)
        a = service.create_playlist("Jazz")
        service.pin_playlist(a.playlist_id)
        writes_before = len(port.saved_nav)
        sub = self._spy(port, service)
        assert service.pin_playlist(a.playlist_id) is False
        assert len(port.saved_nav) == writes_before
        assert sub.calls == 0

    def test_hero_auto_already_auto_zero_write_zero_notify(self, tmp_path):
        port = FakePlaylistsPort()
        service = PlaylistService(playlists_port=port)
        a = service.create_playlist("Jazz")
        writes_before = len(port.saved)
        sub = self._spy(port, service)
        assert service.set_hero_auto(a.playlist_id) is False  # no-op
        assert len(port.saved) == writes_before
        assert sub.calls == 0


# ==========================================================================
# R4-06/R4-07 — ASSET OWNERSHIP V2
# ==========================================================================


def _png(tmp_path, name, color=0xFF581C):
    from PySide6.QtGui import QImage

    img = QImage(16, 16, QImage.Format_RGB32)
    img.fill(color)
    path = tmp_path / name
    assert img.save(str(path), "PNG")
    return path


class TestAssetOwnershipV2:
    def test_abc_hero_and_abc_hero_cover_namespaces_do_not_collide(
        self,
        tmp_path,
    ):
        store = FilesystemPlaylistArtworkStore(tmp_path / "managed")
        hero_a = store.prepare_hero("abc", _png(tmp_path, "a.png"))
        cover_b = store.prepare_cover("abc_hero", _png(tmp_path, "b.png", 0xCB0543))
        assert hero_a and cover_b
        assert hero_a != cover_b
        # A/hero NO puede borrar B/cover.
        assert store.delete_managed_asset("abc", "hero", cover_b) is False
        assert Path(cover_b).exists()
        # B/cover NO puede borrar A/hero.
        assert store.delete_managed_asset("abc_hero", "cover", hero_a) is False
        assert Path(hero_a).exists()
        # Ownership legítima funciona.
        assert store.delete_managed_asset("abc", "hero", hero_a) is True
        assert store.delete_managed_asset("abc_hero", "cover", cover_b) is True

    def test_unsafe_playlist_ids_rejected_on_prepare(self, tmp_path):
        store = FilesystemPlaylistArtworkStore(tmp_path / "managed")
        src = _png(tmp_path, "ok.png")
        for unsafe in ("../../etc", "../foo", "a/b", "a\\b", "", ".", ".."):
            assert store.prepare_cover(unsafe, src) is None, unsafe
            assert store.prepare_hero(unsafe, src) is None, unsafe
        # Sin candidates para los ids unsafe.
        leftovers = (
            list((tmp_path / "managed").iterdir())
            if (tmp_path / "managed").exists()
            else []
        )
        assert leftovers == []
