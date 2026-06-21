"""Central area QSS styles — dark glass premium, no orange/neon."""


def content_surface_qss() -> str:
    return """
        QWidget#contentSurface {
            background: #090B11;
            border: none;
        }
    """


def stack_qss() -> str:
    return """
        QStackedWidget {
            background: transparent;
            border: none;
        }
    """


def header_qss() -> str:
    return """
        QFrame#headerBar {
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba(255,255,255,0.070),
                stop:0.48 rgba(255,255,255,0.045),
                stop:1 rgba(255,255,255,0.030)
            );
            border: 1px solid rgba(255,255,255,0.080);
            border-radius: 18px;
        }
    """


def section_icon_box_qss() -> str:
    return """
        QFrame#sectionIconBox {
            background: rgba(255,255,255,0.060);
            border: 1px solid rgba(255,255,255,0.090);
            border-radius: 13px;
        }
    """


def section_title_qss() -> str:
    return """
        QLabel#sectionTitle {
            font-size: 19px;
            font-weight: bold;
            color: rgba(255,255,255,0.96);
            background: transparent;
            border: none;
        }
    """


def section_subtitle_qss() -> str:
    return """
        QLabel#sectionSubtitle {
            font-size: 12px;
            color: rgba(255,255,255,0.62);
            background: transparent;
            border: none;
        }
    """


def search_qss() -> str:
    return """
        QLineEdit {
            background: rgba(255,255,255,0.10);
            border: 1px solid rgba(255,255,255,0.13);
            border-radius: 13px;
            padding: 5px 32px 5px 12px;
            color: rgba(255,255,255,0.94);
            font-size: 13px;
            selection-background-color: rgba(143,183,255,0.30);
        }
        QLineEdit:focus {
            background: rgba(255,255,255,0.14);
            border: 1px solid rgba(143,183,255,0.34);
        }
    """


def count_badge_qss() -> str:
    return """
        QLabel#countBadge {
            font-size: 11px;
            color: rgba(255,255,255,0.62);
            background: rgba(255,255,255,0.055);
            border: 1px solid rgba(255,255,255,0.075);
            border-radius: 9px;
            padding: 4px 12px;
            qproperty-alignment: AlignCenter;
        }
    """


def tool_button_qss(kind: str = "default") -> str:
    base = """
        QToolButton {
            background: rgba(255,255,255,0.065);
            border: 1px solid rgba(255,255,255,0.085);
            border-radius: 10px;
            padding: 5px 14px;
            color: rgba(255,255,255,0.82);
            font-size: 12px;
            font-weight: 500;
        }
        QToolButton:hover {
            background: rgba(255,255,255,0.105);
            border: 1px solid rgba(255,255,255,0.14);
            color: rgba(255,255,255,0.96);
        }
        QToolButton:pressed {
            background: rgba(255,255,255,0.135);
        }
    """
    if kind == "icon":
        return base + """
            QToolButton {
                border-radius: 12px;
                padding: 6px;
            }
        """
    return base


def menu_qss() -> str:
    return """
        QMenu {
            background: rgba(20,22,28,0.96);
            border: 1px solid rgba(255,255,255,0.09);
            border-radius: 14px;
            padding: 6px;
            color: rgba(255,255,255,0.88);
        }
        QMenu::item {
            padding: 6px 28px 6px 14px;
            border-radius: 8px;
            margin: 2px 4px;
        }
        QMenu::item:selected {
            background: rgba(143,183,255,0.18);
            color: rgba(255,255,255,1.00);
        }
    """


def table_qss() -> str:
    return """
        QTableView {
            background: transparent;
            alternate-background-color: rgba(255,255,255,0.022);
            border: none;
            gridline-color: rgba(255,255,255,0.04);
            selection-background-color: rgba(143,183,255,0.16);
            selection-color: rgba(255,255,255,1.00);
            color: rgba(255,255,255,0.85);
            font-size: 13px;
        }
        QTableView::item {
            padding: 6px 10px;
            border: none;
        }
        QTableView::item:hover {
            background: rgba(255,255,255,0.045);
        }
        QHeaderView::section {
            background: rgba(255,255,255,0.04);
            border: none;
            border-bottom: 1px solid rgba(255,255,255,0.06);
            padding: 7px 10px;
            color: rgba(255,255,255,0.62);
            font-size: 11px;
            font-weight: 600;
        }
    """


def scrollbar_qss() -> str:
    return """
        QScrollBar:vertical {
            width: 3px;
            background: transparent;
            border: none;
            margin: 0;
        }
        QScrollBar::handle:vertical {
            background: rgba(255,255,255,0.12);
            min-height: 32px;
            border-radius: 2px;
        }
        QScrollBar::handle:vertical:hover {
            background: rgba(255,255,255,0.24);
        }
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {
            height: 0;
        }
        QScrollBar:horizontal {
            height: 3px;
            background: transparent;
            border: none;
        }
        QScrollBar::handle:horizontal {
            background: rgba(255,255,255,0.12);
            min-width: 32px;
            border-radius: 2px;
        }
        QScrollBar::handle:horizontal:hover {
            background: rgba(255,255,255,0.24);
        }
        QScrollBar::add-line:horizontal,
        QScrollBar::sub-line:horizontal {
            width: 0;
        }
    """


def empty_state_qss() -> str:
    return """
        QFrame#emptyState {
            background: transparent;
            border: none;
        }
        QLabel#emptyIcon {
            font-size: 48px;
            color: rgba(255,255,255,0.24);
            background: transparent;
            border: none;
        }
        QLabel#emptyTitle {
            font-size: 17px;
            font-weight: 640;
            color: rgba(255,255,255,0.72);
            background: transparent;
            border: none;
        }
        QLabel#emptySubtitle {
            font-size: 13px;
            color: rgba(255,255,255,0.42);
            background: transparent;
            border: none;
        }
    """


def primary_action_button_qss() -> str:
    return """
        QPushButton {
            background: rgba(143,183,255,0.18);
            border: 1px solid rgba(143,183,255,0.30);
            border-radius: 10px;
            padding: 8px 20px;
            color: rgba(255,255,255,0.96);
            font-size: 13px;
            font-weight: 600;
        }
        QPushButton:hover {
            background: rgba(143,183,255,0.28);
            border: 1px solid rgba(143,183,255,0.44);
        }
        QPushButton:pressed {
            background: rgba(143,183,255,0.36);
        }
    """


def secondary_action_button_qss() -> str:
    return """
        QPushButton {
            background: rgba(255,255,255,0.055);
            border: 1px solid rgba(255,255,255,0.09);
            border-radius: 10px;
            padding: 8px 20px;
            color: rgba(255,255,255,0.74);
            font-size: 13px;
            font-weight: 540;
        }
        QPushButton:hover {
            background: rgba(255,255,255,0.09);
            border: 1px solid rgba(255,255,255,0.15);
            color: rgba(255,255,255,0.90);
        }
    """
