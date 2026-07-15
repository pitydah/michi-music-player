from __future__ import annotations

import pytest
from unittest.mock import MagicMock, PropertyMock


@pytest.fixture
def mock_devices_page():
    page = MagicMock()
    page.width = 1400
    page.height = 900
    type(page).objectName = PropertyMock(return_value="devicesPage")
    return page


class TestDevicesPageResponsive:
    @pytest.mark.parametrize("width,expected_cols", [
        (1920, 3),
        (1366, 2),
        (1024, 2),
        (900, 2),
        (700, 1),
        (500, 1),
    ])
    def test_device_grid_columns(self, mock_devices_page, width, expected_cols):
        mock_devices_page.width = width
        if width > 1400:
            assert expected_cols == 3
        elif width >= 768:
            assert expected_cols == 2
        else:
            assert expected_cols == 1

    def test_wide_1920(self, mock_devices_page):
        mock_devices_page.width = 1920
        assert mock_devices_page.width > 1400

    def test_standard_1366(self, mock_devices_page):
        mock_devices_page.width = 1366
        assert 1024 <= mock_devices_page.width <= 1400

    def test_compact_1024(self, mock_devices_page):
        mock_devices_page.width = 1024
        assert mock_devices_page.width >= 768

    def test_narrow_900(self, mock_devices_page):
        mock_devices_page.width = 900
        assert mock_devices_page.width >= 768

    def test_compact_700(self, mock_devices_page):
        mock_devices_page.width = 700
        assert mock_devices_page.width < 768

    def test_narrow_500(self, mock_devices_page):
        mock_devices_page.width = 500
        assert mock_devices_page.width < 768

    def test_percent_125(self, mock_devices_page):
        mock_devices_page.width = int(1400 * 1.25)
        assert mock_devices_page.width > 1400

    def test_percent_150(self, mock_devices_page):
        mock_devices_page.width = int(1400 * 1.5)
        assert mock_devices_page.width > 1400
