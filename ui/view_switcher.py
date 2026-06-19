"""Segmented view switcher — capsule-style view selector for Astra."""

from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QWidget, QPushButton, QHBoxLayout

_GRADIENT = ("background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
             "stop:0 #FF7A00, stop:1 #DD007A);")
_BG = "rgba(255,255,255,0.08)"
_BORDER = "1px solid rgba(255,255,255,0.08)"
_COLOR = "rgba(255,255,255,0.6)"


class SegmentedViewSwitcher(QWidget):
    view_changed = Signal(str)

    def __init__(self, get_icon_func, parent=None):
        super().__init__(parent)
        self.setObjectName("segmentedViewSwitcher")
        self._current = "list"

        self._btn_grid = QPushButton(QIcon(get_icon_func("warm_view_grid")), "")
        self._btn_list = QPushButton(QIcon(get_icon_func("warm_view_list")), "")
        self._btn_cf = QPushButton(QIcon(get_icon_func("warm_view_coverflow")), "")

        self._buttons = {
            "grid": self._btn_grid,
            "list": self._btn_list,
            "coverflow": self._btn_cf,
        }

        for key, btn in self._buttons.items():
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedSize(46, 32)
            btn.setIconSize(QSize(20, 20))
            btn.clicked.connect(
                lambda checked=False, mode=key: self.set_view(mode))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(0)
        layout.addWidget(self._btn_grid)
        layout.addWidget(self._btn_list)
        layout.addWidget(self._btn_cf)

        self.setFixedHeight(38)
        self.setStyleSheet(f"""
            QWidget#segmentedViewSwitcher {{
                background: rgba(255,255,255,0.06);
                border: {_BORDER};
                border-radius: 12px;
            }}
        """)
        self._refresh_styles()

    def _refresh_styles(self):
        for i, (key, btn) in enumerate(self._buttons.items()):
            active = (key == self._current)
            grad = _GRADIENT if active else ""
            color = "#ffffff" if active else _COLOR
            hover = f"QPushButton:hover {{ background: {_BG}; }}"

            if i == 0:  # first
                radius = "border-radius: 10px 0 0 10px;"
                sep = f"border-right: {_BORDER};"
            elif i == 2:  # last
                radius = "border-radius: 0 10px 10px 0;"
                sep = ""
            else:  # middle
                radius = "border-radius: 0;"
                sep = f"border-right: {_BORDER};"

            btn.setStyleSheet(f"""
                QPushButton {{
                    padding: 0; border: none;
                    color: {color}; background: transparent;
                    {radius}
                }}
                QPushButton {{
                    {sep}
                }}
                {hover}
            """)
            if active:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        padding: 0; border: none;
                        color: #ffffff;
                        {grad}
                        {radius}
                    }}
                """)

    def set_view(self, mode: str, emit: bool = True):
        if mode not in self._buttons:
            return
        self._current = mode
        for key, btn in self._buttons.items():
            btn.setChecked(key == mode)
        self._refresh_styles()
        if emit:
            self.view_changed.emit(mode)

    @property
    def current_view(self) -> str:
        return self._current
