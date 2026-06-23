"""SidebarItem — glass dark navigation item with accent bar."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy

from ui.icon_loader import get_sidebar_icon
from ui.sidebar.sidebar_tokens import (
    SIDEBAR_ICON_SIZE, SIDEBAR_ITEM_HEIGHT, SIDEBAR_ACCENT_WIDTH, SIDEBAR_ITEM_SPACING,
)
from ui.sidebar.sidebar_styles import (
    item_qss, item_label_qss, badge_qss, accent_qss, icon_label_qss,
)


class SidebarItem(QFrame):
    clicked = Signal(str)

    def __init__(self, text: str, key: str, icon: str = "",
                 badge: str = "", dark: bool = True):
        super().__init__()
        self._key = key
        self._dark = dark
        self._active = False
        self._hovered = False
        self._icon_name = icon
        self._badge_label = None

        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(SIDEBAR_ITEM_HEIGHT)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(SIDEBAR_ITEM_SPACING)

        # Accent bar — hidden unless active
        self._accent = QFrame()
        self._accent.setFixedWidth(0)
        self._accent.setVisible(False)
        self._accent.setStyleSheet(accent_qss(False))
        layout.addWidget(self._accent)

        # Icon
        self._icon_label = QLabel()
        self._icon_label.setFixedSize(SIDEBAR_ICON_SIZE, SIDEBAR_ICON_SIZE)
        self._icon_label.setScaledContents(False)
        self._icon_label.setAlignment(Qt.AlignCenter)
        self._icon_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._icon_label.setStyleSheet(icon_label_qss())
        self._icon_label.setAttribute(Qt.WA_TranslucentBackground, True)
        self._icon_label.setAutoFillBackground(False)
        self._load_icon()
        layout.addWidget(self._icon_label)

        # Text
        self._label = QLabel(text)
        self._label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self._label.setStyleSheet(item_label_qss("normal"))
        layout.addWidget(self._label)
        layout.addStretch()

        # Badge
        if badge:
            self._badge_label = QLabel(badge)
            self._badge_label.setStyleSheet(badge_qss("normal"))
            layout.addWidget(self._badge_label)

        self._apply_state("normal")

    def _load_icon(self):
        name = self._icon_name
        if name:
            pix = get_sidebar_icon(name, active=self._active,
                                   hover=self._hovered,
                                   size=SIDEBAR_ICON_SIZE)
        else:
            pix = QPixmap(SIDEBAR_ICON_SIZE, SIDEBAR_ICON_SIZE)
            pix.fill(Qt.transparent)
        self._icon_label.setPixmap(pix)

    def _apply_state(self, state: str):
        self.setStyleSheet(item_qss(state))
        self._label.setStyleSheet(item_label_qss(state))
        self._accent.setFixedWidth(SIDEBAR_ACCENT_WIDTH)
        self._accent.setVisible(state == "active")
        self._accent.setStyleSheet(accent_qss(state == "active"))
        if self._badge_label:
            self._badge_label.setStyleSheet(badge_qss(state))
        self.setMinimumHeight(SIDEBAR_ITEM_HEIGHT)

    def set_active(self, active: bool):
        self._active = active
        self._apply_state("active" if active else "normal")
        self._load_icon()

    def enterEvent(self, event):
        self._hovered = True
        if not self._active:
            self._apply_state("hover")
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        if not self._active:
            self._apply_state("normal")
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._key)
        super().mousePressEvent(event)

    @property
    def key(self) -> str:
        return self._key

    def text(self) -> str:
        return self._label.text()
