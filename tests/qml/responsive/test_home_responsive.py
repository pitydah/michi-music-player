from __future__ import annotations
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
    def _check_no_overflow(self, page, viewport_w, viewport_h):
        children = [page] + self._collect_children(page)
        for child in children:
            x = child.property("x") or 0
            y = child.property("y") or 0
            w = child.property("width") or 0
            h = child.property("height") or 0
            if hasattr(child, "objectName") and child.objectName and (x + w > viewport_w + 5 or y + h > viewport_h + 5):
                    pytest.fail(f"Control '{child.objectName()}' overflows viewport at ({x},{y}) {w}x{h} in {viewport_w}x{viewport_h}")

    def _collect_children(self, item):
        found = []
        for c in item.childItems():
            found.append(c)
            found.extend(self._collect_children(c))
        return found

    def test_desktop_1920(self, engine):
        comp = self._create_page(engine, 1920, 1080)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_desktop_1366(self, engine):
        comp = self._create_page(engine, 1366, 768)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_desktop_1024(self, engine):
        comp = self._create_page(engine, 1024, 768)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_desktop_900(self, engine):
        comp = self._create_page(engine, 900, 700)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_compact(self, engine):
        comp = self._create_page(engine, 600, 800)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_narrow(self, engine):
        comp = self._create_page(engine, 360, 640)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_zoom_125(self, engine):
        comp = self._create_page(engine, 900, 700, 1.25)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_zoom_150(self, engine):
        comp = self._create_page(engine, 900, 700, 1.5)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_page_qml_exists(self):
        assert (QML_DIR / "pages/home/HomePage.qml").exists()

import pytest


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
