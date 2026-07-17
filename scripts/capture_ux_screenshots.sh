#!/usr/bin/env bash
# Capture the main QML routes after real navigation and reject duplicate frames.
set -euo pipefail

OUTPUT_DIR="${1:-artifacts/ux-screenshots}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUTPUT_DIR="$(mkdir -p "$OUTPUT_DIR" && cd "$OUTPUT_DIR" && pwd)"

if ! command -v Xvfb >/dev/null 2>&1; then
    echo "ERROR: Xvfb no está instalado. Instala el paquete xvfb." >&2
    exit 1
fi

DISPLAY_NUM="$(shuf -i 100-999 -n 1)"
Xvfb ":${DISPLAY_NUM}" -screen 0 1440x900x24 >/tmp/michi-xvfb.log 2>&1 &
XVFB_PID=$!

cleanup() {
    kill "$XVFB_PID" 2>/dev/null || true
    wait "$XVFB_PID" 2>/dev/null || true
}
trap cleanup EXIT

sleep 1
export DISPLAY=":${DISPLAY_NUM}"
export QT_QPA_PLATFORM=xcb
export MICHI_SAFE_MODE=1
export MICHI_UX_OUTPUT_DIR="$OUTPUT_DIR"

cd "$REPO_ROOT"

echo "=== Michi UX screenshot audit ==="
echo "Display: $DISPLAY"
echo "Output:  $OUTPUT_DIR"

python3 <<'PY'
from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "xcb")
os.environ.setdefault("MICHI_SAFE_MODE", "1")

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QGuiApplication, QWindow
from PySide6.QtQml import QQmlApplicationEngine

from core.application_bootstrap import ApplicationBootstrap

PAGES = [
    "home",
    "library",
    "playback",
    "queue",
    "playlists",
    "radio",
    "mix",
    "connections",
    "devices",
    "home_audio",
    "settings",
    "diagnostics",
    "assistant",
    "audio_lab",
    "library_doctor",
    "disc_lab",
    "history",
    "lyrics",
    "equalizer",
]

output_dir = Path(os.environ["MICHI_UX_OUTPUT_DIR"])
output_dir.mkdir(parents=True, exist_ok=True)

app = QGuiApplication(sys.argv)
app.setApplicationName("Michi UX Audit")
app.setOrganizationName("Michi")
app.setOrganizationDomain("michi.app")

bootstrap = ApplicationBootstrap()
bootstrap.build()
bootstrap.start()
bridges = bootstrap.create_bridges()

engine = QQmlApplicationEngine()
bootstrap.register_context(engine)
qml_path = Path.cwd() / "ui_qml" / "Main.qml"
engine.load(QUrl.fromLocalFile(str(qml_path)))

windows = [obj for obj in engine.rootObjects() if isinstance(obj, QWindow)]
if not windows:
    print("ERROR: Main.qml no creó una ventana", file=sys.stderr)
    bootstrap.shutdown()
    raise SystemExit(1)

window = windows[0]
navigation = bridges.get("navigation")
if navigation is None or not callable(getattr(navigation, "navigate", None)):
    print("ERROR: NavigationBridge no está disponible", file=sys.stderr)
    bootstrap.shutdown()
    raise SystemExit(1)

screen = QGuiApplication.primaryScreen()
if screen is None:
    print("ERROR: no existe una pantalla para capturar", file=sys.stderr)
    bootstrap.shutdown()
    raise SystemExit(1)

state = {
    "index": 0,
    "captures": [],
    "hashes": {},
    "failures": [],
}


def finish() -> None:
    try:
        bootstrap.shutdown()
    finally:
        print(f"\nCapturas válidas: {len(state['captures'])}/{len(PAGES)}")
        for page, path, digest in state["captures"]:
            print(f"  {page:18} {path.name:28} sha256={digest[:12]}")
        if state["failures"]:
            print("\nERRORES:", file=sys.stderr)
            for failure in state["failures"]:
                print(f"  - {failure}", file=sys.stderr)
        app.exit(1 if state["failures"] else 0)


def capture_current(page: str) -> None:
    path = output_dir / f"{page}.png"
    pixmap = screen.grabWindow(window.winId())
    if pixmap.isNull() or not pixmap.save(str(path)):
        state["failures"].append(f"{page}: no fue posible guardar la captura")
    else:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        previous = state["hashes"].get(digest)
        if previous is not None:
            state["failures"].append(
                f"{page}: captura idéntica a {previous}; la navegación no cambió la vista"
            )
        else:
            state["hashes"][digest] = page
        state["captures"].append((page, path, digest))

    state["index"] += 1
    QTimer.singleShot(150, navigate_next)


def navigate_next() -> None:
    if state["index"] >= len(PAGES):
        finish()
        return

    page = PAGES[state["index"]]
    try:
        result = navigation.navigate(page)
    except Exception as exc:
        state["failures"].append(f"{page}: navegación lanzó {exc}")
        state["index"] += 1
        QTimer.singleShot(50, navigate_next)
        return

    if isinstance(result, dict) and result.get("ok") is False:
        error = result.get("error") or result.get("message") or "ruta rechazada"
        state["failures"].append(f"{page}: {error}")
        state["index"] += 1
        QTimer.singleShot(50, navigate_next)
        return

    # Two event-loop turns let PageStack instantiate the route and resolve bindings.
    QTimer.singleShot(350, lambda p=page: QTimer.singleShot(450, lambda: capture_current(p)))


QTimer.singleShot(800, navigate_next)
raise SystemExit(app.exec())
PY

echo "=== UX screenshot audit completed ==="
