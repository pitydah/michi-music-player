"""R2 PRODUCTION REALITY — QML runtime warning gate.

Boots the REAL ApplicationContainer offscreen and fails CI on any of the
runtime QML warning families that previously polluted production logs
(and that source-string tests cannot catch):

- "Cannot read property ... of null"      (context properties torn down /
  mis-wired bridges)
- "Unable to assign [undefined] ..."      (type mismatches like assigning
  a QQuickWindow to a QQuickItem* property)
- "... is not a function"                 (wrong-scope function calls,
  e.g. root.makeRandom on MichiMaterialTexture)
- "Could not convert argument 0 ... QDateTime"  (MichiFormat feeding
  strings to Qt.locale().toString)
- "qsTr(): third argument (n) must be a number" (pluralization misuse)
- "no signal of the target matches the name"    (Connections handler typos)

The gate runs the container lifecycle (initialize -> settle -> shutdown)
and asserts zero warnings from these families.
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
    "QDateTime",
    "qsTr(): third argument",
    "no signal of the target matches",
)


class TestQmlRuntimeWarningGate:
    def test_real_container_boots_without_runtime_qml_warnings(self, qapp):
        from PySide6.QtCore import qInstallMessageHandler
        from PySide6.QtWidgets import QApplication

        captured: list[tuple[float, str]] = []
        t0 = time.monotonic()

        def handler(mode, ctx, msg):
            captured.append((round(time.monotonic() - t0, 2), str(msg)))

        qInstallMessageHandler(handler)
        try:
            from michi.bootstrap import ApplicationContainer

            container = ApplicationContainer()
            container.initialize()
            for _ in range(50):
                QApplication.processEvents()
            container.shutdown()
        finally:
            qInstallMessageHandler(None)

        violations = [
            (ts, msg)
            for ts, msg in captured
            if any(p in msg for p in DANGEROUS_PATTERNS)
        ]
        assert violations == [], (
            f"QML runtime warnings during real container boot ({len(violations)}):\n"
            + "\n".join(f"  t+{ts}s: {msg[:160]}" for ts, msg in violations[:10])
        )
