"""Test that QML compiles without errors and app starts correctly."""
import os
import sys
import subprocess
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


@pytest.mark.skipif(not os.environ.get('QT_QPA_PLATFORM'), reason="Requires QT_QPA_PLATFORM")
def test_app_starts():
    """App launches, prints READY, no traceback, no duplicate actions."""
    proc = subprocess.run(
        [sys.executable, "-c", "import sys; sys.path.insert(0, '.'); from michi.verify_app import run_verify; sys.exit(run_verify())"],
        capture_output=True, text=True, timeout=60,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "MICHI_SAFE_MODE": "1"},
    )
    combined = proc.stdout + proc.stderr

    assert "QML verify mode OK" in combined, (
        f"App never reached OK. stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
    assert proc.returncode == 0, f"Bad return code: {proc.returncode}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    assert "Traceback" not in combined, f"Traceback in output:\n{combined}"
    assert "Failed to load QML" not in combined, f"QML load failure:\n{combined}"
    assert "Duplicate action ID" not in combined, f"Duplicate actions:\n{combined}"


@pytest.mark.skipif(not os.environ.get('QT_QPA_PLATFORM'), reason="Requires QT_QPA_PLATFORM")
def test_app_no_duplicate_actions():
    """No duplicate action IDs in ActionRegistry."""
    proc = subprocess.run(
        [sys.executable, "-c", "import sys; sys.path.insert(0, '.'); from michi.verify_app import run_verify; sys.exit(run_verify())"],
        capture_output=True, text=True, timeout=60,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "MICHI_SAFE_MODE": "1"},
    )
    combined = proc.stdout + proc.stderr
    assert "Duplicate action ID" not in combined, f"Duplicate actions found:\n{combined}"
    assert proc.returncode == 0, f"App start failed:\n{combined}"
