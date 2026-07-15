"""Application launcher — reads MICHI_UI env var, dispatches to QML or Widgets.
Does NOT create QApplication, QQmlApplicationEngine, or QtWidgets directly.
"""
from __future__ import annotations

import os
import sys


_VALID_MODES = {"qml", "widgets", "verify"}


def launch() -> int:
    ui_mode = os.environ.get("MICHI_UI", "qml").strip().lower()
    if ui_mode not in _VALID_MODES:
        print(
            f"[MICHI_UI] Invalid MICHI_UI={ui_mode!r}. "
            f"Valid values: {', '.join(sorted(_VALID_MODES))}",
            file=sys.stderr,
        )
        return 1

    if ui_mode == "qml":
        return _launch_qml()
    elif ui_mode == "verify":
        return _launch_verify()
    else:
        return _launch_widgets()


def _launch_qml() -> int:
    try:
        from michi.qml_app import run_qml
        return run_qml()
    except Exception as exc:
        print(f"[MICHI_UI] QML launch failed: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        print("[MICHI_UI] DIAGNOSIS:", file=sys.stderr)
        _diagnose_qml()
        return 2


def _launch_verify() -> int:
    try:
        from michi.verify_app import run_verify
        return run_verify()
    except Exception as exc:
        print(f"[MICHI_UI] QML verify failed: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return 2


def _launch_widgets() -> int:
    try:
        from michi.widgets_app import run_widgets
        return run_widgets()
    except Exception as exc:
        print(f"[MICHI_UI] Widgets launch failed: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return 2


def _diagnose_qml() -> None:
    import importlib
    for mod_name in ("PySide6", "PySide6.QtGui", "PySide6.QtQml"):
        try:
            importlib.import_module(mod_name)
            print(f"  [OK] {mod_name} available", file=sys.stderr)
        except ImportError as e:
            print(f"  [FAIL] {mod_name}: {e}", file=sys.stderr)
    import os as _os
    qml_dir = _os.path.join(_os.path.dirname(__file__), "..", "ui_qml")
    main_qml = _os.path.join(qml_dir, "Main.qml")
    if _os.path.exists(main_qml):
        print(f"  [OK] Main.qml found at {main_qml}", file=sys.stderr)
    else:
        print(f"  [FAIL] Main.qml not found at {main_qml}", file=sys.stderr)
