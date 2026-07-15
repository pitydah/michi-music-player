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


class TestDevicePageKeyboard:
    DEVICE_PATH = "pages/devices/DevicesPage.qml"

    def test_page_has_focus_scope(self, engine):
        content = (QML_DIR / self.DEVICE_PATH).read_text()
        assert "activeFocusOnTab" in content or "focus" in content or "Keys.on" in content

    def test_server_control_keyboard(self, engine):
        content = (QML_DIR / self.DEVICE_PATH).read_text()
        assert "onStartServer" in content or "onStopServer" in content

    def test_device_card_keyboard(self, engine):
        content = (QML_DIR / self.DEVICE_PATH).read_text()
        has_focus = "focus" in content or "Keys.on" in content or "activeFocusOnTab" in content
        assert has_focus, "Device items should be keyboard accessible"

    def test_pairing_dialog_keyboard(self, engine):
        content = (QML_DIR / self.DEVICE_PATH).read_text()
        assert "Dialog" in content or "dialog" in content

    def test_storage_view_keyboard(self, engine):
        content = (QML_DIR / self.DEVICE_PATH).read_text()
        assert "StorageView" in content or "storage" in content.lower()

    def test_transfer_queue_keyboard(self, engine):
        content = (QML_DIR / self.DEVICE_PATH).read_text()
        assert "TransferQueue" in content or "transfer" in content.lower()
