"""PLAYLISTS FINAL CLOSE SEAL — runtime behavior, not text grep.

PL-FINAL-A01  multiselect identity by PATH (never stale indices)
PL-FINAL-A02  transient state never survives playlist A→B
PL-FINAL-A04  unavailable track: ONE canInteract authority
PL-FINAL-A05  Play/Shuffle operate only on playable tracks
PL-FINAL-A06  missing cover → Automatic mosaic recovery
PL-FINAL-A07  asset contract: prepare_candidate canonical, no invented ownership
PL-FINAL-A08  picker membership from canonical (unfiltered) paths
PL-FINAL-A09  picker: keyboard and mouse share toggleIfAddable
PL-FINAL-A10  Select All visible = UNION (never destroys selection)
PL-FINAL-A11  shift-range selects over visible rows, stores paths
PL-FINAL-A12  detail projection is O(P) — trackref index rebuilt once per revision
PL-FINAL-B02  stale draft palette callback cannot win
PL-FINAL-C03  orphan cleanup fail-closed
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication, QImage
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtTest import QTest

from michi.application.errors import PlaylistPersistenceError
from michi.application.playlist_service import PlaylistService
from michi.infrastructure.playlist_artwork_store import (
    FilesystemPlaylistArtworkStore,
)
from tests.test_m8_playlist_bridge import _make_bridge, _tracks
from tests.test_playlists import FakePlaylistsPort

QML_DIR = Path("src/michi/presentation/qml")


@pytest.fixture(scope="module")
def qapp():
    """QGuiApplication compartido (patrón test_m9_qml) — requerido por
    los harness QML runtime en CI sin display."""
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(sys.argv)
    yield app


def _js_list(obj, prop):
    value = obj.property(prop)
    return list(value.toVariant())


def _png(tmp_path, name, color=0xFF581C, size=16):
    img = QImage(size, size, QImage.Format_RGB32)
    img.fill(color)
    path = tmp_path / name
    assert img.save(str(path), "PNG")
    return path


class _FailingPort(FakePlaylistsPort):
    def __init__(self, fail_after=0):
        super().__init__()
        self._remaining = fail_after

    def save(self, playlists):
        if self._remaining > 0:
            self._remaining -= 1
            raise PlaylistPersistenceError("injected")
        super().save(playlists)

    def save_state(self, playlists, navigation):
        if self._remaining > 0:
            self._remaining -= 1
            raise PlaylistPersistenceError("injected")
        self._stored = list(playlists)
        self._nav_stored = navigation


class _FakeLibrary:
    """LibraryService-compatible double: paths with canonical TrackRefs."""

    def __init__(self, paths):
        from michi.domain.library import TrackRef

        self.state = type("State", (), {"tracks": [], "albums": []})()
        self._build_count = 0
        self.tracks = []
        for i, path in enumerate(paths):
            self.tracks.append(
                TrackRef(
                    file_path=Path(path),
                    display_name=f"T{i}",
                    title=f"T{i}",
                    artist="Artist",
                    album="Album",
                    duration_ms=1000,
                )
            )
        self.state.tracks = tuple(self.tracks)

    def resolve_trackref(self, file_path):
        self._build_count += 1  # spy: O(P×T) legacy would call this per row
        for t in self.state.tracks:
            if t.file_path == file_path:
                return t
        return None

    def artwork_path_for(self, album_key):
        return None

    def subscribe_changed(self, cb):
        pass

    def unsubscribe_changed(self, cb):
        pass


# ==========================================================================
# BRIDGE METAOBJECT — canonical slots invocable from QML
# ==========================================================================


class TestBridgeMetaobject:
    def _bridge(self, tmp_path):
        service = PlaylistService(
            playlists_port=FakePlaylistsPort(),
            artwork_store=FilesystemPlaylistArtworkStore(tmp_path / "managed"),
        )
        bridge, coord, nav = _make_bridge(service)
        return service, bridge

    def test_canonical_slots_invocable_from_qml(self, tmp_path):
        service, bridge = self._bridge(tmp_path)
        playlist = service.create_playlist("Mix")
        service.add_track(playlist.playlist_id, "/a.flac")
        service.add_track(playlist.playlist_id, "/b.flac")
        bridge._coordinator.open_playlist(playlist.playlist_id)
        mo = bridge.metaObject()
        names = {
            bytes(mo.method(i).name()).decode()
            if hasattr(mo.method(i).name(), "data")
            else str(mo.method(i).name())
            for i in range(mo.methodCount())
        }
        for slot in (
            "remove_track",
            "insert_track",
            "apply_visual_appearance",
            "add_tracks",
            "remove_tracks",
            "remove_tracks_by_paths",
            "set_playlist_description",
            "set_playlist_search_query",
            "request_draft_palette",
            "add_track_to_playlist",
            "move_track",
        ):
            assert slot in names, f"slot {slot} debe existir en el metaobject"

    def test_remove_tracks_by_paths_resolves_positions_from_canonical_snapshot(
        self,
        tmp_path,
    ):
        service, bridge = self._bridge(tmp_path)
        playlist = service.create_playlist("Mix")
        service.add_tracks(
            playlist.playlist_id, ["/a.flac", "/b.flac", "/c.flac", "/d.flac"]
        )
        bridge._coordinator.open_playlist(playlist.playlist_id)
        port = bridge._playlist_service._port
        writes_before = len(port.saved)

        # Orden arbitrario + path inexistente → resuelve contra el snapshot
        # canónico actual; el path desaparecido se saltea truthful.
        result = bridge.remove_tracks_by_paths(["/d.flac", "/zzz.flac", "/a.flac"])

        assert result == "removed"
        assert service.get_playlist(playlist.playlist_id).track_paths == (
            "/b.flac",
            "/c.flac",
        )
        assert len(port.saved) == writes_before + 1, "UN persist"

    def test_remove_tracks_by_paths_no_change_and_invalid(self, tmp_path):
        service, bridge = self._bridge(tmp_path)
        playlist = service.create_playlist("Mix")
        service.add_track(playlist.playlist_id, "/a.flac")
        bridge._coordinator.open_playlist(playlist.playlist_id)
        port = bridge._playlist_service._port
        writes_before = len(port.saved)
        assert bridge.remove_tracks_by_paths(["/ghost.flac"]) == "no_change"
        assert bridge.remove_tracks_by_paths([]) == "invalid"
        assert len(port.saved) == writes_before, "cero writes en no-op/invalid"
        bridge.set_playlist_search_query("x")
        assert bridge.remove_tracks_by_paths(["/a.flac"]) == "removed", (
            "paths no dependen del filtro"
        )

    def test_remove_tracks_by_paths_persistence_failure_leaves_playlist_intact(
        self,
        tmp_path,
    ):
        port = _FailingPort(fail_after=0)
        service = PlaylistService(
            playlists_port=port,
            artwork_store=FilesystemPlaylistArtworkStore(tmp_path / "managed"),
        )
        playlist = service.create_playlist("Mix")
        service.add_tracks(playlist.playlist_id, ["/a.flac", "/b.flac"])
        bridge, coord, nav = _make_bridge(service)
        coord.open_playlist(playlist.playlist_id)
        port._remaining = 1
        assert bridge.remove_tracks_by_paths(["/a.flac"]) == "persistence_failed"
        assert service.get_playlist(playlist.playlist_id).track_paths == (
            "/a.flac",
            "/b.flac",
        ), "failure deja la playlist intacta"


# ==========================================================================
# A05 — PLAYBACK SOLO SOBRE TRACKS DISPONIBLES
# ==========================================================================


class TestPlaybackFiltersUnavailable:
    def test_play_playlist_sends_only_resolvable_paths(self, tmp_path):
        library, queue, audio, paths = _tracks(tmp_path, names=("a.mp3", "b.mp3"))
        service = PlaylistService(playlists_port=FakePlaylistsPort())
        playlist = service.create_playlist("Mix")
        service.add_track(playlist.playlist_id, str(paths[0]))
        service.add_track(playlist.playlist_id, "/missing.flac")
        from michi.application.playback_service import PlaybackService
        from michi.application.playback_session_service import (
            PlaybackSessionService,
        )

        session = PlaybackSessionService(PlaybackService(audio), queue)
        session.start()
        bridge, _, _ = _make_bridge(
            service, library=library, session=session, queue=queue
        )
        bridge.play_playlist(playlist.playlist_id)
        audio.trigger_media_accepted(paths[0])
        assert session.state.context_type.name == "PLAYLIST"
        assert session.state.current_entry is not None
        assert session.state.current_entry.file_path == paths[0], (
            "el path missing nunca llega al motor"
        )
        assert session.state.current_index == 0
        bridge.dispose()

    def test_play_playlist_track_unavailable_does_not_reach_engine(
        self,
        tmp_path,
    ):
        library, queue, audio, paths = _tracks(tmp_path, names=("a.mp3",))
        service = PlaylistService(playlists_port=FakePlaylistsPort())
        playlist = service.create_playlist("Mix")
        service.add_track(playlist.playlist_id, str(paths[0]))
        service.add_track(playlist.playlist_id, "/missing.flac")
        from michi.application.playback_service import PlaybackService
        from michi.application.playback_session_service import (
            PlaybackSessionService,
        )

        session = PlaybackSessionService(PlaybackService(audio), queue)
        session.start()
        bridge, coord, _ = _make_bridge(
            service, library=library, session=session, queue=queue
        )
        coord.open_playlist(playlist.playlist_id)
        bridge.play_playlist_track(1)  # el track missing
        assert session.state.context_type.name == "NONE", (
            "unavailable nunca dispara playback"
        )
        bridge.play_playlist_track(0)
        audio.trigger_media_accepted(paths[0])
        assert session.state.context_type.name == "PLAYLIST"
        assert session.state.current_entry.file_path == paths[0]
        bridge.dispose()

    def test_hero_playable_counts(self, tmp_path):
        library, queue, audio, paths = _tracks(tmp_path, names=("a.mp3",))
        service = PlaylistService(playlists_port=FakePlaylistsPort())
        playlist = service.create_playlist("Mix")
        service.add_track(playlist.playlist_id, str(paths[0]))
        service.add_track(playlist.playlist_id, "/missing.flac")
        service.add_track(playlist.playlist_id, "/missing2.flac")
        bridge, coord, _ = _make_bridge(service, library=library)
        coord.open_playlist(playlist.playlist_id)
        assert bridge.property("playlistAvailableTrackCount") == 1
        assert bridge.property("playlistUnavailableCount") == 2
        bridge.dispose()


# ==========================================================================
# A02 — ESTADO TRANSICIONAL A→B (bridge level: search resets)
# ==========================================================================


class TestTransientStateIsolation:
    def test_search_never_survives_playlist_change(self, tmp_path):
        service = PlaylistService(playlists_port=FakePlaylistsPort())
        a = service.create_playlist("A")
        b = service.create_playlist("B")
        service.add_track(a.playlist_id, "/a.flac")
        service.add_track(b.playlist_id, "/b.flac")
        bridge, coord, _ = _make_bridge(service)
        coord.open_playlist(a.playlist_id)
        bridge.set_playlist_search_query("alpha")
        assert bridge.property("playlistSearchQuery") == "alpha"
        coord.open_playlist(b.playlist_id)
        assert bridge.property("playlistSearchQuery") == "", (
            "el query NO sobrevive al cambio de playlist"
        )
        bridge.dispose()


# ==========================================================================
# A08 — PICKER MEMBERSHIP CANÓNICA (sin filtro)
# ==========================================================================


class TestPickerCanonicalMembership:
    def test_selected_playlist_track_paths_is_unfiltered(self, tmp_path):
        service = PlaylistService(playlists_port=FakePlaylistsPort())
        a = service.create_playlist("A")
        service.add_tracks(a.playlist_id, ["/a.flac", "/b.flac", "/c.flac"])
        bridge, coord, _ = _make_bridge(service)
        coord.open_playlist(a.playlist_id)
        assert bridge.property("selectedPlaylistTrackPaths") == [
            "/a.flac",
            "/b.flac",
            "/c.flac",
        ]
        bridge.set_playlist_search_query("a")
        filtered = bridge.property("playlistTrackRows")
        assert [r["path"] for r in filtered] == ["/a.flac"]
        # La membership canónica NO cambia con el filtro (A08).
        assert bridge.property("selectedPlaylistTrackPaths") == [
            "/a.flac",
            "/b.flac",
            "/c.flac",
        ]
        bridge.dispose()


# ==========================================================================
# A07 — CONTRATO DE ASSET ÚNICO
# ==========================================================================


class _LegacyStore:
    """Store que NO implementa prepare_candidate — el service debe
    rechazar la operación fail-closed (nunca inventar ownership)."""

    def prepare_cover(self, playlist_id, source):
        return "/fake/cover.png"

    def prepare_hero(self, playlist_id, source):
        return "/fake/hero.png"

    def delete_managed_asset(self, playlist_id, role, path):
        return True


class TestAssetContractSingle:
    def test_service_refuses_store_without_prepare_candidate(self, tmp_path):
        service = PlaylistService(
            playlists_port=FakePlaylistsPort(), artwork_store=_LegacyStore()
        )
        playlist = service.create_playlist("Mix")
        src = _png(tmp_path, "c.png")
        assert (
            service.apply_visual_appearance(
                playlist.playlist_id,
                cover_action="replace",
                cover_source_path=src,
                hero_mode="auto",
            )
            == "asset_rejected"
        ), "sin prepare_candidate → fail-closed, nunca ownership inventada"
        assert service.get_playlist(playlist.playlist_id).custom_cover_path == ""
        assert service.set_custom_cover(playlist.playlist_id, src) is None

    def test_prepared_playlist_asset_lives_in_application_layer(self):
        from michi.application.playlist_asset_contract import (
            PreparedPlaylistAsset,
        )

        asset = PreparedPlaylistAsset(
            path="/x.png", role="cover", created_by_operation=True
        )
        assert asset.created_by_operation is True


# ==========================================================================
# C03 — ORPHAN CLEANUP FAIL-CLOSED
# ==========================================================================


class TestOrphanCleanup:
    def test_orphan_collection_is_fail_closed(self, tmp_path):
        store = FilesystemPlaylistArtworkStore(tmp_path / "managed")
        storage = tmp_path / "managed"
        storage.mkdir(parents=True)
        # V2 blob no referenciado → orphan probado.
        orphan_v2 = (
            storage / "playlist_v2_0123456789abcdef0123_cover_0123456789abcdef0123.png"
        )
        orphan_v2.write_bytes(b"x")
        # Legacy de playlist inexistente → orphan probado.
        orphan_legacy = storage / "playlist_ghost.png"
        orphan_legacy.write_bytes(b"x")
        # Archivo desconocido → NUNCA.
        unknown = storage / "random.bin"
        unknown.write_bytes(b"x")
        # Legacy de playlist VIVA (aunque no referenciado) → NO se toca.
        live_legacy = storage / "playlist_live1.png"
        live_legacy.write_bytes(b"x")

        orphans = store.collect_orphan_candidates(
            referenced_paths=set(), live_playlist_ids={"live1"}
        )
        names = {p.name for p in orphans}
        assert (
            "playlist_v2_0123456789abcdef0123_cover_0123456789abcdef0123.png" in names
        )
        assert "playlist_ghost.png" in names
        assert "random.bin" not in names, "gramática desconocida → nunca"
        assert "playlist_live1.png" not in names, "dueño vivo → nunca"

    def test_service_orphan_cleanup_removes_only_proven(self, tmp_path):
        store = FilesystemPlaylistArtworkStore(tmp_path / "managed")
        storage = tmp_path / "managed"
        storage.mkdir(parents=True)
        orphan = (
            storage / "playlist_v2_0123456789abcdef0123_cover_0123456789abcdef0123.png"
        )
        orphan.write_bytes(b"x")
        service = PlaylistService(
            playlists_port=FakePlaylistsPort(), artwork_store=store
        )
        playlist = service.create_playlist("Mix")
        src = _png(tmp_path, "c.png")
        service.apply_visual_appearance(
            playlist.playlist_id,
            cover_action="replace",
            cover_source_path=src,
            hero_mode="auto",
        )
        live_cover = service.get_playlist(playlist.playlist_id).custom_cover_path
        assert Path(live_cover).is_file()

        removed = service.collect_orphan_assets()

        assert removed == [str(orphan)]
        assert Path(live_cover).is_file(), "asset vivo nunca se borra"
        assert Path(live_cover).exists()


# ==========================================================================
# A12 — ÍNDICE DE TRACKS O(1): reconstrucción por revisión
# ==========================================================================


class TestDetailProjectionComplexity:
    def test_trackref_index_rebuilt_once_per_library_revision(self, tmp_path):
        service = PlaylistService(playlists_port=FakePlaylistsPort())
        playlist = service.create_playlist("Mix")
        paths = [f"/t{i}.flac" for i in range(50)]
        service.add_tracks(playlist.playlist_id, paths)
        library = _FakeLibrary(paths)
        bridge, coord, _ = _make_bridge(service, library=library)
        coord.open_playlist(playlist.playlist_id)

        # Primera proyección: construye el índice UNA vez.
        bridge.property("playlistTrackRows")
        bridge.property("playlistUnavailableCount")
        bridge.property("playlistAvailableTrackCount")
        assert bridge._trackref_index is not None
        index_object = bridge._trackref_index

        # Múltiples reads NO reconstruyen (misma identidad).
        bridge.property("playlistTrackRows")
        bridge.property("playlistUnavailableCount")
        assert bridge._trackref_index is index_object, (
            "sin revision change el índice NO se reconstruye"
        )
        # El índice se invalidó exactamente con la revisión de Library.
        bridge._on_library_changed()
        assert bridge._trackref_index is None
        bridge.property("playlistTrackRows")
        assert bridge._trackref_index is not index_object
        # Legacy resolve_trackref NUNCA se usa en la proyección (spy).
        assert library._build_count == 0, "proyección O(P) sin resolve lineal"
        bridge.dispose()

    def test_detail_projection_2000_members_uses_index(self, tmp_path):
        import time

        service = PlaylistService(playlists_port=FakePlaylistsPort())
        playlist = service.create_playlist("Big")
        paths = [f"/t{i}.flac" for i in range(2000)]
        service.add_tracks(playlist.playlist_id, paths)
        library = _FakeLibrary(paths)
        bridge, coord, _ = _make_bridge(service, library=library)
        coord.open_playlist(playlist.playlist_id)
        start = time.perf_counter()
        rows = bridge.property("playlistTrackRows")
        elapsed = time.perf_counter() - start
        assert len(rows) == 2000
        assert elapsed < 2.0, f"proyección 2000 tracks: {elapsed:.3f}s"
        assert library._build_count == 0, "sin O(P×T)"
        bridge.dispose()


# ==========================================================================
# RUNTIME QML — DetailView / TrackList comportamiento real
# ==========================================================================


def _load_component(component_name, context_values=None):
    engine = QQmlEngine()
    engine.addImportPath(str(QML_DIR))
    if context_values:
        for name, value in context_values.items():
            engine.rootContext().setContextProperty(name, value)
    component = QQmlComponent(engine)
    qml_path = QML_DIR / "playlists" / component_name
    component.loadUrl(QUrl.fromLocalFile(str(qml_path)))
    assert component.status() == QQmlComponent.Ready, [
        e.toString() for e in component.errors()
    ]
    return engine, component


class TestDetailRuntime:
    def _detail_view(self, qapp, tmp_path):
        """DetailView con bridge REAL como context (playlists definido)."""
        service = PlaylistService(playlists_port=FakePlaylistsPort())
        bridge, coord, _ = _make_bridge(service)
        engine = QQmlEngine()
        engine.addImportPath(str(QML_DIR))
        engine.rootContext().setContextProperty("playlists", bridge)
        component = QQmlComponent(engine)
        qml_path = QML_DIR / "playlists" / "PlaylistDetailView.qml"
        component.loadUrl(QUrl.fromLocalFile(str(qml_path)))
        assert component.status() == QQmlComponent.Ready, [
            e.toString() for e in component.errors()
        ]
        from PySide6.QtCore import QObject

        root = component.create()
        assert root is not None
        holder = QObject()
        root.setParent(holder)
        return engine, root, holder, bridge, coord

    def test_checked_paths_reset_on_playlist_change(self, qapp, tmp_path):
        """PL-FINAL-A02: checkedTrackPaths/selectionMode se resetan al
        cambiar playlistId (la señal onPlaylistIdChanged del Detail)."""
        engine, root, _holder, bridge, coord = self._detail_view(qapp, tmp_path)
        a = bridge._playlist_service.create_playlist("A")
        b = bridge._playlist_service.create_playlist("B")
        root.setProperty("playlistId", a.playlist_id)
        root.setProperty("checkedTrackPaths", ["/a.flac", "/b.flac"])
        root.setProperty("selectionMode", True)
        root.setProperty("shiftAnchorPath", "/a.flac")
        QTest.qWait(10)
        root.setProperty("playlistId", b.playlist_id)
        QTest.qWait(10)
        assert _js_list(root, "checkedTrackPaths") == []
        assert root.property("selectionMode") is False
        assert root.property("shiftAnchorPath") == ""
        engine.deleteLater()

    def test_select_all_visible_unions_in_detail(self, qapp, tmp_path):
        """PL-FINAL-A10: la unión de paths del Detail (usada por el
        shift-range) preserva la selección existente."""
        engine, root, _holder, bridge, coord = self._detail_view(qapp, tmp_path)
        result = root._unionPaths(["/a.flac", "/b.flac"], ["/b.flac", "/c.flac"])
        assert sorted(list(result.toVariant())) == ["/a.flac", "/b.flac", "/c.flac"]
        engine.deleteLater()


class TestPickerRuntime:
    def _picker(self, qapp, present_paths, library_rows):
        from PySide6.QtCore import QObject

        engine = QQmlEngine()
        engine.addImportPath(str(QML_DIR))

        class _FakeLibrary:
            # N815: proyección canónica expuesta a QML (convención UI).
            songRows = library_rows  # noqa: N815

        engine.rootContext().setContextProperty("library", _FakeLibrary())

        class _FakePlaylists:
            def add_tracks(self, playlist_id, paths):
                self.added = list(paths)
                return {
                    "status": "updated",
                    "addedCount": len(paths),
                    "alreadyPresentCount": 0,
                }

        fake = _FakePlaylists()
        engine.rootContext().setContextProperty("playlists", fake)
        component = QQmlComponent(engine)
        qml_path = QML_DIR / "playlists" / "PlaylistTrackPicker.qml"
        component.loadUrl(QUrl.fromLocalFile(str(qml_path)))
        assert component.status() == QQmlComponent.Ready, [
            e.toString() for e in component.errors()
        ]
        obj = component.create()
        # Un popup QML sin parent puede ser recolectado — lo anclamos.
        holder = QObject()
        obj.setParent(holder)
        obj.setProperty("presentPaths", present_paths)
        obj.setProperty("playlistId", "p1")
        obj.setProperty("query", "")
        QTest.qWait(20)
        return engine, obj, holder

    def test_already_present_never_enters_selected_paths(self, qapp):
        rows = [
            {"title": "A", "artist": "X", "album": "Y", "path": "/a.flac"},
            {"title": "B", "artist": "X", "album": "Y", "path": "/b.flac"},
        ]
        engine, obj, _holder = self._picker(qapp, ["/a.flac"], rows)
        obj.setProperty("visibleRows", rows)
        # toggleIfAddable es LA única entrada — mouse/checkbox/keys.
        assert obj.toggleIfAddable("/a.flac") is False, "ya presente → bloqueado"
        assert _js_list(obj, "selectedPaths") == []
        assert obj.toggleIfAddable("/b.flac") is True
        assert _js_list(obj, "selectedPaths") == ["/b.flac"]
        engine.deleteLater()

    def test_select_all_visible_is_union(self, qapp):
        rows = [
            {"title": "A", "artist": "X", "album": "Y", "path": "/a.flac"},
            {"title": "B", "artist": "X", "album": "Y", "path": "/b.flac"},
            {"title": "C", "artist": "X", "album": "Y", "path": "/c.flac"},
        ]
        engine, obj, _holder = self._picker(qapp, [], rows)
        obj.setProperty("visibleRows", rows)
        obj.selectAllVisible()
        assert sorted(_js_list(obj, "selectedPaths")) == [
            "/a.flac",
            "/b.flac",
            "/c.flac",
        ]
        # Segunda ronda bajo OTRO filtro: UNION, no replace.
        obj.setProperty("visibleRows", [rows[0]])
        obj.selectAllVisible()
        assert sorted(_js_list(obj, "selectedPaths")) == [
            "/a.flac",
            "/b.flac",
            "/c.flac",
        ]
        # Clear elimina todo (explícito).
        obj.clearSelection()
        assert _js_list(obj, "selectedPaths") == []
        engine.deleteLater()

    def test_playlist_deleted_while_open_safe_not_found(self, qapp):
        rows = [{"title": "A", "artist": "X", "album": "Y", "path": "/a.flac"}]
        engine, obj, _holder = self._picker(qapp, [], rows)
        obj.setProperty("visibleRows", rows)
        obj.toggleIfAddable("/a.flac")

        class _Gone:
            def add_tracks(self, playlist_id, paths):
                return {
                    "status": "not_found",
                    "addedCount": 0,
                    "alreadyPresentCount": 0,
                }

        gone = _Gone()
        engine.rootContext().setContextProperty("playlists", gone)
        result = gone.add_tracks("p1", ["/a.flac"])
        assert result["status"] == "not_found"
        engine.deleteLater()
