#!/usr/bin/env python3
"""X10.09 — Productive boot real: ApplicationBootstrap -> BridgeFactory -> ContextRegistrar -> Main.qml -> Navigation -> Shutdown."""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["MICHI_SAFE_MODE"] = "1"

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("productive_boot")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))  # noqa: E402

from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtCore import QCoreApplication  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402

from core.application_bootstrap import ApplicationBootstrap  # noqa: E402
from core.service_container import ContainerState  # noqa: E402

NAV_ROUTES = ["home", "library", "playback", "home_audio", "connections", "queue", "radio", "playlists", "ai", "library.tracks", "library.albums", "mix", "history"]

def main():
    errors = []
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(REPO / "ui_qml"))

    bootstrap = ApplicationBootstrap()
    bootstrap.build()

    container = bootstrap.container

    none_req = container.validate_no_none_required()
    if none_req:
        errors.append(f"REQUIRED services are None: {none_req}")

    container.start()
    if container.state == ContainerState.FAILED:
        errors.append(f"Container FAILED on start: {container.health()['failures']}")
    elif container.state in (ContainerState.READY, ContainerState.DEGRADED):
        logger.info("Container state=%s after start", container.state.value)

    bootstrap.create_bridges()
    registrar = bootstrap.register_context(engine)
    audit = registrar.audit()
    logger.info("Context registered: %d bridges, violations=%s", audit["total"], audit["violations"])
    if audit["violations"]:
        errors.append(f"Context violations: {audit['violations']}")

    ok = bootstrap.load_qml(engine)
    if not ok:
        errors.append("Main.qml load failed — no root objects")
        app.quit()
        return 1

    root_objects = engine.rootObjects()
    if not root_objects:
        errors.append("engine.rootObjects() is empty after load")
    else:
        logger.info("Main.qml loaded: %d root object(s)", len(root_objects))
        win = root_objects[0]

        def _walk_children(obj, max_depth=5):
            items = []
            def _walk(o, d):
                if d > max_depth:
                    return
                items.append(o)
                for c in o.children():
                    _walk(c, d + 1)
            _walk(obj, 0)
            return items
        all_obs = _walk_children(win, max_depth=6)
        qobject_count = len(all_obs)
        app_shell_present = qobject_count > 10
        if app_shell_present:
            logger.info("AppShell present: %d QML objects in tree", qobject_count)
        else:
            errors.append("AppShell NOT found")

        ctx = engine.rootContext()
        navigation_bridge = ctx.contextProperty("navigationBridge") if ctx else None

        if navigation_bridge:
            logger.info("NavigationBridge found in context, initial route=%s", getattr(navigation_bridge, "currentRoute", "?"))
            registered_routes = []
            for r in NAV_ROUTES:
                try:
                    navigation_bridge.navigate(r)
                    QCoreApplication.processEvents()
                    registered_routes.append(r)
                    logger.info("  Navigated to '%s' — currentRoute=%s", r, getattr(navigation_bridge, "currentRoute", "?"))
                except Exception as e:
                    errors.append(f"Navigation to '{r}' failed: {e}")
            logger.info("Routes navigated: %s", registered_routes)
        else:
            errors.append("NavigationBridge NOT found in context")

    bootstrap.shutdown()
    logger.info("Shutdown complete")

    if errors:
        logger.error("PRODUCTIVE BOOT FAILED:")
        for e in errors:
            logger.error("  - %s", e)
        return 1

    logger.info("PRODUCTIVE BOOT PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
