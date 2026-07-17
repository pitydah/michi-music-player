"""UX-0.6: Capturas baseline automatizadas — genera screenshots de páginas core."""
from __future__ import annotations

import os
import sys
import logging

logging.basicConfig(level=logging.WARNING)

PAGES = [
    "home", "library", "playback", "nowplaying", "queue",
    "playlists", "radio", "mix", "connections", "devices",
    "home_audio", "settings", "diagnostics", "assistant",
    "audio_lab", "library_doctor", "disc_lab", "history",
    "lyrics", "eq",
]
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "artifacts", "ux-baseline")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["MICHI_CAPTURE_MODE"] = "1"


def run():
    from PySide6.QtGui import QGuiApplication, QWindow
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtCore import QTimer, QUrl

    app = QGuiApplication(sys.argv)
    app.setApplicationName("Michi UX Capture")
    app.setOrganizationName("Michi")
    app.setOrganizationDomain("michi.app")

    from core.application_bootstrap import ApplicationBootstrap

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    bootstrap = ApplicationBootstrap()
    try:
        bootstrap.build()
        bootstrap.start()
    except Exception as e:
        logging.warning("Bootstrap partial: %s", e)

    engine = QQmlApplicationEngine()
    engine.addImportPath(os.path.join(os.path.dirname(__file__), "..", "ui_qml"))

    try:
        bootstrap.create_bridges()
        bootstrap.register_context(engine)
    except Exception as e:
        logging.warning("Bridge registration partial: %s", e)

    qml_path = os.path.join(os.path.dirname(__file__), "..", "ui_qml", "Main.qml")
    engine.load(QUrl.fromLocalFile(qml_path))

    if not engine.rootObjects():
        logging.error("No root objects loaded")
        return 1

    screenshots = []

    def capture_all():
        for i, page_name in enumerate(PAGES):
            QTimer.singleShot((i + 1) * 800, lambda p=page_name: _capture_one(p))
        QTimer.singleShot((len(PAGES) + 1) * 800, finish)

    def _capture_one(page_name):
        from PySide6.QtGui import QScreen
        window = None
        for obj in engine.rootObjects():
            if isinstance(obj, QWindow):
                window = obj
                break
        if window:
            path = os.path.join(OUTPUT_DIR, f"{page_name}.png")
            screen = QScreen.grabWindow(QGuiApplication.primaryScreen(), window.winId())
            screen.save(path)
            screenshots.append((page_name, path))

    def finish():
        try:
            bootstrap.shutdown()
        except Exception:
            pass
        for name, path in screenshots:
            print(f"  {name}: {path}")
        print(f"\n{len(screenshots)} captures saved to {OUTPUT_DIR}")
        QTimer.singleShot(0, app.quit)

    QTimer.singleShot(500, capture_all)
    return app.exec()


if __name__ == "__main__":
    sys.exit(run())
