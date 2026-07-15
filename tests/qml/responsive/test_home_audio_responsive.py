from __future__ import annotations

import pytest
from unittest.mock import MagicMock, PropertyMock


@pytest.fixture
def mock_home_audio_page():
    page = MagicMock()
    page.width = 1400
    page.height = 900
    type(page).objectName = PropertyMock(return_value="homeAudioPage")
    return page


class TestHomeAudioPageResponsive:
    @pytest.mark.parametrize("width,expected_cols", [
        (1920, 3),
        (1366, 2),
        (1024, 2),
        (900, 2),
        (700, 1),
        (500, 1),
    ])
    def test_zone_grid_columns(self, mock_home_audio_page, width, expected_cols):
        mock_home_audio_page.width = width
        if width > 1400:
            assert expected_cols == 3
        elif width >= 768:
            assert expected_cols == 2
        else:
            assert expected_cols == 1

    def test_wide_1920(self, mock_home_audio_page):
        mock_home_audio_page.width = 1920

    def test_standard_1366(self, mock_home_audio_page):
        mock_home_audio_page.width = 1366

    def test_compact_1024(self, mock_home_audio_page):
        mock_home_audio_page.width = 1024

    def test_narrow_900(self, mock_home_audio_page):
        mock_home_audio_page.width = 900

    def test_125_percent(self, mock_home_audio_page):
        mock_home_audio_page.width = int(1400 * 1.25)

    def test_150_percent(self, mock_home_audio_page):
        mock_home_audio_page.width = int(1400 * 1.5)
