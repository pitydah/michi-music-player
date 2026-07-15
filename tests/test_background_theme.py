"""Tests for BackgroundThemeService V2 — QML-compatible, no QStackedWidget."""
from core.background_theme_service import BackgroundThemeService


def test_init(qtbot):
    svc = BackgroundThemeService()
    assert svc is not None


def test_reset(qtbot):
    svc = BackgroundThemeService()
    svc.reset()


def test_apply_null_pixmap(qtbot):
    svc = BackgroundThemeService()
    svc.apply(None)


def test_apply_pixmap(qtbot):
    from PySide6.QtGui import QPixmap
    svc = BackgroundThemeService()
    pix = QPixmap(100, 100)
    pix.fill(0)
    svc.apply(pix)


def test_extract_colors(qtbot):
    from PySide6.QtGui import QPixmap
    svc = BackgroundThemeService()
    pix = QPixmap(100, 100)
    pix.fill(0)
    c1, c2 = svc.extract_colors(pix)
    assert isinstance(c1, str)
    assert isinstance(c2, str)
    assert c1.startswith("#")
    assert c2.startswith("#")
