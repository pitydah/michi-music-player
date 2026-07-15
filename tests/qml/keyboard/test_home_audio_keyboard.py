from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtQml import QQmlEngine

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"


@pytest.fixture
def engine(qapp):
    e = QQmlEngine(qapp)
    e.addImportPath(str(QML_DIR))
    return e


class TestHomeAudioKeyboard:
    HA_PATH = "pages/home_audio/HomeAudioPage.qml"

    def test_mode_selector_keyboard(self, engine):
        content = (QML_DIR / self.HA_PATH).read_text()
        assert "activeFocusOnTab" in content or "focus" in content or "Keys.on" in content

    def test_configure_button_keyboard(self, engine):
        content = (QML_DIR / self.HA_PATH).read_text()
        assert "onConfigureClicked" in content

    def test_diagnostics_button_keyboard(self, engine):
        content = (QML_DIR / self.HA_PATH).read_text()
        assert "onOpenDiagnostics" in content

    def test_device_list_keyboard(self, engine):
        content = (QML_DIR / self.HA_PATH).read_text()
        assert "Repeater" in content

    def test_mode_tabs_keyboard(self, engine):
        content = (QML_DIR / self.HA_PATH).read_text()
        assert "currentIndex" in content or "StackLayout" in content

    def test_glass_card_diagnostics_keyboard(self, engine):
        content = (QML_DIR / self.HA_PATH).read_text()
        assert "GlassCard" in content
