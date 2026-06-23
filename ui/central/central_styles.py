"""Central area QSS styles — dark glass premium, single visual system."""

from ui.central.central_tokens import (
    SURFACE_GLASS, SURFACE_GLASS_HOVER, BORDER_SUBTLE, ACCENT_BLUE, ACCENT_FAINT, ACCENT_SURFACE, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DISABLED,
)

# ── Legacy aliases (for existing code that references old names) ──
_GLASS_BG = SURFACE_GLASS
_GLASS_BORDER = BORDER_SUBTLE
_GLASS_HOVER = SURFACE_GLASS_HOVER
_GLASS_ACTIVE = ACCENT_SURFACE
_ACCENT = ACCENT_BLUE
_ACCENT_BORDER = ACCENT_FAINT
_TEXT_PRIMARY = TEXT_PRIMARY
_TEXT_SECONDARY = TEXT_SECONDARY
_TEXT_MUTED = TEXT_DISABLED


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
                stop:0 rgba(255,255,255,0.06),
                stop:0.48 rgba(255,255,255,0.04),
                stop:1 rgba(255,255,255,0.025)
            );
            border: 1px solid rgba(255,255,255,0.04);
            border-radius: 18px;
        }
    """


def section_icon_box_qss() -> str:
    return """
        QFrame#sectionIconBox {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.05);
            border-radius: 13px;
        }
    """


def section_title_qss() -> str:
    return """
        QLabel#sectionTitle {
            font-size: 19px;
            font-weight: 700;
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
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 13px;
            padding: 5px 32px 5px 12px;
            color: rgba(255,255,255,0.94);
            font-size: 13px;
            selection-background-color: rgba(143,183,255,0.30);
        }
        QLineEdit:focus {
            background: rgba(255,255,255,0.11);
            border: 1px solid rgba(143,183,255,0.28);
        }
    """


def count_badge_qss() -> str:
    return """
        QLabel#countBadge {
            font-size: 11px;
            color: rgba(255,255,255,0.62);
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.04);
            border-radius: 9px;
            padding: 4px 12px;
            qproperty-alignment: AlignCenter;
        }
    """


def tool_button_qss(kind: str = "default") -> str:
    base = """
        QToolButton {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.05);
            border-radius: 10px;
            padding: 5px 14px;
            color: rgba(255,255,255,0.82);
            font-size: 12px;
            font-weight: 500;
        }
        QToolButton:hover {
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.08);
            color: rgba(255,255,255,0.96);
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
            border: 1px solid rgba(255,255,255,0.06);
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
            background: rgba(143,183,255,0.16);
            color: rgba(255,255,255,1.00);
        }
    """


def table_header_qss() -> str:
    return """
        QHeaderView {
            background: #10131A;
            border: none;
        }
        QHeaderView::section {
            background: qlineargradient(
                x1:0, y1:0, x2:0, y2:1,
                stop:0 #181C25,
                stop:1 #10131A
            );
            color: rgba(255,255,255,0.86);
            font-size: 12px;
            font-weight: 600;
            padding: 7px 10px;
            border: none;
        }
        QHeaderView::section:hover {
            background: rgba(143,183,255,0.14);
            color: rgba(255,255,255,0.96);
        }
        QHeaderView::section:checked {
            background: rgba(143,183,255,0.20);
            color: rgba(255,255,255,1.00);
        }
        QTableCornerButton::section {
            background: #10131A;
            border: none;
        }
    """


def table_qss() -> str:
    return """
        QTableView {
            background: transparent;
            alternate-background-color: rgba(255,255,255,0.020);
            border: none;
            gridline-color: transparent;
            selection-background-color: rgba(143,183,255,0.14);
            selection-color: rgba(255,255,255,1.00);
            color: rgba(255,255,255,0.85);
            font-size: 13.5px;
        }
        QTableView::item {
            padding: 7px 14px;
            border: none;
        }
        QTableView::item:hover {
            background: rgba(255,255,255,0.035);
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
            background: rgba(255,255,255,0.10);
            min-height: 32px;
            border-radius: 2px;
        }
        QScrollBar::handle:vertical:hover {
            background: rgba(255,255,255,0.20);
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
            background: rgba(255,255,255,0.10);
            min-width: 32px;
            border-radius: 2px;
        }
        QScrollBar::handle:horizontal:hover {
            background: rgba(255,255,255,0.20);
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
            font-weight: 700;
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
            background: rgba(143,183,255,0.16);
            border: 1px solid rgba(143,183,255,0.18);
            border-radius: 10px;
            padding: 8px 20px;
            color: rgba(255,255,255,0.96);
            font-size: 13px;
            font-weight: 600;
        }
        QPushButton:hover {
            background: rgba(143,183,255,0.24);
            border: 1px solid rgba(143,183,255,0.28);
        }
        QPushButton:pressed {
            background: rgba(143,183,255,0.32);
        }
    """


def secondary_action_button_qss() -> str:
    return """
        QPushButton {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.04);
            border-radius: 10px;
            padding: 8px 20px;
            color: rgba(255,255,255,0.74);
            font-size: 13px;
            font-weight: 500;
        }
        QPushButton:hover {
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.07);
            color: rgba(255,255,255,0.90);
        }
    """


# ── Reusable premium glass styles ──

def glass_card_qss(name: str) -> str:
    """Premium glass card with soft border. Use with QFrame#{name}."""
    return f"""
        QFrame#{name} {{
            background: rgba(255,255,255,0.030);
            border: 1px solid rgba(255,255,255,0.025);
            border-radius: 18px;
        }}
        QFrame#{name}:hover {{
            background: rgba(255,255,255,0.048);
            border: 1px solid rgba(143,183,255,0.10);
        }}
        QFrame#{name} QLabel {{
            background: transparent;
            border: none;
        }}
    """


def glass_chip_qss() -> str:
    """Soft pill/chip badge — no hard borders."""
    return """
        QLabel {
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.025);
            border-radius: 9px;
            padding: 3px 8px;
            font-size: 10px;
            color: rgba(255,255,255,0.62);
        }
    """


def clean_table_header_qss() -> str:
    """Table header without vertical separators."""
    return """
        QHeaderView {
            background: #10131A;
            border: none;
        }
        QHeaderView::section {
            background: rgba(255,255,255,0.030);
            color: rgba(255,255,255,0.78);
            font-size: 12px;
            font-weight: 600;
            padding: 6px 8px;
            border: none;
        }
        QHeaderView::section:hover {
            background: rgba(143,183,255,0.12);
        }
        QTableCornerButton::section {
            background: #10131A;
            border: none;
        }
    """


def clean_table_qss() -> str:
    """Premium table with no visible gridlines."""
    return """
        QTableWidget {
            background: transparent;
            border: none;
            gridline-color: transparent;
            selection-background-color: rgba(143,183,255,0.14);
            selection-color: rgba(255,255,255,1.00);
            color: rgba(255,255,255,0.78);
        }
        QTableWidget::item {
            padding: 5px 8px;
            border: none;
        }
        QTableWidget::item:hover {
            background: rgba(255,255,255,0.035);
        }
    """


def glass_button_qss(kind: str = "secondary") -> str:
    """Unified glass button: primary | secondary | ghost."""
    if kind == "primary":
        return """
            QPushButton {
                background: rgba(143,183,255,0.16);
                border: 1px solid rgba(143,183,255,0.18);
                border-radius: 12px;
                padding: 8px 18px;
                color: rgba(255,255,255,0.96);
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: rgba(143,183,255,0.24);
                border: 1px solid rgba(143,183,255,0.28);
            }
        """
    elif kind == "ghost":
        return """
            QPushButton {
                background: transparent;
                border: 1px solid rgba(255,255,255,0.04);
                border-radius: 10px;
                padding: 6px 12px;
                color: rgba(255,255,255,0.52);
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.08);
                color: rgba(255,255,255,0.78);
            }
        """
    else:  # secondary
        return """
            QPushButton {
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.04);
                border-radius: 12px;
                padding: 8px 18px;
                color: rgba(255,255,255,0.78);
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.08);
                border: 1px solid rgba(255,255,255,0.07);
                color: rgba(255,255,255,0.92);
            }
        """


def transparent_scrollbar_qss() -> str:
    """Thin, minimal scrollbar — clean glass aesthetic."""
    return """
        QScrollBar:vertical {
            width: 4px;
            background: transparent;
            border: none;
            margin: 0;
        }
        QScrollBar::handle:vertical {
            background: rgba(255,255,255,0.08);
            min-height: 30px;
            border-radius: 2px;
        }
        QScrollBar::handle:vertical:hover {
            background: rgba(255,255,255,0.16);
        }
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {
            height: 0;
        }
    """
