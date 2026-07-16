"""Design tokens — unified visual constants, theme-aware."""

from dataclasses import dataclass


@dataclass
class Tokens:
    accent_blue: str
    accent_pink: str
    accent_red: str
    bg_app: str
    bg_panel: str
    bg_panel_strong: str
    bg_card: str
    bg_card_hover: str
    border: str
    border_strong: str
    text: str
    text_muted: str
    text_faint: str


_TOKEN_MAP = {
    "dark": Tokens(
        accent_blue="#8FB7FF",
        accent_pink="rgba(143,183,255,0.60)",
        accent_red="#FF243D",
        bg_app="#0D0F16",
        bg_panel="rgba(28,30,40,0.82)",
        bg_panel_strong="rgba(20,22,30,0.90)",
        bg_card="rgba(255,255,255,0.055)",
        bg_card_hover="rgba(255,255,255,0.075)",
        border="rgba(255,255,255,0.08)",
        border_strong="rgba(255,255,255,0.13)",
        text="rgba(245,245,247,0.92)",
        text_muted="rgba(245,245,247,0.56)",
        text_faint="rgba(245,245,247,0.36)",
    ),
    "light": Tokens(
        accent_blue="#8FB7FF",
        accent_pink="#CC0066",
        accent_red="#CC1A2E",
        bg_app="#F5F5F7",
        bg_panel="rgba(255,255,255,0.85)",
        bg_panel_strong="rgba(255,255,255,0.95)",
        bg_card="rgba(0,0,0,0.04)",
        bg_card_hover="rgba(0,0,0,0.07)",
        border="rgba(0,0,0,0.08)",
        border_strong="rgba(0,0,0,0.13)",
        text="rgba(28,28,30,0.92)",
        text_muted="rgba(28,28,30,0.56)",
        text_faint="rgba(28,28,30,0.36)",
    ),
    "amoled": Tokens(
        accent_blue="#8FB7FF",
        accent_pink="rgba(143,183,255,0.60)",
        accent_red="#FF243D",
        bg_app="#000000",
        bg_panel="rgba(10,10,12,0.88)",
        bg_panel_strong="rgba(8,8,10,0.95)",
        bg_card="rgba(255,255,255,0.04)",
        bg_card_hover="rgba(255,255,255,0.06)",
        border="rgba(255,255,255,0.05)",
        border_strong="rgba(255,255,255,0.10)",
        text="rgba(245,245,247,0.92)",
        text_muted="rgba(245,245,247,0.52)",
        text_faint="rgba(245,245,247,0.30)",
    ),
}

_current_theme: str = "dark"


def get_tokens(theme: str | None = None) -> Tokens:
    """Return tokens for the given theme name, or current theme."""
    name = theme or _current_theme
    return _TOKEN_MAP.get(name, _TOKEN_MAP["dark"])


def set_theme(name: str):
    global _current_theme
    if name in _TOKEN_MAP:
        _current_theme = name


def current_theme() -> str:
    return _current_theme


# ── Backward-compatible module-level constants (dark theme) ──

_t = _TOKEN_MAP["dark"]

COLOR_ACCENT_ORANGE = _t.accent_blue
COLOR_ACCENT_PINK = _t.accent_pink
COLOR_ACCENT_RED = _t.accent_red

ACCENT_GRADIENT = ("qlineargradient(x1:0, y1:0, x2:1, y2:0,"
                   " stop:0 #8FB7FF, stop:1 rgba(143,183,255,0.60))")

COLOR_BG_APP = _t.bg_app
COLOR_BG_PANEL = _t.bg_panel
COLOR_BG_PANEL_STRONG = _t.bg_panel_strong
COLOR_BG_CARD = _t.bg_card
COLOR_BG_CARD_HOVER = _t.bg_card_hover
COLOR_BORDER = _t.border
COLOR_BORDER_STRONG = _t.border_strong

COLOR_TEXT = _t.text
COLOR_TEXT_MUTED = _t.text_muted
COLOR_TEXT_FAINT = _t.text_faint

# ── Radii ──

RADIUS_SM = 8
RADIUS_MD = 12
RADIUS_LG = 18

# ── Spacing (base unit: 4px) ──

SPACING_XS = 4
SPACING_SM = 8
SPACING_MD = 12
SPACING_LG = 16
SPACING_XL = 24
SPACING_XXL = 32

# ── Controls ──

CONTROL_SM = 32
CONTROL_MD = 38
CONTROL_PLAY = 48

# ── Icons ──

ICON_SM = 16
ICON_MD = 20
ICON_LG = 24

# ── View switcher ──

VIEW_BUTTON_W = 46
VIEW_BUTTON_H = 36
VIEW_ICON_W = 23
VIEW_ICON_H = 23

# ── Sidebar ──

SIDEBAR_ITEM_H = 40
SIDEBAR_ICON = 24
SIDEBAR_ACCENT_W = 3
SIDEBAR_W_MIN = 270
SIDEBAR_W_MAX = 380
SIDEBAR_ICON_OPACITY = 0.82
SIDEBAR_ICON_HOVER_OPACITY = 0.96
SIDEBAR_BG_TOP = "rgba(52,55,64,0.96)"
SIDEBAR_BG_BOTTOM = "rgba(38,41,50,0.96)"
SIDEBAR_SECTION_TEXT = "rgba(245,245,247,0.72)"
SIDEBAR_ITEM_TEXT = "rgba(245,245,247,0.86)"
SIDEBAR_ACTIVE_GRADIENT = (
    "qlineargradient(x1:0, y1:0, x2:1, y2:0,"
    " stop:0 rgba(143,183,255,0.70),"
    " stop:0.55 rgba(100,150,255,0.60),"
    " stop:1 rgba(80,130,255,0.50))")
