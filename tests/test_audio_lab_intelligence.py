"""Tests for IntelligencePage — requires pytest-qt."""

import pytest
from unittest.mock import patch

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap


def _pix():
    pix = QPixmap(1, 1)
    pix.fill(Qt.transparent)
    return pix


@pytest.mark.skip(reason="IntelligencePage not implemented yet")
def test_intelligence_no_bpm_as_energy():
    """Confirm _show_energy does NOT use BPM as energy."""
    with open("ui/audio_lab/intelligence_page.py") as f:
        source = f.read()
    energy_def = ""
    in_func = False
    for line in source.split("\n"):
        if "def _show_energy" in line:
            in_func = True
        if in_func:
            energy_def += line + "\n"
            if "def _" in line and "def _show_energy" not in line:
                break
    if "getattr(i, 'bpm'" in energy_def:
        assert False, "_show_energy uses bpm as energy — this is incorrect"
    if "getattr(i, 'energy'" not in energy_def:
        assert False, "_show_energy does not look for energy field"


@pytest.mark.skip(reason="IntelligencePage not implemented yet")
@patch("ui.audio_lab.intelligence_page.get_pixmap")
def test_intelligence_page_renders(mock_pixmap, qtbot):
    from ui.audio_lab.intelligence_page import IntelligencePage
    mock_pixmap.return_value = _pix()
    page = IntelligencePage(db=None)
    qtbot.addWidget(page)
    page.show()
    assert page.isVisible()


@pytest.mark.skip(reason="IntelligencePage not implemented yet")
@patch("ui.audio_lab.intelligence_page.get_pixmap")
def test_intelligence_no_crash_without_db(mock_pixmap, qtbot):
    from ui.audio_lab.intelligence_page import IntelligencePage
    mock_pixmap.return_value = _pix()
    page = IntelligencePage(db=None)
    qtbot.addWidget(page)
    page._show_bpm()
    page._show_energy()
    page._show_key()
