"""Sidebar QSS styles — centralized, reusable, state-driven."""


def sidebar_root_qss() -> str:
    return """
        QWidget#sidebarGlass {
            background: transparent;
            border: none;
        }
    """


def brand_card_qss() -> str:
    return """
        QFrame {
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.07);
            border-radius: 14px;
        }
    """


def search_qss() -> str:
    return """
        QLineEdit#sidebarSearch {
            background: rgba(255,255,255,0.055);
            border: 1px solid rgba(255,255,255,0.055);
            border-radius: 15px;
            padding: 7px 32px 7px 12px;
            color: rgba(255,255,255,0.94);
            font-size: 13px;
            selection-background-color: rgba(143,183,255,0.35);
        }
        QLineEdit#sidebarSearch:focus {
            background: rgba(143,183,255,0.055);
            border: 1px solid rgba(143,183,255,0.22);
        }
    """


def scroll_area_qss() -> str:
    return """
        QScrollArea { background: transparent; border: none; }
        QScrollBar:vertical {
            width: 3px;
            background: transparent;
        }
        QScrollBar::handle:vertical {
            background: rgba(255,255,255,0.08);
            min-height: 36px;
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


def section_header_qss(dark: bool = True, hover: bool = False) -> str:
    if not dark:
        normal_c = "rgba(28,28,30,0.52)"
        hover_c = "rgba(28,28,30,0.64)"
    else:
        normal_c = "rgba(255,255,255,0.78)"
        hover_c = "rgba(255,255,255,0.92)"
    c = hover_c if hover else normal_c
    return (
        f"font-size:10px;font-weight:600;color:{c};letter-spacing:0.8px;"
        "background:transparent;border:none;"
    )


def section_chevron_qss(dark: bool = True, hover: bool = False) -> str:
    if not dark:
        normal_c = "rgba(28,28,30,0.52)"
        hover_c = "rgba(28,28,30,0.72)"
    else:
        normal_c = "rgba(255,255,255,0.78)"
        hover_c = "rgba(255,255,255,0.92)"
    c = hover_c if hover else normal_c
    return (
        f"font-size:10px;color:{c};background:transparent;"
        "border:none;"
    )


def _text_c(state: str) -> str:
    return {
        "normal": "rgba(255,255,255,0.82)",
        "hover": "rgba(255,255,255,0.96)",
        "active": "rgba(255,255,255,1.00)",
    }.get(state, "rgba(255,255,255,0.82)")


def _font_weight(state: str) -> int:
    return {"normal": 500, "hover": 500, "active": 600}.get(state, 500)


def item_qss(state: str) -> str:
    if state == "active":
        return (
            "background: rgba(143,183,255,0.12);"
            "border: 1px solid rgba(143,183,255,0.14);"
            "border-radius: 13px; margin: 1px 6px;"
        )
    if state == "hover":
        return (
            "background: transparent;"
            "border: none;"
            "border-radius: 12px; margin: 1px 6px;"
        )
    return (
        "background: transparent; border: none;"
        "border-radius: 12px; margin: 1px 6px;"
    )


def item_label_qss(state: str) -> str:
    c = _text_c(state)
    w = _font_weight(state)
    return (
        f"font-size:13px;font-weight:{w};color:{c};"
        "background:transparent;border:none;"
    )


def badge_qss(state: str) -> str:
    base = "font-size:10px;"
    if state == "active":
        return (
            base
            + "color:rgba(245,245,247,0.72);"
            "background:rgba(255,255,255,0.10);"
            "border-radius:5px;padding:1px 7px;border:none;"
        )
    return (
        base
        + "color:rgba(245,245,247,0.45);"
        "background:rgba(255,255,255,0.06);"
        "border-radius:5px;padding:1px 7px;border:none;"
    )


def accent_qss(active: bool) -> str:
    if active:
        return (
            "background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            " stop:0 rgba(143,183,255,0.6), stop:1 rgba(143,183,255,0.25));"
            " border-radius: 2px; border: none;"
        )
    return "background: transparent; border-radius: 2px; border: none;"


def icon_label_qss() -> str:
    return (
        "background: transparent; border: none; padding: 0px; margin: 0px;"
    )
