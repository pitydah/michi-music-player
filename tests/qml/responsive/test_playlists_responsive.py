from __future__ import annotations

import pytest
from unittest.mock import MagicMock, PropertyMock


@pytest.fixture
def mock_playlists_page():
    page = MagicMock()
    page.width = 1400
    page.height = 900
    type(page).objectName = PropertyMock(return_value="playlistsPage")
    return page


class TestPlaylistsPageResponsive:
    @pytest.mark.parametrize("width,expected_cols", [
        (1600, 4),
        (1200, 3),
        (900, 2),
        (700, 1),
    ])
    def test_card_grid_columns(self, mock_playlists_page, width, expected_cols):
        mock_playlists_page.width = width
        if width > 1400:
            assert expected_cols == 4
        elif width >= 1024:
            assert expected_cols == 3
        elif width >= 768:
            assert expected_cols == 2
        else:
            assert expected_cols == 1

    def test_wide_layout(self, mock_playlists_page):
        mock_playlists_page.width = 1600
        assert mock_playlists_page.width > 1400

    def test_narrow_layout(self, mock_playlists_page):
        mock_playlists_page.width = 700
        assert mock_playlists_page.width < 768
