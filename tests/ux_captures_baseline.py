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

    _nav_bridge = None
    for b_name in dir(bootstrap):
        b = getattr(bootstrap, b_name, None)
        if b and hasattr(b, 'navigate') and hasattr(b, 'currentRoute'):
            _nav_bridge = b
            break

    _previous_hash = None

    def capture_all():
        nonlocal _nav_bridge
        if not _nav_bridge:
            for name in dir(bootstrap):
                obj = getattr(bootstrap, name, None)
                if obj and hasattr(obj, 'navigate') and hasattr(obj, 'currentRoute'):
                    _nav_bridge = obj
                    break
        navigate_next(0)

    def navigate_next(idx):
        if idx >= len(PAGES):
            finish()
            return
        page_name = PAGES[idx]
        if _nav_bridge and hasattr(_nav_bridge, 'navigate'):
            try:
                _nav_bridge.navigate(page_name)
            except Exception:
                pass
        QTimer.singleShot(1200, lambda: _capture_one(page_name, idx))

    def _capture_one(page_name, idx):
        nonlocal _previous_hash
        from PySide6.QtGui import QScreen
        import hashlib
        window = None
        for obj in engine.rootObjects():
            if isinstance(obj, QWindow):
                window = obj
                break
        if window:
            path = os.path.join(OUTPUT_DIR, f"{page_name}.png")
            screen = QScreen.grabWindow(QGuiApplication.primaryScreen(), window.winId())
            screen.save(path)
            current_hash = hashlib.md5(open(path, "rb").read()).hexdigest()
            if _previous_hash and current_hash == _previous_hash:
                print(f"  WARN: {page_name} has same hash as previous page (navigation may have failed)")
            _previous_hash = current_hash
            screenshots.append((page_name, path))
        QTimer.singleShot(200, lambda: navigate_next(idx + 1))

    def finish():
        try:
            bootstrap.shutdown()
        except Exception:
            pass
        for name, path in screenshots:
            print(f"  {name}: {path}")
        print(f"\n{len(screenshots)} captures saved to {OUTPUT_DIR}")
        unique_hashes = len(set(s[0] for s in screenshots))
        if unique_hashes < len(screenshots) and len(screenshots) > 1:
            print(f"  WARNING: {len(screenshots) - unique_hashes} duplicate pages detected")
        QTimer.singleShot(0, app.quit)

    QTimer.singleShot(500, capture_all)
    return app.exec()


if __name__ == "__main__":
    sys.exit(run())
