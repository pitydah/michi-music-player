"""Legacy widgets entry point — minimal launcher. Prefer QML (python main.py)."""
from __future__ import annotations

import sys
import logging

logger = logging.getLogger("michi.widgets_app")


def main():
    try:
        from PySide6.QtWidgets import QApplication
        app = QApplication(sys.argv)
        from legacy_widgets.ui.window import MainWindow
        win = MainWindow()
        win.show()
        return app.exec()
    except ImportError as e:
        print(f"ERROR: widgets not available ({e}). Install michi-widgets-legacy or run QML.")
        return 1


run_widgets = main

if __name__ == "__main__":
    sys.exit(main())
