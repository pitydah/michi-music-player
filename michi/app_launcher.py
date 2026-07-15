"""Application launcher — reads MICHI_UI env var, dispatches to QML or Widgets.
Does NOT create QApplication directly.
"""
from __future__ import annotations

import os
import sys


def launch():
    ui_mode = os.environ.get("MICHI_UI", "qml").lower()
    if ui_mode == "qml":
        from michi.qml_app import run_qml
        sys.exit(run_qml())
    elif ui_mode == "verify":
        from michi.qml_app import run_qml
        exit_code = run_qml()
        print(f"QML verification exit code: {exit_code}")
        sys.exit(exit_code)
    else:
        from michi.widgets_app import run_widgets
        sys.exit(run_widgets())
