"""Test ApplicationBootstrap.build() without mocks - must not crash."""
import os
import sys
import pytest


@pytest.mark.skipif(not os.environ.get('CI'), reason="Requires full environment")
def test_bootstrap_build():
    """ApplicationBootstrap.build() completes without errors."""
    from core.application_bootstrap import ApplicationBootstrap
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    bootstrap = ApplicationBootstrap()
    bootstrap.build()
    assert bootstrap.container is not None
    assert bootstrap.container.get("action_registry") is not None


@pytest.mark.skipif(True, reason="Requires full desktop environment")
def test_bootstrap_with_engine():
    """ApplicationBootstrap with GStreamerEngine."""
    from core.application_bootstrap import ApplicationBootstrap
    bootstrap = ApplicationBootstrap()
    bootstrap.build()
    ar = bootstrap.container.get("action_registry")
    issues = ar.validate_all()
    assert len(issues) == 0, f"ActionRegistry issues: {issues}"
