"""Stub — QtWidgets frontend retired.

Michi now runs exclusively on QML.
See `main.py` or `michi/qml_app.py`.
"""
from __future__ import annotations

import sys


def main() -> int:
    print("Michi ya no incluye la interfaz QtWidgets.", file=sys.stderr)
    print("Ejecute 'python main.py' para usar la interfaz QML.", file=sys.stderr)
    return 2


run_widgets = main

if __name__ == "__main__":
    sys.exit(main())
