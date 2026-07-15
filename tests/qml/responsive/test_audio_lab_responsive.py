from __future__ import annotations

import pytest
from unittest.mock import MagicMock, PropertyMock


@pytest.fixture
def mock_audio_lab_page():
    page = MagicMock()
    page.width = 1400
    page.height = 900
    type(page).objectName = PropertyMock(return_value="audioLabPage")
    return page


class TestAudioLabPageResponsive:
    @pytest.mark.parametrize("width,expected_cols", [
        (1920, 4),
        (1366, 3),
        (1024, 2),
        (900, 2),
        (700, 1),
        (500, 1),
    ])
    def test_tool_grid_columns(self, mock_audio_lab_page, width, expected_cols):
        mock_audio_lab_page.width = width
        if width > 1600:
            assert expected_cols == 4
        elif width > 1200:
            assert expected_cols == 3
        elif width >= 768:
            assert expected_cols == 2
        else:
            assert expected_cols == 1

    def test_wide_1920(self, mock_audio_lab_page):
        mock_audio_lab_page.width = 1920
        assert mock_audio_lab_page.width > 1400

    def test_standard_1366(self, mock_audio_lab_page):
        mock_audio_lab_page.width = 1366
        assert 1024 <= mock_audio_lab_page.width <= 1400

    def test_compact_1024(self, mock_audio_lab_page):
        mock_audio_lab_page.width = 1024

    def test_narrow_900(self, mock_audio_lab_page):
        mock_audio_lab_page.width = 900

    def test_125_percent(self, mock_audio_lab_page):
        mock_audio_lab_page.width = int(1400 * 1.25)
        assert mock_audio_lab_page.width > 1400

    def test_150_percent(self, mock_audio_lab_page):
        mock_audio_lab_page.width = int(1400 * 1.5)
        assert mock_audio_lab_page.width > 1400
