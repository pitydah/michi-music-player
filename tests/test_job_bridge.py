from unittest.mock import MagicMock
from ui_qml_bridge.job_bridge import JobBridge


class TestJobBridge:
    def test_create(self):
        bridge = JobBridge(worker_manager=MagicMock(), db=MagicMock())
        assert bridge is not None
