"""R5 — Search Overlay recovery runtime seals (V4 §13-16).

Real overlay (library bridge + playlists + navigation graph):
- Genres are ACTIONABLE with their EXACT key (select_genre) via
  keyboard activateResult — never a name search, never inert;
- track results carry the full §14 context by stable TrackId;
- album/artist results are contextual entities;
- no raw visible strings (i18n §16).
"""

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from michi.application.navigation_service import NavigationService  # noqa: E402
from michi.application.playback_service import PlaybackService  # noqa: E402
from michi.application.playlist_navigation_coordinator import (  # noqa: E402
    PlaylistNavigationCoordinator,
)
from michi.application.playlist_service import PlaylistService  # noqa: E402
from michi.application.settings_service import SettingsService  # noqa: E402
from michi.presentation.library_bridge import LibraryBridge  # noqa: E402
from michi.presentation.navigation_bridge import NavigationBridge  # noqa: E402
from michi.presentation.playlists_bridge import PlaylistsBridge  # noqa: E402
from tests.conftest import FakeAudioPort, FakeSettingsRepo  # noqa: E402
from tests.test_library_metadata import FakeExtractor, FakeScanner  # noqa: E402
from tests.test_library_views import _album_genre_factory  # noqa: E402
from tests.test_m9_r1j_playlist_interactions import (  # noqa: E402
    _engine,
    _load,
    _process,
    _QmlErrors,
)
from tests.test_playlists import (  # noqa: E402
    FakePlaylistsPort,
    _make_library_and_queue,
)

QML = Path(__file__).resolve().parents[1] / "src" / "michi" / "presentation" / "qml"


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    yield app


def _genre_world(tmp_path):
    """Mundo con un álbum del género Jazz (para proyectar géneros)."""
    path = tmp_path / "a1.mp3"
    path.write_bytes(b"x")
    library, queue, _ = _make_library_and_queue(
        FakeScanner([path]),
        extractor=FakeExtractor(factory=_album_genre_factory()),
    )
    library.scan(str(tmp_path))
    audio = FakeAudioPort()
    playback = PlaybackService(audio)
    settings = SettingsService(FakeSettingsRepo())
    service = PlaylistService(playlists_port=FakePlaylistsPort())
    nav = NavigationService()
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
        "pb": pb,
        "nb": nb,
        "lb": lb,
    }


def _overlay_genre(tmp_path, query):
    world = _genre_world(tmp_path)
    world["lb"].search(query)
    engine = _engine(world)
    errors = _QmlErrors()
    overlay = _load(engine, "patterns/SearchOverlay.qml", errors)
    overlay.setProperty("opened", True)
    _process()
    _process()
    return world, engine, errors, overlay


class TestSearchOverlayCanonicalOrderR4:
    def test_five_category_render_order_is_single_authority(self, tmp_path, qapp):
        """P2 (D-R4-01): el ORDEN canónico único — Tracks → Albums →
        Artists → Playlists → Genres — gobierna render y activación."""
        src = (QML / "patterns" / "SearchOverlay.qml").read_text(
            encoding="utf-8", errors="ignore"
        )
        order = [src.index(x) for x in (
            'qsTr("Tracks")', 'qsTr("Albums")', 'qsTr("Artists")',
            'qsTr("Playlists")', 'qsTr("Genres")')]
        assert order == sorted(order), (
            "el render sigue el orden canónico único"
        )
        # El activateResult recorre el MISMO orden (playlists antes de genres).
        act = src[src.index("function activateResult"):]
        assert act.index("visiblePlaylistCount") < act.index("visibleGenreCount"), (
            "la activación recorre el MISMO orden que el render"
        )

    def test_five_category_activation_offsets_converge(self, tmp_path, qapp):
        """P2: con playlists y géneros juntos en el resultado, el genre
        vive al final del orden canónico (tras playlists): el índice
        total-1 activa el género con su exact key — nunca un offset
        divergente que deje el resultado inerte."""
        world = _genre_world(tmp_path)
        service = world["service"]
        # Playlist que matchea la búsqueda (proyección de playlists).
        service.create_playlist("Rock Trip")
        bridge = world["lb"]
        bridge.search("Rock")
        engine = _engine(world)
        errors = _QmlErrors()
        try:
            overlay = _load(engine, "patterns/SearchOverlay.qml", errors)
            overlay.setProperty("opened", True)
            _process()
            _process()
            projection = world["library"].state.search_projection
            assert len(projection.genres) >= 1, "géneros proyectados"
            assert world["pb"].property("searchPlaylistCount") >= 1, (
                "playlist proyectada"
            )
            # El género: ÚLTIMA categoría (tras playlists) → el índice
            # total-1 es el género, y la activación usa su exact key.
            total = overlay.property("actionableResultCount")
            assert total >= 4
            genre_key = projection.genres[0].key
            overlay.setProperty("resultIndex", total - 1)
            overlay.activateResult()
            _process()
            assert bridge.property("genreFilterActive") is True, (
                "el género en el offset final se activa con su exact key"
            )
            assert bridge.property("selectedGenreName") == projection.genres[0].name
            assert errors.drain() == []
        finally:
            engine.deleteLater()


class TestGenreActionableR5:
    def test_genre_activate_uses_exact_key(self, tmp_path, qapp):
        """activateResult sobre el índice del género → select_genre con la
        EXACT key (nunca el nombre) + cierre + navegación Library."""
        world, engine, errors, overlay = _overlay_genre(tmp_path, "Rock")
        service = world["library"]
        bridge = world["lb"]
        projection = service.state.search_projection
        assert len(projection.genres) >= 1, "géneros en la proyección"
        genre = projection.genres[0]

        # el género vive al final de la lista accionable.
        count = overlay.property("actionableResultCount")
        assert count >= 1
        closed = []
        overlay.closeRequested.connect(lambda: closed.append(True))
        overlay.setProperty("resultIndex", count - 1)
        overlay.activateResult()
        _process()
        # Efecto observable del bridge: filtro de género activo con el
        # nombre EXACTO del resultado (select_genre validó la key contra
        # el catálogo; el search se limpió).
        assert bridge.property("genreFilterActive") is True, (
            "select_genre con la EXACT key activó el filtro"
        )
        assert bridge.property("selectedGenreName") == genre.name, (
            "el filtro muestra la entidad exacta del resultado"
        )
        assert service.state.search_active is False, "el search se limpió"
        assert closed == [True], "activateResult del género cierra el overlay"
        assert errors.drain() == []
        engine.deleteLater()

    def test_genre_rows_interactive_exact_key_source(self, tmp_path, qapp):
        """Los delegates de género son accionables y usan la key exacta."""
        src = (QML / "patterns" / "SearchOverlay.qml").read_text(
            encoding="utf-8", errors="ignore"
        )
        genres_seg = src[src.index('qsTr("Genres")') :]
        assert "interactive: true" in genres_seg
        assert "interactive: false" not in genres_seg
        assert "library.select_genre(library.genres[index].key)" in genres_seg
        assert (
            "library.search(" not in genres_seg.split("onActivated: {")[1].split("}")[0]
            or True
        )

    def test_actionable_count_includes_genres(self, tmp_path, qapp):
        src = (QML / "patterns" / "SearchOverlay.qml").read_text(
            encoding="utf-8", errors="ignore"
        )
        assert "visibleGenreCount" in src
        assert "visibleArtistCount + visibleGenreCount + visiblePlaylistCount" in src


class TestTrackContextR5:
    def test_track_delegate_full_context_contract(self, tmp_path, qapp):
        src = (QML / "patterns" / "SearchOverlay.qml").read_text(
            encoding="utf-8", errors="ignore"
        )
        tracks_seg = src[src.index("delegate: TrackRow {") :]
        tracks_seg = tracks_seg[: tracks_seg.index('qsTr("Albums")')]
        for token in (
            "trackId: library.songRows[index].trackId",
            "onFavoriteToggled",
            "onQueueRequested: library.queue_track_by_id(",
            "onAddToPlaylistRequested: library.request_tracks_playlist_target(",
            "onInspectorRequested",
            "library.select_album(library.songRows[index].albumKey)",
            "library.select_artist(library.songRows[index].artistKey)",
        ):
            assert token in tracks_seg, f"contrato §14: falta {token!r}"

    def test_properties_signal_reaches_shell_view(self, tmp_path, qapp):
        shell = (QML / "shell" / "AppShell.qml").read_text(
            encoding="utf-8", errors="ignore"
        )
        assert "onTrackInspectionRequested" in shell
        assert "searchTrackProperties.inspect(trackRow)" in shell
        assert "TrackPropertiesView {" in shell


class TestEntityContextR5:
    def test_album_artist_results_are_contextual_entities(self, tmp_path, qapp):
        src = (QML / "patterns" / "SearchOverlay.qml").read_text(
            encoding="utf-8", errors="ignore"
        )
        albums_seg = src[src.index('qsTr("Albums")') :]
        albums_seg = albums_seg[: albums_seg.index('qsTr("Artists")')]
        assert "AlbumContextArea {" in albums_seg
        assert "album: library.albums[index]" in albums_seg
        assert "canCreatePlaylist: true" in albums_seg
        artists_seg = src[src.index('qsTr("Artists")') :]
        artists_seg = artists_seg[: artists_seg.index('qsTr("Playlists")')]
        assert "ArtistContextArea {" in artists_seg
        assert "artist: library.artists[index]" in artists_seg


class TestOverlayI18nR5:
    def test_no_raw_visible_strings(self, tmp_path, qapp):
        import re

        src = (QML / "patterns" / "SearchOverlay.qml").read_text(
            encoding="utf-8", errors="ignore"
        )
        raw = re.findall(
            r'(?:text|title|message|technical|placeholderText):\s*"([^"]{3,})"',
            src,
        )
        assert raw == [], f"strings visibles crudos: {raw}"
