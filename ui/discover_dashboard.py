"""Discover Dashboard — large cards for Mix, NoReproducidos, Favoritos, Recientes."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QScrollArea, QFrame,
)

from ui.icons import get_icon


class DiscoverDashboard(QWidget):
    navigate_requested = Signal(str)  # sidebar key

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: #090B11;")

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.NoFrame)
        self._scroll.setStyleSheet(
            "QScrollArea { background: #090B11; border: none; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(20)

        # Title
        title = QLabel("Descubrir")
        title.setStyleSheet(
            "font-size: 22px; font-weight: 750; color: rgba(255,255,255,0.94);"
            "background: transparent;")
        layout.addWidget(title)

        subtitle = QLabel("Explora, descubre y redescubre tu música")
        subtitle.setStyleSheet(
            "font-size: 13px; color: rgba(255,255,255,0.48);"
            "background: transparent;")
        layout.addWidget(subtitle)
        layout.addSpacing(8)

        # Cards grid
        grid = QGridLayout()
        grid.setSpacing(16)

        cards = [
            ("mix_daily", "Mix diario", "Reproducido en los últimos 7 días",
             "qlineargradient(x1:0, y1:0, x2:1, y2:1, "
             "stop:0 rgba(255,122,0,0.15), stop:1 rgba(232,0,109,0.10))",
             "sidebar_mix"),
            ("mix_unplayed", "No escuchadas", "Canciones que aún no has reproducido",
             "qlineargradient(x1:0, y1:0, x2:1, y2:1, "
             "stop:0 rgba(255,255,255,0.08), stop:1 rgba(255,255,255,0.04))",
             "sidebar_unplayed"),
            ("mix_popular", "Más escuchadas", "Tus canciones con más reproducciones",
             "qlineargradient(x1:0, y1:0, x2:1, y2:1, "
             "stop:0 rgba(255,122,0,0.10), stop:1 rgba(232,0,109,0.08))",
             "sidebar_popular"),
            ("favs", "Favoritos", "Canciones que has marcado como favoritas",
             "qlineargradient(x1:0, y1:0, x2:1, y2:1, "
             "stop:0 rgba(232,0,109,0.12), stop:1 rgba(255,122,0,0.06))",
             "sidebar_popular"),
            ("recent", "Recientes", "Reproducidas recientemente",
             "qlineargradient(x1:0, y1:0, x2:1, y2:1, "
             "stop:0 rgba(255,255,255,0.06), stop:1 rgba(255,255,255,0.03))",
             "sidebar_recent"),
        ]

        for i, (key, name, desc, bg, icon_name) in enumerate(cards):
            card = _DiscoverCard(name, desc, bg, icon_name)
            card.clicked.connect(lambda k=key: self.navigate_requested.emit(k))
            row = i // 2
            col = i % 2
            grid.addWidget(card, row, col)

        layout.addLayout(grid)
        layout.addStretch()

        self._scroll.setWidget(container)

        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.addWidget(self._scroll)


class _DiscoverCard(QFrame):
    clicked = Signal()

    def __init__(self, title: str, desc: str, bg: str, icon_name: str):
        super().__init__()
        self.setMinimumHeight(140)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            QFrame {{
                background: {bg};
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 16px;
            }}
            QFrame:hover {{
                border: 1px solid rgba(255,122,0,0.25);
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Icon
        icon_lbl = QLabel()
        path = get_icon(icon_name)
        if path:
            from PySide6.QtGui import QPixmap
            pix = QPixmap(path)
            if not pix.isNull():
                icon_lbl.setPixmap(pix.scaled(48, 48, Qt.KeepAspectRatio,
                                             Qt.SmoothTransformation))
        icon_lbl.setFixedSize(56, 56)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet(
            "QLabel { background: rgba(255,255,255,0.06); border-radius: 14px; }")
        layout.addWidget(icon_lbl)

        # Text
        text_col = QVBoxLayout()
        text_col.setSpacing(4)
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            "font-size: 16px; font-weight: 650; color: rgba(255,255,255,0.92);"
            "background: transparent;")
        text_col.addWidget(title_lbl)

        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet(
            "font-size: 12px; color: rgba(255,255,255,0.50);"
            "background: transparent;")
        desc_lbl.setWordWrap(True)
        text_col.addWidget(desc_lbl)
        layout.addLayout(text_col, 1)

        layout.addStretch()

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)
