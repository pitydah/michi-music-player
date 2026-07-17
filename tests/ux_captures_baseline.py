"""Generate UX baseline screenshots after real route navigation.

This module is an executable audit helper rather than a normal pytest test. It
returns a non-zero status when a route cannot be loaded, a frame cannot be
captured, or two named routes produce the exact same image.
"""
from __future__ import annotations

import hashlib
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.WARNING)

PAGES = [
    "home",
    "library",
    "playback",
    "nowplaying",
    "queue",
    "playlists",
    "radio",
    "mix",
    "connections",
    "devices.list",
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
_DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "artifacts" / "ux-baseline"
OUTPUT_DIR = Path(os.environ.get("MICHI_UX_OUTPUT_DIR", _DEFAULT_OUTPUT_DIR)).resolve()

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["MICHI_CAPTURE_MODE"] = "1"
os.environ.setdefault("MICHI_SAFE_MODE", "1")


def run() -> int:
    from PySide6.QtCore import QTimer, QUrl
    from PySide6.QtGui import QGuiApplication, QWindow
    from PySide6.QtQml import QQmlApplicationEngine

    from core.application_bootstrap import ApplicationBootstrap

    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    app.setApplicationName("Michi UX Capture")
    app.setOrganizationName("Michi")
    app.setOrganizationDomain("michi.app")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    bootstrap = ApplicationBootstrap()
    bootstrap.build()
    bootstrap.start()
    bridges = bootstrap.create_bridges()

    engine = QQmlApplicationEngine()
    bootstrap.register_context(engine)
    qml_path = Path(__file__).resolve().parent.parent / "ui_qml" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path)))

    windows = [obj for obj in engine.rootObjects() if isinstance(obj, QWindow)]
    if not windows:
        logging.error("Main.qml did not create a root window")
        bootstrap.shutdown()
        return 1

    navigation = bridges.get("navigation")
    if navigation is None or not callable(getattr(navigation, "navigate", None)):
        logging.error("NavigationBridge is unavailable")
        bootstrap.shutdown()
        return 1

    screen = QGuiApplication.primaryScreen()
    if screen is None:
        logging.error("No screen available for screenshot capture")
        bootstrap.shutdown()
        return 1

    state = {
        "index": 0,
        "captures": [],
        "hashes": {},
        "failures": [],
    }
    window = windows[0]

    def finish() -> None:
        try:
            bootstrap.shutdown()
        finally:
            print(f"\n{len(state['captures'])}/{len(PAGES)} captures written to {OUTPUT_DIR}")
            for page, path, digest in state["captures"]:
                print(f"  {page:18} {path.name:28} sha256={digest[:12]}")
            if state["failures"]:
                print("\nCapture failures:", file=sys.stderr)
                for failure in state["failures"]:
                    print(f"  - {failure}", file=sys.stderr)
            app.exit(1 if state["failures"] else 0)

    def capture_current(page: str) -> None:
        path = OUTPUT_DIR / f"{page.replace('.', '_')}.png"
        pixmap = screen.grabWindow(window.winId())
        if pixmap.isNull() or not pixmap.save(str(path)):
            state["failures"].append(f"{page}: screenshot could not be saved")
        else:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            previous_page = state["hashes"].get(digest)
            if previous_page is not None:
                state["failures"].append(
                    f"{page}: frame is identical to {previous_page}; route navigation did not change the UI"
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

        requested = PAGES[state["index"]]
        navigation.navigate(requested)
        resolved = navigation.currentRoute
        if resolved != requested:
            state["failures"].append(
                f"{requested}: resolved as {resolved}; route is invalid or its capability is unavailable"
            )
            state["index"] += 1
            QTimer.singleShot(50, navigate_next)
            return

        # Allow PageStack and asynchronous loaders to settle before capture.
        QTimer.singleShot(
            400,
            lambda page=requested: QTimer.singleShot(500, lambda: capture_current(page)),
        )

    QTimer.singleShot(800, navigate_next)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
