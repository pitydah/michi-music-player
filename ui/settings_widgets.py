"""Premium settings widgets — reusable cards, rows, toggles, pickers for preferences UI."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QCheckBox, QComboBox, QSlider, QLineEdit, QFileDialog,
)
from PySide6.QtGui import QPixmap

_BG = "#090B11"
_PANEL = "rgba(255,255,255,0.035)"
_PANEL_ALT = "rgba(255,255,255,0.055)"
_HOVER = "rgba(255,255,255,0.075)"
_SELECTED = "rgba(255,255,255,0.115)"
_BORDER = "rgba(255,255,255,0.075)"
_TEXT = "#FFFFFF"
_TEXT2 = "rgba(255,255,255,0.78)"
_TEXT3 = "rgba(255,255,255,0.62)"
_TEXT_DIM = "rgba(255,255,255,0.34)"


class SettingsCard(QFrame):
    """Group of related settings with a title and optional subtitle."""

    def __init__(self, title: str = "", subtitle: str = "", parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background: {_PANEL};
                border: 1px solid {_BORDER};
                border-radius: 18px;
            }}
        """)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(18, 16, 18, 16)
        self._layout.setSpacing(4)

        if title:
            t = QLabel(title)
            t.setStyleSheet(f"color: {_TEXT}; font-size: 14px; font-weight: 700; background: transparent;")
            self._layout.addWidget(t)
        if subtitle:
            s = QLabel(subtitle)
            s.setWordWrap(True)
            s.setStyleSheet(f"color: {_TEXT3}; font-size: 11px; background: transparent;")
            self._layout.addWidget(s)

        if title or subtitle:
            self._layout.addSpacing(8)

        self._rows = QVBoxLayout()
        self._rows.setSpacing(2)
        self._layout.addLayout(self._rows)

    def add_row(self, widget):
        self._rows.addWidget(widget)

    def add_stretch(self):
        self._layout.addStretch()


class SettingsRow(QFrame):
    """Label + description on left, control on right."""

    def __init__(self, title: str, description: str = "", control: QWidget = None, parent=None):
        super().__init__(parent)
        self.setStyleSheet("QFrame { background: transparent; border: none; }")
        self.setMinimumHeight(48)

        h = QHBoxLayout(self)
        h.setContentsMargins(4, 6, 4, 6)
        h.setSpacing(12)

        left = QVBoxLayout()
        left.setSpacing(1)
        t = QLabel(title)
        t.setStyleSheet(f"color: {_TEXT2}; font-size: 12px; font-weight: 560; background: transparent;")
        left.addWidget(t)
        if description:
            d = QLabel(description)
            d.setWordWrap(True)
            d.setStyleSheet(f"color: {_TEXT3}; font-size: 10.5px; background: transparent;")
            left.addWidget(d)
        h.addLayout(left)
        h.addStretch()

        self._control = control
        if control:
            h.addWidget(control)

    @property
    def control(self):
        return self._control


class SettingsSwitch(QCheckBox):
    """Styled toggle switch."""

    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        self.setChecked(checked)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(40, 22)
        self.setStyleSheet("""
            QCheckBox {
                background: rgba(255,255,255,0.10); border: 1px solid rgba(255,255,255,0.12);
                border-radius: 11px; padding: 0;
            }
            QCheckBox::indicator {
                width: 16px; height: 16px; border-radius: 8px;
                background: rgba(255,255,255,0.40);
                margin: 2px;
            }
            QCheckBox:checked {
                background: rgba(255,255,255,0.18); border: 1px solid rgba(255,255,255,0.20);
            }
            QCheckBox:checked::indicator {
                background: #FFFFFF; margin-left: 20px;
            }
        """)


class SettingsCombo(QComboBox):
    """Styled combobox for settings."""

    def __init__(self, items: list[str] = None, current: str = "", parent=None):
        super().__init__(parent)
        if items:
            self.addItems(items)
        if current and current in (items or []):
            self.setCurrentText(current)
        self.setMinimumWidth(140)
        self.setStyleSheet(f"""
            QComboBox {{
                background: rgba(255,255,255,0.06); color: {_TEXT};
                border: 1px solid rgba(255,255,255,0.10); border-radius: 8px;
                padding: 6px 10px; font-size: 11.5px;
            }}
            QComboBox:hover {{ border-color: rgba(255,255,255,0.15); }}
            QComboBox QAbstractItemView {{
                background: rgba(22,24,31,0.97); color: {_TEXT};
                border: 1px solid rgba(255,255,255,0.10); selection-background-color: rgba(255,255,255,0.10);
            }}
        """)


class SettingsSlider(QWidget):
    """Slider with value label."""

    valueChanged = Signal(int)

    def __init__(self, min_val: int = 0, max_val: int = 100, value: int = 50,
                 suffix: str = "", parent=None):
        super().__init__(parent)
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)

        self._slider = QSlider(Qt.Horizontal)
        self._slider.setRange(min_val, max_val)
        self._slider.setValue(value)
        self._slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{ height: 4px; background: rgba(255,255,255,0.10); border-radius: 2px; }}
            QSlider::handle:horizontal {{
                width: 12px; height: 12px; margin: -5px 0; border-radius: 6px;
                background: {_TEXT};
            }}
            QSlider::sub-page:horizontal {{ background: rgba(255,255,255,0.20); border-radius: 2px; }}
        """)
        self._slider.valueChanged.connect(lambda v: self._update_label())
        h.addWidget(self._slider, 1)

        self._suffix = suffix
        self._label = QLabel(f"{value}{suffix}")
        self._label.setFixedWidth(55)
        self._label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._label.setStyleSheet(f"color: {_TEXT2}; font-size: 11px; background: transparent;")
        h.addWidget(self._label)

    def _update_label(self):
        self._label.setText(f"{self._slider.value()}{self._suffix}")
        self.valueChanged.emit(self._slider.value())

    def value(self):
        return self._slider.value()

    def setValue(self, v):
        self._slider.setValue(v)


class SettingsPathPicker(QFrame):
    """Line edit + browse button for folder/file paths."""

    def __init__(self, path: str = "", parent=None):
        super().__init__(parent)
        self.setStyleSheet("QFrame { background: transparent; border: none; }")
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)

        self._edit = QLineEdit(path)
        self._edit.setStyleSheet(f"""
            QLineEdit {{
                background: rgba(255,255,255,0.06); color: {_TEXT};
                border: 1px solid rgba(255,255,255,0.10); border-radius: 8px;
                padding: 6px 10px; font-size: 11.5px;
            }}
        """)
        h.addWidget(self._edit, 1)

        btn = QPushButton("...")
        btn.setFixedSize(32, 30)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255,255,255,0.06); color: {_TEXT2};
                border: 1px solid rgba(255,255,255,0.10); border-radius: 8px;
                font-size: 12px; font-weight: 700;
            }}
            QPushButton:hover {{ background: rgba(255,255,255,0.10); color: {_TEXT}; }}
        """)
        btn.clicked.connect(self._browse)
        h.addWidget(btn)

    def _browse(self):
        path = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta")
        if path:
            self._edit.setText(path)

    def text(self):
        return self._edit.text()

    def setText(self, v):
        self._edit.setText(v)


class SettingsActionButton(QPushButton):
    """Styled action button for settings."""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(34)
        self.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255,255,255,0.06); color: {_TEXT2};
                border: 1px solid rgba(255,255,255,0.095); border-radius: 10px;
                padding: 7px 14px; font-size: 12px; font-weight: 600;
            }}
            QPushButton:hover {{
                background: rgba(255,255,255,0.095); color: {_TEXT};
                border: 1px solid rgba(255,255,255,0.14);
            }}
        """)


class SettingsPageHeader(QWidget):
    """Page header with icon, title, subtitle."""

    def __init__(self, title: str, subtitle: str = "", icon_name: str = "", parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 12)
        h.setSpacing(12)

        from ui.icons import get_icon
        if icon_name:
            path = get_icon(icon_name)
            if path:
                pix = QPixmap(path)
                if not pix.isNull():
                    icon_lbl = QLabel()
                    icon_lbl.setPixmap(pix.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    icon_lbl.setFixedSize(32, 32)
                    icon_lbl.setStyleSheet("background: transparent;")
                    h.addWidget(icon_lbl)

        v = QVBoxLayout()
        v.setSpacing(2)
        t = QLabel(title)
        t.setStyleSheet(f"color: {_TEXT}; font-size: 20px; font-weight: 800; background: transparent;")
        v.addWidget(t)
        if subtitle:
            s = QLabel(subtitle)
            s.setWordWrap(True)
            s.setStyleSheet(f"color: {_TEXT3}; font-size: 11.5px; background: transparent;")
            v.addWidget(s)
        h.addLayout(v)
        h.addStretch()
