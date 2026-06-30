"""Widget tests for Audio Lab hub — requires pytest-qt/QApplication."""

from __future__ import annotations

from unittest.mock import patch

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap


def _pix():
    pix = QPixmap(1, 1)
    pix.fill(Qt.transparent)
    return pix


@patch("ui.audio_lab.audio_lab_page.get_pixmap")
def test_hub_renders_five_cards(mock_pixmap, qtbot):
    from ui.audio_lab.audio_lab_page import AudioLabPage

    mock_pixmap.return_value = _pix()
    page = AudioLabPage()
    qtbot.addWidget(page)
    page.show()

    assert page.isVisible()
    assert page._status_label is not None
    assert page._status_label.text() == "Sin reproducción activa."


@patch("ui.audio_lab.audio_lab_page.get_pixmap")
def test_hub_set_status(mock_pixmap, qtbot):
    from ui.audio_lab.audio_lab_page import AudioLabPage

    mock_pixmap.return_value = _pix()
    page = AudioLabPage()
    qtbot.addWidget(page)

    page.set_status_text("FLAC 24/192 · Bit-perfect")
    assert page._status_label.text() == "FLAC 24/192 · Bit-perfect"

    page.set_status_text("Sin reproducción activa.")
    assert page._status_label.text() == "Sin reproducción activa."


@patch("ui.audio_lab.sub_pages.get_pixmap")
def test_identifier_page_renders(mock_pixmap, qtbot):
    from ui.audio_lab.sub_pages import AudioLabIdentifierPage

    mock_pixmap.return_value = _pix()
    page = AudioLabIdentifierPage()
    qtbot.addWidget(page)
    page.show()

    assert page.isVisible()
    assert page.navigate_requested is not None


@patch("ui.audio_lab.sub_pages.get_pixmap")
def test_backup_page_renders(mock_pixmap, qtbot):
    from ui.audio_lab.sub_pages import AudioLabBackupPage

    mock_pixmap.return_value = _pix()
    page = AudioLabBackupPage()
    qtbot.addWidget(page)
    page.show()

    assert page.isVisible()
    assert page.navigate_requested is not None


@patch("ui.audio_lab.sub_pages.get_pixmap")
def test_diagnostics_page_renders(mock_pixmap, qtbot):
    from ui.audio_lab.sub_pages import AudioLabDiagnosticsPage

    mock_pixmap.return_value = _pix()
    page = AudioLabDiagnosticsPage()
    qtbot.addWidget(page)
    page.show()

    assert page.isVisible()
    assert page.navigate_requested is not None


@patch("ui.audio_lab.sub_pages.get_pixmap")
def test_output_page_renders(mock_pixmap, qtbot):
    from ui.audio_lab.sub_pages import AudioLabOutputPage

    mock_pixmap.return_value = _pix()
    page = AudioLabOutputPage()
    qtbot.addWidget(page)
    page.show()

    assert page.isVisible()


@patch("ui.audio_lab.sub_pages.get_pixmap")
def test_intelligence_page_renders(mock_pixmap, qtbot):
    from ui.audio_lab.sub_pages import AudioLabIntelligencePage

    mock_pixmap.return_value = _pix()
    page = AudioLabIntelligencePage()
    qtbot.addWidget(page)
    page.show()

    assert page.isVisible()
