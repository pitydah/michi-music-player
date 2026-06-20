"""Segmented view switcher — unified capsule control with QButtonGroup."""

from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QWidget, QPushButton, QHBoxLayout, QButtonGroup

from ui.design_tokens import (VIEW_BUTTON_W, VIEW_BUTTON_H,
    VIEW_ICON_W, VIEW_ICON_H)


class SegmentedViewSwitcher(QWidget):
    view_changed = Signal(str)

    def __init__(self, get_icon_func, parent=None):
        super().__init__(parent)
        self.setObjectName("segmentedViewSwitcher")
        self.setFixedHeight(38)
        self.setFixedWidth(132)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        self._buttons = {
            "grid": QPushButton(QIcon(get_icon_func("warm_view_grid")), ""),
            "list": QPushButton(QIcon(get_icon_func("warm_view_list")), ""),
            "coverflow": QPushButton(QIcon(get_icon_func("warm_view_coverflow")), ""),
        }

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)

        for mode, btn in self._buttons.items():
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFocusPolicy(Qt.NoFocus)
            btn.setFlat(True)
            btn.setFixedSize(VIEW_BUTTON_W, VIEW_BUTTON_H)
            btn.setMinimumSize(VIEW_BUTTON_W, VIEW_BUTTON_H)
            btn.setMaximumSize(VIEW_BUTTON_W, VIEW_BUTTON_H)
            btn.setIconSize(QSize(VIEW_ICON_W, VIEW_ICON_H))
            self._group.addButton(btn)
            layout.addWidget(btn)

        self.set_view("list", emit=False)

        self.setStyleSheet(f"""
            QWidget#segmentedViewSwitcher {{
                background: rgba(255,255,255,0.04);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 12px;
            }}
            QWidget#segmentedViewSwitcher QPushButton {{
                background: transparent;
                border: none;
                margin: 0;
                padding: 0;
                min-width: 42px;
                max-width: 42px;
                min-height: 34px;
                max-height: 34px;
                border-radius: 8px;
            }}
            QWidget#segmentedViewSwitcher QPushButton:hover {{
                background: rgba(255,255,255,0.06);
            }}
            QWidget#segmentedViewSwitcher QPushButton:checked {{
                background: rgba(255,255,255,0.10);
                border: none;
                margin: 0;
                padding: 0;
            }}
        """)

        for mode, btn in self._buttons.items():
            btn.clicked.connect(lambda checked=False, m=mode: self.set_view(m))

    def set_view(self, mode: str, emit: bool = True):
        if mode not in self._buttons:
            return
        self._current = mode
        self._buttons[mode].setChecked(True)
        if emit:
            self.view_changed.emit(mode)

    @property
    def current_view(self) -> str:
        return self._current

    def set_available_modes(self, modes: list[str]):
        for mode_name, btn in self._buttons.items():
            btn.setVisible(mode_name in modes)
        if self._current not in modes and modes:
            self.set_view(modes[0], emit=False)
