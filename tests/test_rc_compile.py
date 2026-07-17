"""Test that QML compiles without errors."""
import os
import sys
import pytest
from pathlib import Path


@pytest.mark.skipif(not os.environ.get('QT_QPA_PLATFORM'), reason="Requires QT_QPA_PLATFORM")
def test_qml_compile_zero_errors():
    """All QML files compile without errors."""
    from PySide6.QtQml import QQmlEngine, QQmlComponent
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    engine = QQmlEngine()

    class D:
        pass
    for n in ['appBridge','navigationBridge','themeBridge','queueBridge',
              'libraryBridge','playbackBridge','playlistsBridge','historyBridge',
              'globalSearchBridge','settingsBridge','devicesBridge',
              'notificationBridge','michiAiBridge','commandPaletteBridge',
              'capabilityBridge','jobBridge','desktopBridge','homeBridge']:
        engine.rootContext().setContextProperty(n, D())

    errors = []
    for f in sorted(Path('ui_qml').rglob('*.qml')):
        c = QQmlComponent(engine, str(f))
        if c.status() != QQmlComponent.Ready:
            for e in c.errors():
                errors.append(f"{f.relative_to(Path('.'))}: {e.description()}")

    assert len(errors) == 0, f"{len(errors)} QML errors:\n" + "\n".join(errors[:10])
