"""QSS helpers — premium glass, cards, buttons, scrollbars for Michi."""
from ui.style_tokens import COLORS, RADIUS


def glass_panel(radius: int = 18, level: int = 1) -> str:
    """Background panel with subtle glass effect."""
    surface = COLORS.get(f"surface_{level}", COLORS["surface_1"])
    return (
        f"background: {surface};"
        f"border: 1px solid {COLORS['border']};"
        f"border-radius: {radius}px;"
    )


def glass_card(radius: int = 20) -> str:
    """Premium card with hover state."""
    return (
        f"background: {COLORS['surface_1']};"
        f"border: 1px solid {COLORS['border']};"
        f"border-radius: {radius}px;"
        f"QLabel {{ background: transparent; }}"
    )


def premium_button(kind: str = "default") -> str:
    """Button QSS variants: default, primary, ghost."""
    base = "font-size: 12px; font-weight: 600; border-radius: 12px; padding: 8px 16px;"
    if kind == "primary":
        return (
            f"QPushButton {{ {base}"
            f"  color: #FFFFFF;"
            f"  background: rgba(70,145,255,0.22);"
            f"  border: 1px solid rgba(90,165,255,0.42); }}"
            f"QPushButton:hover {{ background: rgba(90,165,255,0.32);"
            f"  border: 1px solid rgba(120,190,255,0.56); }}"
            f"QPushButton:pressed {{ background: rgba(50,120,255,0.16); }}")
    elif kind == "ghost":
        return (
            f"QPushButton {{ {base}"
            f"  color: {COLORS['text_muted']};"
            f"  background: transparent;"
            f"  border: 1px solid rgba(255,255,255,0.07); }}"
            f"QPushButton:hover {{ color: {COLORS['text_primary']};"
            f"  background: rgba(255,255,255,0.05);"
            f"  border: 1px solid rgba(255,255,255,0.12); }}")
    else:  # default
        return (
            f"QPushButton {{ {base}"
            f"  color: {COLORS['text_secondary']};"
            f"  background: rgba(255,255,255,0.06);"
            f"  border: 1px solid rgba(255,255,255,0.09); }}"
            f"QPushButton:hover {{ color: {COLORS['text_primary']};"
            f"  background: rgba(255,255,255,0.10);"
            f"  border: 1px solid rgba(255,255,255,0.15); }}")


def premium_menu_qss() -> str:
    """Dark glass context menu."""
    return (
        f"QMenu {{"
        f"  background: rgba(18,20,28,0.98);"
        f"  color: {COLORS['text_secondary']};"
        f"  border: 1px solid rgba(255,255,255,0.105);"
        f"  border-radius: {RADIUS['md']}px;"
        f"  padding: 6px 4px; }}"
        f"QMenu::item {{ padding: 7px 28px 7px 14px;"
        f"  border-radius: 8px; font-size: 12.5px; }}"
        f"QMenu::item:selected {{ background: rgba(255,255,255,0.095);"
        f"  color: {COLORS['text_primary']}; }}"
        f"QMenu::separator {{ height: 1px;"
        f"  background: rgba(255,255,255,0.08); margin: 4px 8px; }}")


def section_header_qss() -> str:
    """Sidebar section header uppercase style."""
    return (
        "font-size: 11px; font-weight: 700;"
        "color: rgba(255,255,255,0.42);"
        "background: transparent; border: none;")


def search_field_qss() -> str:
    """Premium search field."""
    return (
        f"QLineEdit {{"
        f"  background: rgba(255,255,255,0.075);"
        f"  border: 1px solid rgba(255,255,255,0.095);"
        f"  border-radius: 15px;"
        f"  padding: 7px 32px 7px 14px;"
        f"  color: {COLORS['text_primary']};"
        f"  font-size: 13px; }}"
        f"QLineEdit:focus {{"
        f"  background: rgba(255,255,255,0.11);"
        f"  border: 1px solid rgba(122,167,255,0.32); }}")


def scroll_bar_qss() -> str:
    """Minimal scrollbar."""
    return (
        "QScrollBar:vertical { width: 3px; background: transparent; }"
        "QScrollBar::handle:vertical {"
        "  background: rgba(255,255,255,0.14);"
        "  min-height: 36px; border-radius: 2px; }"
        "QScrollBar::handle:vertical:hover {"
        "  background: rgba(255,255,255,0.24); }"
        "QScrollBar::add-line:vertical,"
        "QScrollBar::sub-line:vertical { height: 0; }")
