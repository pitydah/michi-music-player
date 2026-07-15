"""CoverFlow — stub for QML migration. Real CoverFlow is in QML."""
from __future__ import annotations

from PySide6.QtWidgets import QWidget


class CoverFlowWidget(QWidget):
    def __init__(self, parent=None, db=None, player_service=None):
        super().__init__(parent)

    def set_album_keys(self, keys):
        pass

    def refresh(self):
        pass
