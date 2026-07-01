"""Smoke tests for new genre UI components — instantiation, signals, rendering.

Uses pytest-qt (qtbot) for proper Qt event loop and widget lifecycle.
"""
import pytest

from unittest.mock import MagicMock


def _genre_data(**overrides):
    data = {
        "genre": "Rock", "track_count": 100, "album_count": 10,
        "artist_count": 20, "duration_total": 36000,
        "lossless_count": 80, "lossy_count": 20, "hires_count": 10,
        "missing_metadata_count": 0, "play_count": 500, "health": "ok",
        "dominant_quality": "Lossless", "dominant_format": "FLAC",
    }
    data.update(overrides)
    return data


def _health_summary(**overrides):
    data = {
        "health_pct": 84, "total_genres": 12, "total_tracks": 5000,
        "missing_metadata": 128, "healthy_count": 10, "warning_count": 2,
    }
    data.update(overrides)
    return data


# ── GenreHubPage ──

class TestGenreHubPageQt:
    @pytest.fixture
    def page(self, qtbot):
        from ui.genres.genre_hub_page import GenreHubPage
        p = GenreHubPage()
        p.show()
        qtbot.addWidget(p)
        return p

    def test_instantiation(self, page):
        assert page is not None

    def test_set_genres_empty(self, page):
        page.set_genres([])
        assert page._empty_state.isVisibleTo(page)

    def test_set_genres_with_data(self, page):
        page.set_genres([_genre_data()], _health_summary())
        assert not page._empty_state.isVisibleTo(page)
        assert page._health_card.isVisibleTo(page)

    def test_health_bar_percentage(self, page):
        page.set_genres([_genre_data()], _health_summary(health_pct=100))
        assert "100%" in page._health_pct_lbl.text()

    def test_health_bar_warning(self, page):
        page.set_genres([_genre_data()], _health_summary(health_pct=50))
        assert "50%" in page._health_pct_lbl.text()

    def test_signals_defined(self, page):
        assert hasattr(page, 'genre_selected')
        assert hasattr(page, 'genre_play_requested')
        assert hasattr(page, 'genre_mix_requested')
        assert hasattr(page, 'genre_radio_requested')
        assert hasattr(page, 'genre_cleanup_requested')
        assert hasattr(page, 'cleanup_page_requested')

    def test_search_filters(self, page):
        page.set_genres([
            _genre_data(genre="Rock"),
            _genre_data(genre="Pop"),
            _genre_data(genre="Jazz"),
        ], _health_summary())
        page._on_search("Rock")
        assert page._search_text == "Rock"

    def test_filter_health(self, page):
        page._health_combo.setCurrentIndex(1)
        assert page._filter_health == "ok"

    def test_sort_by_tracks(self, page):
        page._sort_combo.setCurrentIndex(0)
        assert page._sort_key == "track_count"

    def test_genre_selected_signal(self, page, qtbot):
        page.set_genres([_genre_data(genre="Rock")], _health_summary())
        with qtbot.waitSignal(page.genre_selected, timeout=100):
            page.genre_selected.emit("Rock")

    def test_cleanup_page_requested_signal(self, page, qtbot):
        with qtbot.waitSignal(page.cleanup_page_requested, timeout=100):
            page.cleanup_page_requested.emit()

    def test_mix_requested_signal(self, page, qtbot):
        with qtbot.waitSignal(page.genre_mix_requested, timeout=100):
            page.genre_mix_requested.emit("Rock")

    def test_radio_requested_signal(self, page, qtbot):
        with qtbot.waitSignal(page.genre_radio_requested, timeout=100):
            page.genre_radio_requested.emit("Rock")


# ── GenreCard ──

class TestGenreCardQt:
    @pytest.fixture
    def card(self, qtbot):
        from ui.genres.genre_card import GenreCard
        c = GenreCard(_genre_data())
        qtbot.addWidget(c)
        return c

    def test_instantiation(self, card):
        assert card is not None

    def test_with_warning(self, qtbot):
        from ui.genres.genre_card import GenreCard
        c = GenreCard(_genre_data(health="warning", missing_metadata_count=5))
        qtbot.addWidget(c)
        assert c is not None

    def test_signals_defined(self, card):
        assert hasattr(card, 'clicked')
        assert hasattr(card, 'play_requested')
        assert hasattr(card, 'mix_requested')

    def test_click_emits_signal(self, card, qtbot):
        with qtbot.waitSignal(card.clicked, timeout=100):
            card.clicked.emit(card._genre_key)


# ── GenreDetailPage ──

class TestGenreDetailPageQt:
    @pytest.fixture
    def page(self, qtbot):
        from ui.genres.genre_detail_page import GenreDetailPage
        p = GenreDetailPage()
        qtbot.addWidget(p)
        return p

    def test_instantiation(self, page):
        assert page is not None

    def test_set_genre(self, page):
        page.set_genre(_genre_data())
        assert page._genre_data is not None

    def test_signals_defined(self, page):
        assert hasattr(page, 'play_requested')
        assert hasattr(page, 'mix_requested')
        assert hasattr(page, 'radio_requested')
        assert hasattr(page, 'cleanup_requested')

    def test_play_signal(self, page, qtbot):
        with qtbot.waitSignal(page.play_requested, timeout=100):
            page.play_requested.emit("Rock")

    def test_mix_signal(self, page, qtbot):
        with qtbot.waitSignal(page.mix_requested, timeout=100):
            page.mix_requested.emit("Rock")

    def test_cleanup_signal(self, page, qtbot):
        with qtbot.waitSignal(page.cleanup_requested, timeout=100):
            page.cleanup_requested.emit("Rock")


# ── GenreCleanupPage ──

class TestGenreCleanupPageQt:
    @pytest.fixture
    def page(self, qtbot):
        from ui.genres.genre_cleanup_page import GenreCleanupPage
        p = GenreCleanupPage()
        p.show()
        qtbot.addWidget(p)
        return p

    def test_instantiation(self, page):
        assert page is not None

    def test_set_duplicates(self, page):
        page.set_duplicates([
            {"canonical": "Rock", "raw_values": ["Rock", "rock"],
             "count": 50, "track_examples": ["/a.flac"]},
        ])
        assert page._duplicates_section["card"].isVisibleTo(page)

    def test_set_junk(self, page):
        page.set_junk([{"value": "unknown", "count": 5, "examples": []}])
        assert page._junk_section["card"].isVisibleTo(page)

    def test_set_rare(self, page):
        page.set_rare([{"genre": "Weird", "track_count": 2}])
        assert page._rare_section["card"].isVisibleTo(page)

    def test_set_untagged(self, page):
        items = [MagicMock(title="Track 1", artist="Artist", filepath="/a.flac")]
        page.set_untagged({"count": 1, "tracks": items, "total": 1})
        assert page._untagged_section["card"].isVisibleTo(page)

    def test_set_multi_genre(self, page):
        page.set_multi_genre([
            {"title": "Multi", "raw_genre": "Rock, Pop",
             "suggested_genres": ["Rock", "Pop"]},
        ])
        assert page._multi_section["card"].isVisibleTo(page)

    def test_show_empty(self, page):
        page.show_empty()
        assert page._empty_state.isVisibleTo(page)

    def test_signals_defined(self, page):
        assert hasattr(page, 'back_requested')
        assert hasattr(page, 'refresh_requested')
        assert hasattr(page, 'cleanup_requested')

    def test_refresh_signal(self, page, qtbot):
        with qtbot.waitSignal(page.refresh_requested, timeout=100):
            page.refresh_requested.emit()

    def test_duplicates_then_empty_clears(self, page):
        page.set_duplicates([{"canonical": "Rock", "raw_values": ["Rock"],
                              "count": 5, "track_examples": []}])
        assert page._duplicates_section["card"].isVisibleTo(page)
        page.set_duplicates([])
        assert not page._duplicates_section["card"].isVisibleTo(page)


# ── GenreEmptyState ──

class TestGenreEmptyStateQt:
    @pytest.fixture
    def state(self, qtbot):
        from ui.genres.genre_empty_states import GenreEmptyState
        s = GenreEmptyState()
        s.show()
        qtbot.addWidget(s)
        return s

    def test_no_genres(self, state):
        state.show_no_genres()
        assert state._primary_btn.isVisibleTo(state)
        assert state._secondary_btn.isVisibleTo(state)

    def test_empty_genre(self, state):
        state.show_empty_genre()
        assert not state._primary_btn.isVisibleTo(state)

    def test_issues_found(self, state):
        state.show_issues_found(dup_count=5, untagged=10, junk=2, rare=3)
        assert state._primary_btn.isVisibleTo(state)

    def test_error(self, state):
        state.show_error("DB error")
        assert not state._primary_btn.isVisibleTo(state)

    def test_primary_action_signal(self, state, qtbot):
        with qtbot.waitSignal(state.primary_clicked, timeout=100):
            state.primary_clicked.emit()


# ── GenreStatsPanel ──

class TestGenreStatsPanelQt:
    @pytest.fixture
    def panel(self, qtbot):
        from ui.genres.genre_stats_panel import GenreStatsPanel
        p = GenreStatsPanel()
        qtbot.addWidget(p)
        return p

    def test_instantiation(self, panel):
        assert panel is not None

    def test_set_stats(self, panel):
        panel.set_stats(_genre_data())
        assert panel is not None


# ── GenreActionsPanel ──

class TestGenreActionsPanelQt:
    @pytest.fixture
    def panel(self, qtbot):
        from ui.genres.genre_actions_panel import GenreActionsPanel
        p = GenreActionsPanel(genre_key="Rock")
        qtbot.addWidget(p)
        return p

    def test_instantiation(self, panel):
        assert panel is not None

    def test_set_genre_key(self, qtbot):
        from ui.genres.genre_actions_panel import GenreActionsPanel
        p = GenreActionsPanel()
        qtbot.addWidget(p)
        p.set_genre_key("Jazz")
        assert p._genre_key == "Jazz"

    def test_signals_defined(self, panel):
        assert hasattr(panel, 'play_requested')
        assert hasattr(panel, 'mix_requested')
        assert hasattr(panel, 'cleanup_requested')

    def test_play_signal(self, panel, qtbot):
        with qtbot.waitSignal(panel.play_requested, timeout=100):
            panel.play_requested.emit("Rock")
