"""Central area design tokens — dark glass premium, single source of truth."""

# ── Backgrounds ──
BG_APP                 = "#070A10"
BG_CONTENT             = "#090B11"
SURFACE_GLASS          = "rgba(255,255,255,0.040)"
SURFACE_GLASS_HOVER    = "rgba(255,255,255,0.060)"
SURFACE_POPUP          = "rgba(13,16,24,0.985)"
SURFACE_SECTION        = "rgba(255,255,255,0.035)"
SURFACE_INPUT          = "rgba(255,255,255,0.055)"

# ── Borders ──
BORDER_SUBTLE          = "rgba(255,255,255,0.035)"
BORDER_FOCUS           = "rgba(143,183,255,0.22)"
BORDER_NORMAL          = "rgba(255,255,255,0.06)"
BORDER_POPUP           = "rgba(143,183,255,0.12)"
BORDER_DIALOG          = "rgba(143,183,255,0.10)"

GLASS_EDGE             = "rgba(255,255,255,0.035)"
GLASS_EDGE_FOCUS       = "rgba(143,183,255,0.28)"
GLASS_INPUT_DEPTH      = "qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 rgba(0,0,0,0.12), stop:0.05 rgba(0,0,0,0.02), stop:1 rgba(255,255,255,0.03))"

# ── Text ──
TEXT_PRIMARY           = "rgba(255,255,255,0.95)"
TEXT_NORMAL            = "rgba(255,255,255,0.86)"
TEXT_SECONDARY         = "rgba(255,255,255,0.68)"
TEXT_MUTED             = "rgba(255,255,255,0.54)"
TEXT_DISABLED          = "rgba(255,255,255,0.42)"
TEXT_META              = "rgba(255,255,255,0.44)"
TEXT_PAGE_TITLE        = "rgba(255,255,255,0.92)"
TEXT_PAGE_SUBTITLE     = "rgba(255,255,255,0.56)"

# ── Accent ──
ACCENT_BLUE            = "#8FB7FF"
ACCENT_FAINT           = "rgba(143,183,255,0.34)"
ACCENT_SURFACE         = "rgba(143,183,255,0.08)"
ACCENT_SELECTION       = "rgba(143,183,255,0.14)"

# ── Badge colors ──
BADGE_LOCAL_BG         = "rgba(143,183,255,0.10)"
BADGE_LOCAL_TEXT       = "rgba(143,183,255,0.60)"
BADGE_REMOTE_BG        = "rgba(200,180,100,0.10)"
BADGE_REMOTE_TEXT      = "rgba(200,180,100,0.60)"
BADGE_ACTIVE_BG        = "rgba(100,220,140,0.10)"
BADGE_ACTIVE_TEXT      = "rgba(100,220,140,0.60)"
BADGE_DISCONNECTED_BG  = "rgba(255,255,255,0.06)"
BADGE_DISCONNECTED_TEXT = "rgba(255,255,255,0.42)"
BADGE_ERROR_BG         = "rgba(255,100,100,0.08)"
BADGE_ERROR_TEXT       = "rgba(255,100,100,0.55)"
BADGE_EXPERIMENTAL_BG  = "rgba(180,150,255,0.08)"
BADGE_EXPERIMENTAL_TEXT = "rgba(180,150,255,0.55)"

# ── Radii ──
RADIUS_LG              = 24
RADIUS_MD              = 16
RADIUS_SM              = 12
RADIUS_XS              = 8

# ── Sizing ──
CONTROL_H              = 36
SEARCH_W               = 240

# ── Card surfaces (semantic) ──
SURFACE_CARD            = "rgba(255,255,255,0.040)"
SURFACE_CARD_HOVER      = "rgba(255,255,255,0.060)"
SURFACE_CARD_ELEVATED   = "qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 rgba(255,255,255,0.060), stop:0.7 rgba(255,255,255,0.040), stop:1 rgba(143,183,255,0.035))"
SURFACE_CARD_ACCENT     = "rgba(143,183,255,0.04)"
SURFACE_CARD_COMPACT    = "rgba(255,255,255,0.030)"
SURFACE_CARD_ELEVATED_STRONG = "qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 rgba(255,255,255,0.070), stop:0.6 rgba(255,255,255,0.045), stop:1 rgba(143,183,255,0.040))"
SURFACE_HERO            = "qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 rgba(255,255,255,0.065), stop:0.5 rgba(143,183,255,0.035), stop:1 rgba(255,255,255,0.025))"
SURFACE_FLOATING        = "rgba(16,18,26,0.96)"
SURFACE_CONTROL         = "rgba(255,255,255,0.045)"
SURFACE_CONTROL_HOVER   = "rgba(255,255,255,0.065)"

# ── Card borders (semantic) — brighter than card bg for edge definition ──
BORDER_CARD             = "rgba(255,255,255,0.055)"
BORDER_CARD_HOVER       = "rgba(255,255,255,0.080)"
BORDER_CARD_ACCENT      = "rgba(143,183,255,0.10)"
BORDER_CARD_ELEVATED    = "rgba(255,255,255,0.055)"
BORDER_CONTROL          = "rgba(255,255,255,0.05)"
BORDER_CONTROL_HOVER    = "rgba(255,255,255,0.06)"
BORDER_SEPARATOR        = "rgba(143,183,255,0.08)"

# ── Card text (semantic) ──
TEXT_CARD_TITLE         = "rgba(255,255,255,0.88)"
TEXT_CARD_DESC          = "rgba(255,255,255,0.56)"
TEXT_PLACEHOLDER        = "rgba(255,255,255,0.42)"

# ── Status colors (semantic) ──
STATUS_INFO_BG          = "rgba(143,183,255,0.08)"
STATUS_INFO_TEXT        = "rgba(143,183,255,0.60)"
STATUS_WARNING_BG       = "rgba(200,180,100,0.08)"
STATUS_WARNING_TEXT     = "rgba(200,180,100,0.60)"
STATUS_SUCCESS_BG       = "rgba(100,220,140,0.08)"
STATUS_SUCCESS_TEXT     = "rgba(100,220,140,0.60)"
STATUS_ERROR_BG         = "rgba(255,100,100,0.08)"
STATUS_ERROR_TEXT       = "rgba(255,100,100,0.55)"
STATUS_ACTIVE_BG        = "rgba(100,220,140,0.10)"
STATUS_ACTIVE_TEXT      = "rgba(100,220,140,0.60)"
STATUS_DISCONNECTED_BG  = "rgba(255,255,255,0.06)"
STATUS_DISCONNECTED_TEXT = "rgba(255,255,255,0.42)"
STATUS_EXPERIMENTAL_BG  = "rgba(180,150,255,0.08)"
STATUS_EXPERIMENTAL_TEXT = "rgba(180,150,255,0.55)"

# ── MichiGlass tokens — higher contrast surfaces ──
GLASS_CARD_BG           = "rgba(255,255,255,0.045)"
GLASS_CARD_BORDER       = "rgba(255,255,255,0.060)"
GLASS_CARD_HOVER_BG     = "rgba(255,255,255,0.070)"
GLASS_CARD_HOVER_BORDER = "rgba(255,255,255,0.090)"
GLASS_CARD_ACCENT_BORDER = "rgba(143,183,255,0.12)"
GLASS_HERO_BG           = "qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 rgba(255,255,255,0.075), stop:1 rgba(143,183,255,0.040))"
GLASS_HERO_BORDER       = "rgba(255,255,255,0.070)"
GLASS_POPUP_BG          = "rgba(13,16,24,0.985)"
GLASS_POPUP_BORDER      = "rgba(143,183,255,0.14)"
GLASS_INPUT_BG          = "rgba(255,255,255,0.055)"
GLASS_INPUT_BORDER      = "rgba(255,255,255,0.07)"
GLASS_INPUT_FOCUS_BORDER = "rgba(143,183,255,0.24)"
GLASS_BUTTON_BG         = "rgba(255,255,255,0.050)"
GLASS_BUTTON_HOVER_BG   = "rgba(255,255,255,0.080)"
GLASS_BUTTON_PRESSED_BG = "rgba(255,255,255,0.030)"
GLASS_BUTTON_BORDER     = "rgba(255,255,255,0.06)"
GLASS_BUTTON_HOVER_BORDER = "rgba(255,255,255,0.10)"
GLASS_TABLE_ROW_ALT     = "rgba(255,255,255,0.020)"
GLASS_TABLE_ROW_HOVER   = "rgba(143,183,255,0.05)"
GLASS_TABLE_SELECTION   = "rgba(143,183,255,0.10)"
GLASS_EMPTY_BG          = "rgba(255,255,255,0.020)"
GLASS_BADGE_BG          = "rgba(255,255,255,0.055)"
GLASS_BADGE_HOVER_BG    = "rgba(255,255,255,0.080)"
GLASS_DIVIDER           = "rgba(143,183,255,0.07)"

# ── NowPlayingBar slider colors — warm original palette ──
# Do NOT replace with ACCENT_BLUE. These are specific to the player bar slider.
NOWPLAYING_SLIDER_GRADIENT_START = "#FF7A00"
NOWPLAYING_SLIDER_GRADIENT_MID_A = "#FF4A2D"
NOWPLAYING_SLIDER_GRADIENT_MID_B = "#F21B5B"
NOWPLAYING_SLIDER_GRADIENT_END   = "#9F0C80"
NOWPLAYING_SLIDER_THUMB_DEFAULT  = "#F92141"
NOWPLAYING_SLIDER_THUMB_HOVER    = "#FF4A2D"
NOWPLAYING_SLIDER_THUMB_PRESSED  = "#F21B5B"
NOWPLAYING_SLIDER_DISABLED_FILL  = "#525866"
NOWPLAYING_SLIDER_DISABLED_BORDER = "#747986"
