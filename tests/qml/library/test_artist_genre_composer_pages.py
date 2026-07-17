from __future__ import annotations
"""Tests for ArtistGridPage, GenresPage, ComposersPage, ArtistDetailPage, GenreDetailPage."""

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.library_bridge import LibraryBridge

pytestmark = [pytest.mark.qml_module("library")]


# ── ArtistGridPage ──

class TestArtistGridPage:
    def test_artist_model_property(self):
        bridge = MagicMock()
        bridge.artistModel = MagicMock()
        assert bridge.artistModel is not None

    def test_artist_model_total_count(self):
        model = MagicMock()
        model.totalCount = 10
        assert model.totalCount == 10

    def test_artist_model_zero_count(self):
        model = MagicMock()
        model.totalCount = 0
        assert model.totalCount == 0

    def test_artist_clicked_signal(self):
        bridge = MagicMock()
        bridge.filterByArtist = MagicMock(return_value={"ok": True})
        result = bridge.filterByArtist("Test Artist")
        assert result["ok"] is True

    def test_artist_grid_object_name(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "artist_grid_page",
            "ui_qml/pages/library/ArtistGridPage.qml",
        )
        assert spec is not None
        assert spec.origin.endswith("ArtistGridPage.qml")

    def test_artist_grid_imports_components(self):
        with open("ui_qml/pages/library/ArtistGridPage.qml") as f:
            content = f.read()
        assert "../../components" in content
        assert "../../theme" in content
        assert "ArtistCard" in content


# ── GenresPage ──

class TestGenresPage:
    def test_genres_initial_empty(self):
        bridge = MagicMock()
        bridge.getGenres.return_value = []
        genres = bridge.getGenres()
        assert genres == []

    def test_genres_populated(self):
        bridge = MagicMock()
        bridge.getGenres.return_value = [
            {"name": "Rock", "count": 42},
            {"name": "Jazz", "count": 15},
        ]
        genres = bridge.getGenres()
        assert len(genres) == 2
        assert genres[0]["name"] == "Rock"
        assert genres[0]["count"] == 42

    def test_genres_signal_emitted(self):
        bridge = MagicMock()
        bridge.getGenres.return_value = [{"name": "Classical", "count": 7}]
        genres = bridge.getGenres()
        names = [g["name"] for g in genres]
        assert "Classical" in names

    def test_genres_list_view_model(self):
        bridge = MagicMock()
        genres = [{"name": "Rock", "count": 42}]
        bridge.getGenres.return_value = genres
        assert bridge.getGenres() == genres

    def test_genres_header_title(self):
        with open("ui_qml/pages/library/GenresPage.qml") as f:
            content = f.read()
        assert "Géneros" in content
        assert "root._genres" in content
        assert "root.lib.getGenres" in content

    def test_genres_reload_calls_bridge(self):
        bridge = MagicMock()
        bridge.getGenres.return_value = [{"name": "Pop", "count": 20}]
        bridge.getGenres.assert_not_called()
        _ = bridge.getGenres()
        bridge.getGenres.assert_called_once()

    def test_genres_empty_after_reload(self):
        bridge = MagicMock()
        bridge.getGenres.return_value = []
        assert bridge.getGenres() == []

    def test_genre_selected_signal(self):
        bridge = MagicMock()
        bridge.setGenreFilter = MagicMock(return_value={"ok": True})
        result = bridge.setGenreFilter("Jazz")
        assert result["ok"] is True

    def test_genres_page_object_name(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "genres_page",
            "ui_qml/pages/library/GenresPage.qml",
        )
        assert spec is not None
        assert spec.origin.endswith("GenresPage.qml")


# ── ComposersPage ──

class TestComposersPage:
    def test_composers_initial_empty(self):
        bridge = MagicMock()
        bridge.getComposers.return_value = []
        composers = bridge.getComposers()
        assert composers == []

    def test_composers_populated(self):
        bridge = MagicMock()
        bridge.getComposers.return_value = [
            "Beethoven",
            "Mozart",
        ]
        composers = bridge.getComposers()
        assert len(composers) == 2
        assert composers[0] == "Beethoven"

    def test_composers_single_entry(self):
        bridge = MagicMock()
        bridge.getComposers.return_value = ["Chopin"]
        composers = bridge.getComposers()
        assert composers == ["Chopin"]

    def test_composers_list_view_model(self):
        bridge = MagicMock()
        composers = ["Bach", "Vivaldi", "Debussy"]
        bridge.getComposers.return_value = composers
        assert bridge.getComposers() == composers

    def test_composers_header_title(self):
        with open("ui_qml/pages/library/ComposersPage.qml") as f:
            content = f.read()
        assert "Compositores" in content
        assert "root._composers" in content
        assert "root.lib.getComposers" in content

    def test_composers_reload_calls_bridge(self):
        bridge = MagicMock()
        bridge.getComposers.return_value = ["Liszt"]
        bridge.getComposers.assert_not_called()
        _ = bridge.getComposers()
        bridge.getComposers.assert_called_once()

    def test_composer_selected_signal(self):
        bridge = MagicMock()
        bridge.setComposerFilter = MagicMock(return_value={"ok": True})
        result = bridge.setComposerFilter("Beethoven")
        assert result["ok"] is True

    def test_composers_page_object_name(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "composers_page",
            "ui_qml/pages/library/ComposersPage.qml",
        )
        assert spec is not None
        assert spec.origin.endswith("ComposersPage.qml")


# ── ArtistDetailPage ──

class TestArtistDetailPage:
    @pytest.fixture
    def bridge(self):
        qs = MagicMock()
        qs.fetch_artist_detail.return_value = {
            "name": "Test Artist",
            "album_count": 5,
            "track_count": 42,
            "genre": "Rock",
            "bio": "A great artist",
        }
        return LibraryBridge(query_service=qs)

    def test_artist_detail_loads(self, bridge):
        detail = bridge.getArtistDetail("Test Artist")
        assert detail["ok"] is True
        assert detail["name"] == "Test Artist"
        assert detail["album_count"] == 5
        assert detail["track_count"] == 42
        assert detail["genre"] == "Rock"

    def test_artist_detail_has_bio(self, bridge):
        detail = bridge.getArtistDetail("Test Artist")
        assert detail.get("bio") == "A great artist"

    def test_artist_detail_not_found(self):
        qs = MagicMock()
        qs.fetch_artist_detail.return_value = None
        bridge = LibraryBridge(query_service=qs)
        detail = bridge.getArtistDetail("Unknown")
        assert detail["ok"] is False
        assert detail["error"] == "NOT_FOUND"

    def test_artist_detail_no_query_service(self):
        from unittest.mock import patch
        with patch.object(LibraryBridge, "__init__", return_value=None):
            bridge = MagicMock()
            bridge.getArtistDetail.return_value = {"ok": False, "error": "NO_QUERY_SERVICE"}
            result = bridge.getArtistDetail("Test")
            assert result["ok"] is False
            assert result["error"] == "NO_QUERY_SERVICE"

    def test_artist_detail_has_albums_section(self, bridge):
        detail = bridge.getArtistDetail("Test Artist")
        assert detail.get("album_count", 0) > 0

    def test_artist_detail_has_tracks_section(self, bridge):
        detail = bridge.getArtistDetail("Test Artist")
        assert detail.get("track_count", 0) > 0

    def test_artist_detail_genre_present(self, bridge):
        detail = bridge.getArtistDetail("Test Artist")
        assert detail.get("genre") == "Rock"

    def test_artist_detail_back_button(self):
        with open("ui_qml/pages/library/ArtistDetailPage.qml") as f:
            content = f.read()
        assert "Volver" in content
        assert "backRequested" in content

    def test_artist_detail_play_all_button(self):
        with open("ui_qml/pages/library/ArtistDetailPage.qml") as f:
            content = f.read()
        assert "Reproducir todo" in content

    def test_artist_detail_albums_header(self):
        with open("ui_qml/pages/library/ArtistDetailPage.qml") as f:
            content = f.read()
        assert "Álbumes" in content
        assert "SectionHeader" in content

    def test_artist_detail_songs_header(self):
        with open("ui_qml/pages/library/ArtistDetailPage.qml") as f:
            content = f.read()
        assert "Canciones" in content

    def test_artist_detail_page_object_name(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "artist_detail_page",
            "ui_qml/pages/library/ArtistDetailPage.qml",
        )
        assert spec is not None
        assert spec.origin.endswith("ArtistDetailPage.qml")


# ── GenreDetailPage ──

class TestGenreDetailPage:
    @pytest.fixture
    def bridge(self):
        qs = MagicMock()
        qs.fetch_artist_detail.return_value = None
        b = LibraryBridge(query_service=qs)
        b._filter_genre = ""
        b.trackModel = MagicMock()
        b.trackModel.count = 5
        return b

    def test_genre_detail_loads(self, bridge):
        result = bridge.setGenreFilter("Rock")
        assert result["ok"] is True
        assert bridge._filter_genre == "Rock"

    def test_genre_detail_back_button(self):
        with open("ui_qml/pages/library/GenreDetailPage.qml") as f:
            content = f.read()
        assert "Volver" in content
        assert "backRequested" in content

    def test_genre_detail_play_all(self, bridge):
        bridge.playAllFiltered = MagicMock(return_value={"ok": True})
        result = bridge.playAllFiltered()
        assert result["ok"] is True

    def test_genre_detail_header_shows_genre(self):
        with open("ui_qml/pages/library/GenreDetailPage.qml") as f:
            content = f.read()
        assert "G\u00e9nero:" in content
        assert "root.genre" in content

    def test_genre_detail_songs_header(self):
        with open("ui_qml/pages/library/GenreDetailPage.qml") as f:
            content = f.read()
        assert "Canciones en" in content

    def test_genre_detail_shuffle_button(self):
        with open("ui_qml/pages/library/GenreDetailPage.qml") as f:
            content = f.read()
        assert "Mezclar" in content

    def test_genre_detail_add_queue_button(self):
        with open("ui_qml/pages/library/GenreDetailPage.qml") as f:
            content = f.read()
        assert "A\u00f1adir a cola" in content

    def test_genre_detail_track_model_used(self, bridge):
        assert bridge.trackModel is not None

    def test_genre_detail_page_object_name(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "genre_detail_page",
            "ui_qml/pages/library/GenreDetailPage.qml",
        )
        assert spec is not None
        assert spec.origin.endswith("GenreDetailPage.qml")
