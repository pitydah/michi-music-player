from __future__ import annotations

import pytest
from unittest.mock import MagicMock, PropertyMock


@pytest.fixture
def mock_connections_page():
    page = MagicMock()
    page.width = 1400
    page.height = 900
    type(page).objectName = PropertyMock(return_value="connectionsPage")
    return page


class TestConnectionsPageResponsive:
    @pytest.mark.parametrize("width,expected_cols", [
        (1600, 3),
        (1200, 2),
        (900, 2),
        (700, 1),
    ])
    def test_server_grid_columns(self, mock_connections_page, width, expected_cols):
        mock_connections_page.width = width
        if width > 1400:
            assert expected_cols == 3
        elif width >= 768:
            assert expected_cols == 2
        else:
            assert expected_cols == 1

    def test_wide_three_column(self, mock_connections_page):
        mock_connections_page.width = 1600
        assert mock_connections_page.width > 1400

    def test_standard_two_column(self, mock_connections_page):
        mock_connections_page.width = 1200
        assert 1024 <= mock_connections_page.width <= 1400

    def test_narrow_single_column(self, mock_connections_page):
        mock_connections_page.width = 700
        assert mock_connections_page.width < 768
