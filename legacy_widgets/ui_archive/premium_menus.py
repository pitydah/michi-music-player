"""Premium menu QSS — reusable dark/glass menu styling for Michi Music Player."""


def premium_menu_qss() -> str:
    return """
    QMenu {
        background: rgba(18,20,28,0.98);
        color: rgba(255,255,255,0.90);
        border: 1px solid rgba(255,255,255,0.105);
        border-radius: 13px;
        padding: 8px;
    }
    QMenu::item {
        padding: 9px 34px 9px 14px;
        border-radius: 9px;
        color: rgba(255,255,255,0.86);
        font-size: 12.5px;
        font-weight: 560;
    }
    QMenu::item:selected {
        background: rgba(255,255,255,0.085);
        color: #FFFFFF;
    }
    QMenu::item:checked {
        background: rgba(255,255,255,0.125);
        color: #FFFFFF;
    }
    QMenu::item:disabled {
        color: rgba(255,255,255,0.32);
    }
    QMenu::separator {
        height: 1px;
        background: rgba(255,255,255,0.075);
        margin: 6px 8px;
    }
    """
