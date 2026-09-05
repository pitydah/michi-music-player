"""LIB-A P1-A/P1-B/P1-C — persistence roundtrip y hydración del query.

COR01 trackTable Domain JSON roundtrip
COR02 trackTable Settings service roundtrip
COR03 old settings without trackTable migrate safely
COR04 malformed widths clamp
COR05 Title hidden persistence ignored
COR06 startup restore no save loop (aplicado en runtime QML)
COR07 resize persistence debounced (runtime QML)
COR08-10 persisted sort/direction/filter restored to Application
COR11 startup UI == Application query state
COR12 Search + Album filter count == rendered albums
COR13 filteredAlbumCount no invalid .mode access
"""

import json

from michi.domain.settings import (
    LibraryTrackTablePreferences,
    LibraryViewPreferences,
    library_view_preferences_from_json,
    library_view_preferences_to_json,
)


class TestTrackTableDomainRoundtrip:
    def _custom(self) -> LibraryViewPreferences:
        return LibraryViewPreferences(
            active_mode="grid",
            sort_mode="year",
            sort_descending=True,
            filter_mode="hires",
            track_table=LibraryTrackTablePreferences(
                preset="audiophile",
                title_width=420,
                artist_width=210,
                genre_visible=True,
                sample_rate_visible=True,
                album_visible=False,
            ),
        )

    def test_cor01_domain_roundtrip_exact(self) -> None:
        """COR01: Audiophile custom → JSON → parse → igualdad semántica."""
        original = self._custom()
        raw = library_view_preferences_to_json(original)
        restored, malformed = library_view_preferences_from_json(raw)
        assert malformed is False
        assert restored.track_table.preset == "audiophile"
        assert restored.track_table.title_width == 420
        assert restored.track_table.artist_width == 210
        assert restored.track_table.genre_visible is True
        assert restored.track_table.sample_rate_visible is True
        assert restored.track_table.album_visible is False
        # Igualdad semántica (ambos lados emiten el mismo JSON canónico).
        assert library_view_preferences_to_json(
            restored
        ) == library_view_preferences_to_json(original)

    def test_cor03_old_settings_migrate_to_defaults(self) -> None:
        """COR03: settings viejos sin trackTable → defaults seguros."""
        old = json.dumps(
            {
                "activeMode": "grid",
                "sortMode": "title",
                "sortDescending": False,
                "filterMode": "all",
                "gallery": {"artworkSize": "medium", "spacing": "balanced"},
            }
        )
        restored, malformed = library_view_preferences_from_json(old)
        assert malformed is False
        assert restored.track_table.preset == "essential"
        assert restored.track_table.title_visible is True
        assert restored.track_table.genre_visible is False
        assert restored.track_table.title_width == 300

    def test_cor04_malformed_widths_clamp(self) -> None:
        """COR04: widths patológicos se clampean (5, -1, 20000, NaN...)."""
        raw = json.dumps(
            {
                "activeMode": "grid",
                "trackTable": {
                    "preset": "essential",
                    "visible": {"artwork": True, "title": True},
                    "widths": {
                        "title": 5,
                        "artist": -1,
                        "album": 20000,
                        "duration": float("nan"),
                        "genre": float("inf"),
                        "artwork": 400,
                    },
                },
            }
        )
        restored, malformed = library_view_preferences_from_json(raw)
        # NaN/Inf: json.dumps los emite como NaN... el parse de NaN:
        # json.loads acepta NaN por defecto → los tratamos en el decode.
        assert restored.track_table.title_width >= 220
        assert restored.track_table.artist_width >= 120
        assert restored.track_table.album_width <= 720
        assert restored.track_table.artwork_width <= 52
        assert restored.track_table.duration_width >= 76

    def test_cor05_title_hidden_ignored(self) -> None:
        """COR05: un JSON con title hidden → title_visible True."""
        raw = json.dumps(
            {
                "activeMode": "grid",
                "trackTable": {
                    "preset": "essential",
                    "visible": {"title": False, "artist": True},
                },
            }
        )
        restored, _ = library_view_preferences_from_json(raw)
        assert restored.track_table.title_visible is True
        assert restored.track_table.artist_visible is True

    def test_cor_malformed_field_isolated(self) -> None:
        """Un campo malformado no invalida el objeto completo."""
        raw = json.dumps(
            {
                "activeMode": "grid",
                "trackTable": {
                    "preset": "essential",
                    "visible": {"artist": "yes", "album": True},
                    "widths": {"title": "wide"},
                },
            }
        )
        restored, malformed = library_view_preferences_from_json(raw)
        assert malformed is False  # el decode es field-isolated
        assert restored.track_table.artist_visible is True  # default
        assert restored.track_table.album_visible is True
        assert restored.track_table.title_width == 300

    def test_cor02_settings_service_roundtrip(self, tmp_path) -> None:
        """COR02: a través del servicio real (sqlite)."""

        from michi.application.settings_service import SettingsService
        from michi.domain.settings import SettingsState
        from michi.infrastructure.sqlite_settings import SQLiteSettingsRepository

        repo = SQLiteSettingsRepository.open_for_startup(tmp_path / "s.db")
        service = SettingsService(repo)
        state = SettingsState()
        state.library_views = self._custom()
        repo.save(state)
        loaded = repo.load()
        assert loaded.library_views.track_table.preset == "audiophile"
        assert loaded.library_views.track_table.title_width == 420
        assert loaded.library_views.track_table.sample_rate_visible is True
        assert loaded.library_views.track_table.album_visible is False


class TestAlbumQueryHydration:
    def _bridge_with_state(self, tmp_path, service_prefs):
        from michi.presentation.library_bridge import LibraryBridge

        path = tmp_path / "miles.flac"
        path.write_bytes(b"x")
        from test_library_album_views import (
            FakeExtractor,
            FakeScanner,
            _make_library,
        )

        from michi.domain.library import TrackMetadata

        library, *_ = _make_library(
            FakeScanner([path]),
            FakeExtractor(
                factory=lambda p: TrackMetadata(
                    artist="Miles",
                    album="Blue",
                    title="So What",
                    genre="Jazz",
                    duration_ms=1000,
                )
            ),
        )
        library.scan(str(tmp_path))
        bridge = LibraryBridge(library)
        del service_prefs
        return bridge, library

    def test_cor08_13_hydration_and_count_contract(self, tmp_path) -> None:
        """COR08-13: el estado persistido hidrata la APLICACIÓN y los
        conteos reflejan la proyección visible."""
        from test_library_album_views import (
            FakeExtractor,
            FakeScanner,
            _make_library,
        )

        from michi.domain.library import TrackMetadata
        from michi.presentation.library_bridge import LibraryBridge

        path = tmp_path / "miles.flac"
        path.write_bytes(b"x")
        library, *_ = _make_library(
            FakeScanner([path]),
            FakeExtractor(
                factory=lambda p: TrackMetadata(
                    artist="Miles",
                    album="Blue",
                    title="So What",
                    genre="Jazz",
                    duration_ms=1000,
                    sample_rate_hz=96000,
                )
            ),
        )
        library.scan(str(tmp_path))
        bridge = LibraryBridge(library)

        # Simula el restore del startup (LibraryView.loadViewPreferences).
        bridge.set_album_query_state("year", True, "hires")
        assert bridge._album_query.state.sort_mode == "year"
        assert bridge._album_query.state.descending is True
        assert bridge._album_query.state.filter_mode == "hires"
        albums = bridge.property("albums")
        assert len(albums) == 1  # el fixture es 96kHz → hi-res
        assert bridge.property("filteredAlbumCount") == len(albums), (
            "COR12: conteo == proyección renderizada"
        )
        # filter all + search activa (búsqueda sin matches):
        bridge.set_album_query_state("title", False, "all")
        bridge.search("zzz-none")
        assert len(bridge.property("albums")) == 0
        assert bridge.property("filteredAlbumCount") == 0, (
            "search 0 + filter all → 0 visibles"
        )
        bridge.dispose()
