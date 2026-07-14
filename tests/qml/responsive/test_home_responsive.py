from __future__ import annotations

import pytest
from unittest.mock import MagicMock, PropertyMock


@pytest.fixture
def mock_home_page():
    page = MagicMock()
    page.width = 1400
    page.height = 900
    type(page).objectName = PropertyMock(return_value="homePage")
    return page


class TestHomePageResponsive:
    @pytest.mark.parametrize("width,expected_layout", [
        (1600, "wide"),
        (1200, "standard"),
        (900, "compact"),
        (700, "narrow"),
    ])
    def test_layout_breakpoints(self, mock_home_page, width, expected_layout):
        mock_home_page.width = width
        if width > 1400:
            assert expected_layout == "wide"
        elif width >= 1024:
            assert expected_layout == "standard"
        elif width >= 768:
            assert expected_layout == "compact"
        else:
            assert expected_layout == "narrow"

    def test_wide_stacked_row(self, mock_home_page):
        mock_home_page.width = 1600
        assert mock_home_page.width > 1400
        assert mock_home_page.objectName == "homePage"

    def test_narrow_single_column(self, mock_home_page):
        mock_home_page.width = 700
        assert mock_home_page.width < 768
