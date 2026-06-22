"""SidebarBrand — app icon + name card at top of sidebar."""
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel

from ui.sidebar.sidebar_styles import brand_card_qss


class SidebarBrand(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(brand_card_qss())

        inner = QHBoxLayout(self)
        inner.setContentsMargins(10, 8, 10, 8)
        inner.setSpacing(10)

        app_icon_label = QLabel()
        app_icon_path = str(Path(__file__).parent.parent.parent / "icons" / "app_icon.png")
        pix = QPixmap(app_icon_path)
        if not pix.isNull():
            app_icon_label.setPixmap(
                pix.scaled(34, 34, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            app_icon_label.setFixedSize(34, 34)
        app_icon_label.setStyleSheet("background:transparent;border:none;")
        inner.addWidget(app_icon_label)

        text_col = QVBoxLayout()
        text_col.setSpacing(0)
        title = QLabel("MICHI")
        title.setStyleSheet(
            "font-size:16px;font-weight:bold;color:rgba(255,255,255,0.96);"
            "background:transparent;border:none;")
        sub = QLabel("Music Player")
        sub.setStyleSheet(
            "font-size:11px;color:rgba(245,245,247,0.66);"
            "background:transparent;border:none;")
        text_col.addWidget(title)
        text_col.addWidget(sub)
        inner.addLayout(text_col)
        inner.addStretch()
