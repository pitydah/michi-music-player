"""Tests: SongsFilterBar — current_state emits all fields correctly."""

from unittest.mock import MagicMock

from library.songs_view_state import SongsFilterState


def _make_bar(**overrides):
    """Create a mock SongsFilterBar bypassing __init__ (needs QApplication)."""
    from ui.library.songs_filter_bar import SongsFilterBar
    bar = SongsFilterBar.__new__(SongsFilterBar)

    defaults = dict(
        format_data="", quality_data="", genre_data="",
        year_min="", year_max="", sr_text="", br_text="",
        fav=False, meta=False, cover=False, missing=False, al=False,
    )
    defaults.update(overrides)

    bar._format_combo = MagicMock()
    bar._format_combo.currentData.return_value = defaults["format_data"]
    bar._quality_combo = MagicMock()
    bar._quality_combo.currentData.return_value = defaults["quality_data"]
    bar._genre_combo = MagicMock()
    bar._genre_combo.currentData.return_value = defaults["genre_data"]
    bar._year_min = MagicMock()
    bar._year_min.text.return_value = defaults["year_min"]
    bar._year_max = MagicMock()
    bar._year_max.text.return_value = defaults["year_max"]
    bar._sr_input = MagicMock()
    bar._sr_input.text.return_value = defaults["sr_text"]
    bar._br_input = MagicMock()
    bar._br_input.text.return_value = defaults["br_text"]
    bar._fav_check = MagicMock()
    bar._fav_check.isChecked.return_value = defaults["fav"]
    bar._meta_check = MagicMock()
    bar._meta_check.isChecked.return_value = defaults["meta"]
    bar._cover_check = MagicMock()
    bar._cover_check.isChecked.return_value = defaults["cover"]
    bar._missing_check = MagicMock()
    bar._missing_check.isChecked.return_value = defaults["missing"]
    bar._al_check = MagicMock()
    bar._al_check.isChecked.return_value = defaults["al"]
    return bar


class TestSongsFilterBar:

    def test_default_state_all_empty(self):
        state = _make_bar().current_state()
        assert isinstance(state, SongsFilterState)
        assert state.formats == frozenset()
        assert state.qualities == frozenset()
        assert state.genres == frozenset()
        assert state.year_min is None
        assert state.year_max is None
        assert state.sample_rate_min is None
        assert state.bitrate_min is None
        assert state.only_favorites is False
        assert state.only_missing_metadata is False
        assert state.only_missing_cover is False
        assert state.only_missing_file is False
        assert state.only_audio_lab_warning is False

    def test_format(self):
        state = _make_bar(format_data="FLAC").current_state()
        assert "FLAC" in state.formats

    def test_quality(self):
        state = _make_bar(quality_data="hires").current_state()
        assert "hires" in state.qualities

    def test_genre(self):
        state = _make_bar(genre_data="Rock").current_state()
        assert "Rock" in state.genres

    def test_year_min(self):
        state = _make_bar(year_min="1990").current_state()
        assert state.year_min == 1990

    def test_year_max(self):
        state = _make_bar(year_max="2020").current_state()
        assert state.year_max == 2020

    def test_sample_rate_converts_khz_to_hz(self):
        state = _make_bar(sr_text="96").current_state()
        assert state.sample_rate_min == 96000

    def test_sample_rate_invalid_ignored(self):
        state = _make_bar(sr_text="abc").current_state()
        assert state.sample_rate_min is None

    def test_bitrate_min(self):
        state = _make_bar(br_text="320").current_state()
        assert state.bitrate_min == 320

    def test_favorites(self):
        state = _make_bar(fav=True).current_state()
        assert state.only_favorites is True

    def test_missing_metadata(self):
        state = _make_bar(meta=True).current_state()
        assert state.only_missing_metadata is True

    def test_missing_cover(self):
        state = _make_bar(cover=True).current_state()
        assert state.only_missing_cover is True

    def test_missing_file(self):
        state = _make_bar(missing=True).current_state()
        assert state.only_missing_file is True

    def test_audio_lab_warning(self):
        state = _make_bar(al=True).current_state()
        assert state.only_audio_lab_warning is True

    def test_all_filters_combined(self):
        state = _make_bar(
            format_data="FLAC", quality_data="hires", genre_data="Rock",
            year_min="2000", year_max="2020", sr_text="96", br_text="1000",
            fav=True, meta=True, cover=True, missing=True, al=True,
        ).current_state()
        assert "FLAC" in state.formats
        assert "hires" in state.qualities
        assert "Rock" in state.genres
        assert state.year_min == 2000
        assert state.year_max == 2020
        assert state.sample_rate_min == 96000
        assert state.bitrate_min == 1000
        assert state.only_favorites is True
        assert state.only_missing_metadata is True
        assert state.only_missing_cover is True
        assert state.only_missing_file is True
        assert state.only_audio_lab_warning is True
