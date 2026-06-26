"""Central area QSS styles — dark glass premium, single visual system."""

from ui.central.central_tokens import (
    SURFACE_GLASS, SURFACE_GLASS_HOVER, SURFACE_POPUP, SURFACE_INPUT,
    BORDER_SUBTLE, BORDER_FOCUS, ACCENT_BLUE, ACCENT_FAINT, ACCENT_SURFACE, ACCENT_SELECTION,
    TEXT_PRIMARY, TEXT_NORMAL, TEXT_SECONDARY, TEXT_DISABLED,
    BADGE_LOCAL_BG, BADGE_LOCAL_TEXT, BADGE_REMOTE_BG, BADGE_REMOTE_TEXT,
    BADGE_ACTIVE_BG, BADGE_ACTIVE_TEXT,
    BADGE_DISCONNECTED_BG, BADGE_DISCONNECTED_TEXT,
    BADGE_ERROR_BG, BADGE_ERROR_TEXT,
    BADGE_EXPERIMENTAL_BG, BADGE_EXPERIMENTAL_TEXT,
    SURFACE_CARD, SURFACE_CARD_HOVER, SURFACE_CARD_ELEVATED,
    SURFACE_CARD_ACCENT, BORDER_CARD, BORDER_CARD_ACCENT, BORDER_CARD_ELEVATED,
    STATUS_INFO_BG, STATUS_INFO_TEXT,
    STATUS_WARNING_BG, STATUS_WARNING_TEXT,
    STATUS_SUCCESS_BG, STATUS_SUCCESS_TEXT,
    STATUS_ERROR_BG, STATUS_ERROR_TEXT,
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
            border: 1px solid rgba(255,255,255,0.035);
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
            border: 1px solid rgba(255,255,255,0.06);
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
            border: 1px solid rgba(255,255,255,0.05);
            color: rgba(255,255,255,0.90);
        }
    """


# ── Reusable premium glass styles ──

def glass_card_qss(name: str, variant: str = "base") -> str:
    """Premium glass card. variant: base | elevated | accent."""
    if variant == "elevated":
        bg = SURFACE_CARD_ELEVATED
        bd = BORDER_CARD_ELEVATED
    elif variant == "accent":
        bg = SURFACE_CARD_ACCENT
        bd = BORDER_CARD_ACCENT
    else:
        bg = SURFACE_CARD
        bd = BORDER_CARD

    return f"""
        QFrame#{name} {{
            background: {bg};
            border: 1px solid {bd};
            border-radius: 18px;
        }}
        QFrame#{name}:hover {{
            background: {SURFACE_CARD_HOVER};
            border: 1px solid {BORDER_CARD_ACCENT};
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
    """Unified glass button: primary | secondary | ghost | accent | danger | disabled."""
    qss_map = {
        "primary": """
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
        """,
        "accent": """
            QPushButton {
                background: rgba(143,183,255,0.10);
                border: 1px solid rgba(143,183,255,0.14);
                border-radius: 12px;
                padding: 8px 18px;
                color: rgba(143,183,255,0.90);
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: rgba(143,183,255,0.18);
                border: 1px solid rgba(143,183,255,0.24);
            }
        """,
        "danger": """
            QPushButton {
                background: rgba(255,100,100,0.10);
                border: 1px solid rgba(255,100,100,0.14);
                border-radius: 12px;
                padding: 8px 18px;
                color: rgba(255,100,100,0.85);
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: rgba(255,100,100,0.18);
                border: 1px solid rgba(255,100,100,0.24);
            }
        """,
        "disabled": """
            QPushButton {
                background: rgba(255,255,255,0.03);
                border: 1px solid rgba(255,255,255,0.025);
                border-radius: 12px;
                padding: 8px 18px;
                color: rgba(255,255,255,0.32);
                font-size: 12px;
                font-weight: 500;
            }
        """,
        "ghost": """
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
                border: 1px solid rgba(255,255,255,0.06);
                color: rgba(255,255,255,0.78);
            }
        """,
    }
    if kind in qss_map:
        return qss_map[kind]
    # secondary (default)
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
            border: 1px solid rgba(255,255,255,0.05);
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


def skeleton_qss(name: str) -> str:
    """Glass skeleton loading card. Use with QFrame#{name}."""
    return f"""
        QFrame#{name} {{
            background: rgba(255,255,255,0.025);
            border: 1px solid rgba(255,255,255,0.02);
            border-radius: 12px;
        }}
    """


def tooltip_qss() -> str:
    """Global tooltip with glass popup styling."""
    return f"""
        QToolTip {{
            background: {SURFACE_POPUP};
            border: 1px solid rgba(143,183,255,0.12);
            border-radius: 8px;
            padding: 6px 10px;
            color: {TEXT_NORMAL};
            font-size: 11px;
        }}
    """


def badge_qss(kind: str) -> str:
    """Reusable badge chip. Kind: local|remote|active|disconnected|error|experimental|success|warning."""
    badges = {
        "local":        (BADGE_LOCAL_BG, BADGE_LOCAL_TEXT),
        "remote":       (BADGE_REMOTE_BG, BADGE_REMOTE_TEXT),
        "active":       (BADGE_ACTIVE_BG, BADGE_ACTIVE_TEXT),
        "disconnected": (BADGE_DISCONNECTED_BG, BADGE_DISCONNECTED_TEXT),
        "error":        (BADGE_ERROR_BG, BADGE_ERROR_TEXT),
        "experimental": (BADGE_EXPERIMENTAL_BG, BADGE_EXPERIMENTAL_TEXT),
        "success":      (STATUS_SUCCESS_BG, STATUS_SUCCESS_TEXT),
        "warning":      (STATUS_WARNING_BG, STATUS_WARNING_TEXT),
        "info":         (STATUS_INFO_BG, STATUS_INFO_TEXT),
    }
    bg, text = badges.get(kind, ("rgba(255,255,255,0.04)", "rgba(255,255,255,0.54)"))
    return f"""
        QLabel {{
            background: {bg};
            border: 1px solid transparent;
            border-radius: 8px;
            padding: 3px 10px;
            color: {text};
            font-size: 10px;
            font-weight: 500;
        }}
    """


def dialog_qss() -> str:
    """Unified glass dialog style."""
    return f"""
        QDialog {{
            background: {SURFACE_POPUP};
            border: 1px solid rgba(143,183,255,0.12);
            border-radius: 18px;
        }}
        QDialog QLabel {{
            background: transparent;
            border: none;
        }}
    """


def combo_dropdown_qss() -> str:
    """Unified QComboBox dropdown style — same as menus."""
    return f"""
        QComboBox QAbstractItemView {{
            background: {SURFACE_POPUP};
            border: 1px solid {BORDER_SUBTLE};
            border-radius: 8px;
            selection-background-color: {ACCENT_SELECTION};
            color: {TEXT_NORMAL};
            outline: none;
        }}
    """


def tab_bar_qss() -> str:
    """Unified premium tab bar styling — dark glass, accent selected."""
    return f"""
        QTabWidget::pane {{
            border: none;
            background: transparent;
        }}
        QTabBar::tab {{
            background: rgba(255,255,255,0.02);
            border: 1px solid {BORDER_CARD};
            border-radius: 8px;
            padding: 8px 20px;
            color: {TEXT_SECONDARY};
            font-size: 13px;
            margin-right: 4px;
        }}
        QTabBar::tab:hover {{
            color: {TEXT_NORMAL};
        }}
        QTabBar::tab:selected {{
            background: {ACCENT_SELECTION};
            border: 1px solid {BORDER_FOCUS};
            color: {TEXT_PRIMARY};
        }}
    """


def card_title_qss() -> str:
    """Card title — 16px, semibold, premium."""
    return (
        "QLabel { color: rgba(255,255,255,0.88); font-size: 16px; "
        "font-weight: 600; background: transparent; border: none; }"
    )


def card_desc_qss() -> str:
    """Card description — 12px, medium weight, muted."""
    return (
        "QLabel { color: rgba(255,255,255,0.56); font-size: 12px; "
        "font-weight: 500; background: transparent; border: none; }"
    )


def section_label_qss() -> str:
    """Section label — 11px, muted, for category headers in cards."""
    return (
        "QLabel { color: rgba(255,255,255,0.48); font-size: 11px; "
        "font-weight: 600; background: transparent; border: none; }"
    )


def glass_progress_qss() -> str:
    """Glass progress bar — accent chunk on dark glass track."""
    return f"""
        QProgressBar {{
            background: rgba(255,255,255,0.04);
            border: 1px solid {BORDER_CARD};
            border-radius: 8px;
            height: 8px;
            text-align: center;
            color: transparent;
        }}
        QProgressBar::chunk {{
            background: {ACCENT_SELECTION};
            border-radius: 6px;
        }}
    """


def glass_chip_button_qss() -> str:
    """Chip button — compact glass pill for tags/devices."""
    return (
        "QPushButton {"
        "  background: rgba(255,255,255,0.04);"
        "  border: 1px solid rgba(255,255,255,0.03);"
        "  border-radius: 9px;"
        "  padding: 4px 10px;"
        "  color: rgba(255,255,255,0.62);"
        "  font-size: 10px;"
        "}"
    "QPushButton:hover {"
    "  background: rgba(143,183,255,0.08);"
    "  border: 1px solid rgba(143,183,255,0.12);"
    "}"
)


# ── Page-level helpers ──

def page_title_qss() -> str:
    """Page title — 22px bold, high contrast."""
    return (
        "QLabel { color: rgba(255,255,255,0.92); font-size: 22px; "
        "font-weight: 700; background: transparent; border: none; }"
    )


def page_subtitle_qss() -> str:
    """Page subtitle — 13px, muted."""
    return (
        "QLabel { color: rgba(255,255,255,0.56); font-size: 13px; "
        "font-weight: 400; background: transparent; border: none; }"
    )


def card_meta_qss() -> str:
    """Card metadata — 11px, dim."""
    return (
        "QLabel { color: rgba(255,255,255,0.44); font-size: 11px; "
        "font-weight: 400; background: transparent; border: none; }"
    )


def muted_label_qss() -> str:
    """Secondary label — 12px, muted."""
    return (
        "QLabel { color: rgba(255,255,255,0.48); font-size: 12px; "
        "font-weight: 400; background: transparent; border: none; }"
    )


def field_input_qss() -> str:
    """Form input field — dark glass with accent focus."""
    return f"""
        QLineEdit, QSpinBox {{
            background: {SURFACE_INPUT};
            border: 1px solid {BORDER_CARD};
            border-radius: 8px;
            padding: 6px 10px;
            color: {TEXT_NORMAL};
            font-size: 12px;
        }}
        QLineEdit:focus, QSpinBox:focus {{
            border: 1px solid {BORDER_FOCUS};
        }}
    """


def status_card_qss(status: str) -> str:
    """Status-tinted card variant. status: info|warning|success|error."""
    colors = {
        "info": (STATUS_INFO_BG, STATUS_INFO_TEXT),
        "warning": (STATUS_WARNING_BG, STATUS_WARNING_TEXT),
        "success": (STATUS_SUCCESS_BG, STATUS_SUCCESS_TEXT),
        "error": (STATUS_ERROR_BG, STATUS_ERROR_TEXT),
    }
    bg, text = colors.get(status, (SURFACE_CARD, TEXT_SECONDARY))
    return f"""
        QFrame {{
            background: {bg};
            border: 1px solid rgba(255,255,255,0.03);
            border-radius: 12px;
        }}
        QFrame QLabel {{
            background: transparent;
            border: none;
            color: {text};
        }}
    """


def grid_card_qss(name: str, active: bool = False) -> str:
    """Compact card for album/artist/genre grids."""
    border = ACCENT_SELECTION if active else BORDER_CARD
    bg = SURFACE_CARD_ACCENT if active else SURFACE_CARD
    return f"""
        QFrame#{name} {{
            background: {bg};
            border: 1px solid {border};
            border-radius: 14px;
        }}
        QFrame#{name}:hover {{
            background: {SURFACE_CARD_HOVER};
            border: 1px solid {BORDER_CARD_ACCENT};
        }}
        QFrame#{name} QLabel {{
            background: transparent;
            border: none;
        }}
    """


def icon_slot_qss(name: str) -> str:
    """Square slot for icons — no text, just a centered icon container."""
    return f"""
        QLabel#{name} {{
            background: rgba(143,183,255,0.06);
            border: 1px solid rgba(143,183,255,0.06);
            border-radius: 12px;
            color: rgba(255,255,255,0.52);
        }}
    """
