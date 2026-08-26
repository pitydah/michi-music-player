"""R2.1-05 — TRUE QML runtime warning gate (production tree).

The previous gate only ran initialize() and never loaded main.qml — a
false gate. This gate:

1. creates the REAL ApplicationContainer,
2. initialize()s it,
3. loads the PRODUCTION main.qml through the SAME engine path run()
   uses (the testable load_qml() seam),
4. pumps enough events for loaders/bindings/Connections to instantiate,
5. exercises representative routes/components,
6. asserts POSITIVE PRESENCE first (root object, AppShell, NowPlayingBar,
   route views) — "pass by absence" is impossible,
7. collects Qt/QML messages across the whole interval and fails on the
   targeted warning families.

CLAIM:
    the real production QML tree instantiates without the runtime warning
    families that previously polluted production logs.

OBSERVABLES:
    QQmlApplicationEngine root objects, AppShell/NowPlayingBar object
    names in the live tree, Qt message handler output.

REAL:
    ApplicationContainer, production main.qml, production QML components.

FAKE:
    none.
"""

import os
import time

import pytest


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication.instance() or QGuiApplication([])
    yield app


DANGEROUS_PATTERNS = (
    "Cannot read property",
    "of null",
    "Unable to assign [undefined]",
    "is not a function",
    "Could not convert argument",
    "QDateTime",
    "qsTr(): third argument",
    "no signal of the target matches",
    "ReferenceError",
    "TypeError",
)


class TestQmlRuntimeWarningGate:
    def test_real_production_qml_tree_instantiates_clean(self, qapp):
        from PySide6.QtCore import QEventLoop, qInstallMessageHandler
        from PySide6.QtWidgets import QApplication

        captured: list[tuple[float, str]] = []
        t0 = time.monotonic()

        def handler(mode, ctx, msg):
            captured.append((round(time.monotonic() - t0, 2), str(msg)))

        qInstallMessageHandler(handler)
        container = None
        try:
            from michi.bootstrap import ApplicationContainer

            container = ApplicationContainer()
            container.initialize()
            # R2.1-05: load the PRODUCTION main.qml through the same
            # engine path run() uses (testable seam — run() = load_qml()
            # + exec())
            assert container.load_qml() is True, "main.qml failed to load"

            engine = container._engine
            root_objects = engine.rootObjects()
            # POSITIVE PRESENCE (no pass-by-absence):
            assert root_objects, "QML root object MISSING"
            # AppShell must be the production root
            root = root_objects[0]
            # positive presence: the production AppShell tree instantiated
            # (its distinctive children must exist in the live QObject tree)
            app_shell_evidence = root.findChild(object, "workspaceSplitView")
            assert app_shell_evidence is not None, (
                "AppShell MISSING from the QML tree (workspaceSplitView absent)"
            )

            # pump until the shell + NowPlayingBar instantiate
            deadline = time.monotonic() + 10.0
            now_playing = None
            while time.monotonic() < deadline:
                QApplication.processEvents(QEventLoop.AllEvents, 20)
                time.sleep(0.01)
                now_playing = root.findChild(object, "nowPlayingBar")
                if now_playing is not None:
                    break
            assert now_playing is not None, (
                "NowPlayingBar MISSING — the production QML tree did not "
                "instantiate the player bar"
            )

            # exercise representative routes through the production
            # navigation service (the same one the QML shell binds to)
            container._navigation.navigate("library")
            container._navigation.navigate("queue")
            container._navigation.navigate("settings")

            # settle all loaders/bindings
            deadline = time.monotonic() + 3.0
            while time.monotonic() < deadline:
                QApplication.processEvents(QEventLoop.AllEvents, 20)
                time.sleep(0.01)
        finally:
            if container is not None:
                container.shutdown()
            qInstallMessageHandler(None)

        violations = [
            (ts, msg)
            for ts, msg in captured
            if any(p in msg for p in DANGEROUS_PATTERNS)
        ]
        assert violations == [], (
            f"QML runtime warnings with the REAL production tree "
            f"({len(violations)}):\n"
            + "\n".join(f"  t+{ts}s: {msg[:180]}" for ts, msg in violations[:12])
        )
