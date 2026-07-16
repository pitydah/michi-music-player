"""Plasma-native palette and modern QSS for Michi Music Player."""

from PySide6.QtGui import QPalette, QColor

from ui.central.central_tokens import (
    SURFACE_POPUP, BORDER_NORMAL, BORDER_FOCUS, BORDER_SEPARATOR,
    ACCENT_SURFACE, ACCENT_SELECTION,
    TEXT_NORMAL,
)


def is_dark_mode(palette: QPalette | None = None) -> bool:
    """Detect if the current system theme is dark."""
    if palette is None:
        from PySide6.QtWidgets import QApplication
        palette = QApplication.instance().palette()
    return palette.color(QPalette.Window).lightness() <= 128


def build_plasma_palette() -> QPalette:
    """Clean, modern QPalette — light mode."""
    p = QPalette()
    p.setColor(QPalette.Window,          QColor("#f5f5f7"))
    p.setColor(QPalette.WindowText,      QColor("#1c1c1e"))
    p.setColor(QPalette.Base,            QColor("#ffffff"))
    p.setColor(QPalette.AlternateBase,   QColor("#fafafa"))
    p.setColor(QPalette.Text,            QColor("#1c1c1e"))
    p.setColor(QPalette.Highlight,       QColor("#8FB7FF"))
    p.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    p.setColor(QPalette.Button,          QColor("#f5f5f7"))
    p.setColor(QPalette.ButtonText,      QColor("#1c1c1e"))
    p.setColor(QPalette.Light,           QColor("#ffffff"))
    p.setColor(QPalette.Midlight,        QColor("#e5e5ea"))
    p.setColor(QPalette.Mid,             QColor("#c7c7cc"))
    p.setColor(QPalette.Dark,            QColor("#8e8e93"))
    p.setColor(QPalette.Shadow,          QColor("#636366"))
    p.setColor(QPalette.ToolTipBase,     QColor("#f5f5f7"))
    p.setColor(QPalette.ToolTipText,     QColor("#1c1c1e"))
    p.setColor(QPalette.Link,            QColor("#8FB7FF"))
    p.setColor(QPalette.LinkVisited,     QColor("#8FB7FF"))
    p.setColor(QPalette.PlaceholderText, QColor("#8e8e93"))
    return p


PLASMA_QSS = """
QMainWindow { background: transparent; }

QTreeWidget {
    background: transparent; border: none; outline: none;
    padding: 4px 4px;
}
QTreeWidget::item {
    padding: 6px 10px; border-radius: 6px; margin: 1px 4px;
    font-size: 13px;
}
QTreeWidget::item:selected {
    background: rgba(143,183,255,0.25); color: #ffffff; font-weight: 600;
}
QTreeWidget::item:hover:!selected {
    background: rgba(143,183,255,0.06);
}
QTreeWidget::branch { background: transparent; }
    QTableView {
        background: transparent;
        border: none; outline: none;
        border-radius: 12px; gridline-color: transparent;
}
QTableView::item { padding: 6px 12px; border-bottom: none; color: rgba(255,255,255,0.85); }
QTableView::item:hover { background: """ + ACCENT_SURFACE + """; }
QTableView::item:selected { background: """ + ACCENT_SELECTION + """; color: #fff; }
QHeaderView::section {
    background: rgba(255,255,255,0.04); color: rgba(255,255,255,0.64); padding: 8px 12px;
    border: none; border-bottom: 1px solid rgba(255,255,255,0.06);
    font-size: 11px; font-weight: 600;
}
QHeaderView::section:hover { color: rgba(255,255,255,0.90); }

QSlider::groove:horizontal { height: 3px; background: rgba(255,255,255,0.1); border-radius: 2px; }
QSlider::handle:horizontal {
    width: 10px; height: 10px; margin: -4px 0; border-radius: 5px;
    background: #ffffff; border: 2px solid #8FB7FF;
}
QSlider::handle:horizontal:hover { background: #8FB7FF; }
QSlider::sub-page:horizontal { background: #8FB7FF; border-radius: 2px; }

QProgressBar {
    background: rgba(255,255,255,0.06); border: none; border-radius: 4px; height: 6px;
}
QProgressBar::chunk { background: #8FB7FF; border-radius: 3px; }

QLineEdit {
    background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.08);
    border-radius: 8px; padding: 6px 12px; color: rgba(255,255,255,0.85);
}
QLineEdit:focus { border-color: #8FB7FF; }

QComboBox {
    background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.08);
    border-radius: 8px; padding: 5px 10px; color: rgba(255,255,255,0.85); min-width: 80px;
}
QComboBox:hover { border-color: rgba(255,255,255,0.15); }
QComboBox QAbstractItemView {
    background: """ + SURFACE_POPUP + """; border: 1px solid """ + BORDER_NORMAL + """;
    border-radius: 8px; selection-background-color: """ + ACCENT_SELECTION + """;
    selection-color: #fff; outline: none;
}

QScrollBar:vertical { width: 6px; background: transparent; margin: 2px; }
QScrollBar::handle:vertical {
    background: rgba(255,255,255,0.1); border-radius: 3px; min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: rgba(255,255,255,0.2); }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { height: 6px; background: transparent; margin: 2px; }
QScrollBar::handle:horizontal {
    background: rgba(255,255,255,0.1); border-radius: 3px; min-width: 30px;
}
QScrollBar::handle:horizontal:hover { background: rgba(255,255,255,0.2); }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

QMenu {
    background: """ + SURFACE_POPUP + """; border: 1px solid """ + BORDER_NORMAL + """;
    border-radius: 10px; padding: 4px; color: """ + TEXT_NORMAL + """;
}
QMenu::item { padding: 6px 32px 6px 12px; border-radius: 6px; }
QMenu::item:selected { background: """ + BORDER_FOCUS + """; color: #fff; }
QMenu::separator {
    height: 1px; background: """ + BORDER_SEPARATOR + """; margin: 3px 8px;
}

QMenuBar {
    background: rgba(20,20,25,230); border-bottom: 1px solid rgba(255,255,255,0.04);
    padding: 2px 0; color: rgba(255,255,255,0.7);
}
QMenuBar::item {
    padding: 5px 10px; border-radius: 6px; margin: 1px 2px; color: rgba(255,255,255,0.7);
}
QMenuBar::item:selected {
    background: rgba(143,183,255,0.15); color: #8FB7FF;
}

/* ── Disabled-state protection: never go fully gray ── */
QWidget:disabled {
    color: rgba(255,255,255,0.66);
}
QLabel:disabled {
    color: rgba(255,255,255,0.66);
}
QPushButton:disabled {
    color: rgba(255,255,255,0.42);
    background: rgba(255,255,255,0.030);
    border: 1px solid rgba(255,255,255,0.045);
}
QTreeView:disabled, QTreeWidget:disabled {
    color: rgba(255,255,255,0.66);
    background: transparent;
}
QTableView:disabled {
    color: rgba(255,255,255,0.66);
    background: transparent;
}

QPushButton[flat=\"true\"] {
    border: none; background: transparent; border-radius: 6px;
}
QPushButton[flat=\"true\"]:hover { background: rgba(255,255,255,0.06); }
QPushButton[flat=\"true\"]:pressed { background: rgba(255,255,255,0.1); }

QToolTip {
    background: """ + SURFACE_POPUP + """; color: """ + TEXT_NORMAL + """;
    border: 1px solid rgba(255,255,255,0.08);     border-radius: 6px; padding: 4px 8px;
}
QComboBox QAbstractItemView {
    background: """ + SURFACE_POPUP + """; border: 1px solid """ + BORDER_NORMAL + """;
    border-radius: 8px; selection-background-color: """ + ACCENT_SELECTION + """;
    color: """ + TEXT_NORMAL + """; outline: none;
}

QDialog { background: """ + SURFACE_POPUP + """; }
"""


def apply_dialog_shadow(widget, radius=20, offset=3, opacity=50):
    """Apply subtle drop shadow to a dialog or widget."""
    from PySide6.QtWidgets import QGraphicsDropShadowEffect
    from PySide6.QtGui import QColor
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(radius)
    shadow.setXOffset(0)
    shadow.setYOffset(offset)
    shadow.setColor(QColor(0, 0, 0, opacity))
    widget.setGraphicsEffect(shadow)
    return shadow
