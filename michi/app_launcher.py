"""Application launcher — reads MICHI_UI env var and launches the appropriate UI.

No fallback within the same process. If fallback is needed, use os.execv or
a clean subprocess.
"""
import os


def _resolve_ui_mode() -> str:
    mode = os.environ.get("MICHI_UI", "widgets").strip().lower()
    if mode not in ("widgets", "qml"):
        mode = "widgets"
    return mode


def launch():
    ui_mode = _resolve_ui_mode()
    if ui_mode == "qml":
        from michi.qml_app import run_qml
        run_qml()
    else:
        from michi.widgets_app import run_widgets
        run_widgets()
