from unittest.mock import MagicMock
from ui_qml_bridge.diagnostics_bridge import DiagnosticsBridge


class TestDiagnosticsBridge:
    def test_create(self):
        bridge = DiagnosticsBridge(diagnostics_service=MagicMock())
        assert bridge is not None
