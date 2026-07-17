#!/usr/bin/env python3
"""Capture UI/UX baseline screenshots using QQuickWindow.grabWindow() in offscreen mode.

Usage: python scripts/capture_uiux_baseline.py [--output DIR]
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "uiux" / "screenshots" / "baseline-post-x10"

PAGES = [
    ("home", "home"),
    ("library", "library"),
    ("nowplaying", "nowplaying"),
    ("queue", "queue"),
    ("playlists", "playlists"),
    ("mix", "mix"),
    ("settings", "settings"),
    ("devices", "devices"),
    ("connections", "connections"),
    ("eq", "eq"),
]

ENGINE_SCRIPT = """
import sys, os, json, time
from pathlib import Path
sys.path.insert(0, '.')
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import QUrl, QTimer

app = QGuiApplication(sys.argv)
engine = QQmlApplicationEngine()
engine.addImportPath(str(Path('.').resolve()))
engine.load(QUrl.fromLocalFile('ui_qml/Main.qml'))

root = None
def on_ready():
    global root
    root = engine.rootObjects()[0] if engine.rootObjects() else None
    if root is None:
        print("ERROR: No root object")
        sys.exit(1)
    print("READY")
    QTimer.singleShot(2000, lambda: capture_all())

def capture_all():
    results = {}
    for name, route in PAGES:
        nav = root.findChild(type(root), "navigationBridge") if hasattr(root, 'findChild') else None
        if nav and hasattr(nav, 'navigate'):
            nav.navigate(route)
        time.sleep(0.5)
        import gc; gc.collect()
        win = None
        for obj in engine.rootObjects():
            if hasattr(obj, 'grabWindow'):
                win = obj
                break
        if win is None:
            results[name] = "NO_WINDOW"
            continue
        try:
            img = win.grabWindow()
            out = OUTPUT_DIR / f"baseline-{name}.png"
            img.save(str(out))
            results[name] = str(out)
        except Exception as e:
            results[name] = f"ERROR: {e}"
    print(json.dumps(results))
    sys.exit(0)

engine.objectCreationCompleted.connect(on_ready)
sys.exit(app.exec())
"""


def main():
    parser = argparse.ArgumentParser(description="Capture UI/UX baseline screenshots")
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    script = ENGINE_SCRIPT.replace("OUTPUT_DIR", json.dumps(str(output_dir)))
    script = script.replace("PAGES", json.dumps(PAGES))

    print(f"Output: {output_dir}")
    print("Launching QML app for captures...")

    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True, timeout=120,
        cwd=Path(__file__).resolve().parent.parent,
    )

    print(result.stdout)
    if result.stderr:
        for line in result.stderr.split("\n"):
            if "ERROR" in line or "Traceback" in line:
                print(line, file=sys.stderr)

    try:
        data = json.loads(result.stdout.strip().split("\n")[-1])
        for name, path in data.items():
            if path.startswith("ERROR") or path == "NO_WINDOW":
                print(f"  {name}: FAIL - {path}")
            else:
                size = os.path.getsize(path)
                print(f"  {name}: OK ({size} bytes)")
    except (json.JSONDecodeError, IndexError):
        print("ERROR: Could not parse capture results")
        print(result.stdout[-500:])


if __name__ == "__main__":
    main()
