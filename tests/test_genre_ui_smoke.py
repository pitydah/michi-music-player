"""Smoke tests for new genre UI components — instantiation and basic rendering."""
import pytest
from unittest.mock import MagicMock
from PySide6.QtWidgets import QApplication


@pytest.fixture(autouse=True, scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TestGenreHubPage:
    def test_instantiation(self):
        from ui.genres.genre_hub_page import GenreHubPage
        page = GenreHubPage()
        assert page is not None

    def test_set_genres_empty(self):
        from ui.genres.genre_hub_page import GenreHubPage
        page = GenreHubPage()
        page.set_genres([])
        assert page is not None

    def test_set_genres_with_data(self):
        from ui.genres.genre_hub_page import GenreHubPage
        page = GenreHubPage()
        genres = [
            {"genre": "Rock", "track_count": 100, "album_count": 10,
             "artist_count": 20, "duration_total": 36000,
             "lossless_count": 80, "lossy_count": 20, "hires_count": 10,
             "missing_metadata_count": 0, "play_count": 500, "health": "ok"},
        ]
        page.set_genres(genres, {"health_pct": 100, "missing_metadata": 0})
        assert page is not None

    def test_signals(self):
        from ui.genres.genre_hub_page import GenreHubPage
        page = GenreHubPage()
        assert hasattr(page, 'genre_selected')
        assert hasattr(page, 'genre_play_requested')
        assert hasattr(page, 'genre_mix_requested')
        assert hasattr(page, 'genre_radio_requested')
        assert hasattr(page, 'genre_cleanup_requested')
        assert hasattr(page, 'cleanup_page_requested')

    def test_search_filter(self):
        from ui.genres.genre_hub_page import GenreHubPage
        page = GenreHubPage()
        page._on_search("Rock")
        assert page._search_text == "Rock"

    def test_filter_health(self):
        from ui.genres.genre_hub_page import GenreHubPage
        page = GenreHubPage()
        page._health_combo.setCurrentIndex(1)
        assert page._filter_health == "ok"


class TestGenreCard:
    def test_instantiation(self):
        from ui.genres.genre_card import GenreCard
        card = GenreCard({
            "genre": "Rock", "track_count": 100, "artist_count": 10,
            "album_count": 5, "duration_total": 20000, "health": "ok",
            "missing_metadata_count": 0,
        })
        assert card is not None

    def test_with_warning(self):
        from ui.genres.genre_card import GenreCard
        card = GenreCard({
            "genre": "Rock", "track_count": 100, "artist_count": 10,
            "album_count": 5, "duration_total": 20000, "health": "warning",
            "missing_metadata_count": 5,
        })
        assert card is not None

    def test_signals(self):
        from ui.genres.genre_card import GenreCard
        card = GenreCard({
            "genre": "Rock", "track_count": 100, "artist_count": 10,
            "album_count": 5, "duration_total": 20000, "health": "ok",
            "missing_metadata_count": 0,
        })
        assert hasattr(card, 'clicked')
        assert hasattr(card, 'play_requested')
        assert hasattr(card, 'mix_requested')


class TestGenreDetailPage:
    def test_instantiation(self):
        from ui.genres.genre_detail_page import GenreDetailPage
        page = GenreDetailPage()
        assert page is not None

    def test_set_genre(self):
        from ui.genres.genre_detail_page import GenreDetailPage
        page = GenreDetailPage()
        page.set_genre({
            "genre": "Rock", "track_count": 50, "artist_count": 10,
            "album_count": 5, "duration_total": 10000,
            "dominant_quality": "Lossless",
            "lossless_count": 40, "lossy_count": 10, "hires_count": 5,
            "missing_metadata_count": 0, "play_count": 200,
        })
        assert page is not None

    def test_signals(self):
        from ui.genres.genre_detail_page import GenreDetailPage
        page = GenreDetailPage()
        assert hasattr(page, 'play_requested')
        assert hasattr(page, 'mix_requested')
        assert hasattr(page, 'radio_requested')
        assert hasattr(page, 'cleanup_requested')


class TestGenreCleanupPage:
    def test_instantiation(self):
        from ui.genres.genre_cleanup_page import GenreCleanupPage
        page = GenreCleanupPage()
        assert page is not None

    def test_set_duplicates(self):
        from ui.genres.genre_cleanup_page import GenreCleanupPage
        page = GenreCleanupPage()
        page.set_duplicates([
            {"canonical": "Rock", "raw_values": ["Rock", "rock"],
             "count": 50, "track_examples": ["/a.flac"]},
        ])
        assert page is not None

    def test_set_junk(self):
        from ui.genres.genre_cleanup_page import GenreCleanupPage
        page = GenreCleanupPage()
        page.set_junk([{"value": "unknown", "count": 5, "examples": []}])
        assert page is not None

    def test_set_rare(self):
        from ui.genres.genre_cleanup_page import GenreCleanupPage
        page = GenreCleanupPage()
        page.set_rare([{"genre": "Weird", "track_count": 2}])
        assert page is not None

    def test_set_untagged(self):
        from ui.genres.genre_cleanup_page import GenreCleanupPage
        page = GenreCleanupPage()
        items = [MagicMock(title="Track 1", artist="Artist", filepath="/a.flac")]
        page.set_untagged({"count": 1, "tracks": items, "total": 1})
        assert page is not None

    def test_set_multi_genre(self):
        from ui.genres.genre_cleanup_page import GenreCleanupPage
        page = GenreCleanupPage()
        page.set_multi_genre([
            {"title": "Multi", "raw_genre": "Rock, Pop",
             "suggested_genres": ["Rock", "Pop"]},
        ])
        assert page is not None

    def test_show_empty(self):
        from ui.genres.genre_cleanup_page import GenreCleanupPage
        page = GenreCleanupPage()
        page.show_empty()
        assert page is not None

    def test_signals(self):
        from ui.genres.genre_cleanup_page import GenreCleanupPage
        page = GenreCleanupPage()
        assert hasattr(page, 'back_requested')
        assert hasattr(page, 'refresh_requested')
        assert hasattr(page, 'cleanup_requested')


class TestGenreEmptyState:
    def test_no_genres(self):
        from ui.genres.genre_empty_states import GenreEmptyState
        state = GenreEmptyState()
        state.show_no_genres()
        assert state is not None

    def test_empty_genre(self):
        from ui.genres.genre_empty_states import GenreEmptyState
        state = GenreEmptyState()
        state.show_empty_genre()
        assert state is not None

    def test_issues_found(self):
        from ui.genres.genre_empty_states import GenreEmptyState
        state = GenreEmptyState()
        state.show_issues_found(dup_count=5, untagged=10, junk=2, rare=3)
        assert state is not None

    def test_error(self):
        from ui.genres.genre_empty_states import GenreEmptyState
        state = GenreEmptyState()
        state.show_error("DB error")
        assert state is not None


class TestGenreStatsPanel:
    def test_instantiation(self):
        from ui.genres.genre_stats_panel import GenreStatsPanel
        panel = GenreStatsPanel()
        assert panel is not None

    def test_set_stats(self):
        from ui.genres.genre_stats_panel import GenreStatsPanel
        panel = GenreStatsPanel()
        panel.set_stats({
            "track_count": 100, "album_count": 10, "artist_count": 20,
            "duration_total": 36000, "dominant_quality": "Lossless",
            "lossless_count": 80, "lossy_count": 20, "hires_count": 10,
            "missing_metadata_count": 0, "play_count": 500,
        })
        assert panel is not None


class TestGenreActionsPanel:
    def test_instantiation(self):
        from ui.genres.genre_actions_panel import GenreActionsPanel
        panel = GenreActionsPanel(genre_key="Rock")
        assert panel is not None

    def test_set_genre_key(self):
        from ui.genres.genre_actions_panel import GenreActionsPanel
        panel = GenreActionsPanel()
        panel.set_genre_key("Jazz")
        assert panel._genre_key == "Jazz"

    def test_signals(self):
        from ui.genres.genre_actions_panel import GenreActionsPanel
        panel = GenreActionsPanel()
        assert hasattr(panel, 'play_requested')
        assert hasattr(panel, 'mix_requested')
        assert hasattr(panel, 'cleanup_requested')
