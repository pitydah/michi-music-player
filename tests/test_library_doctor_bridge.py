from unittest.mock import MagicMock
from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge


class TestLibraryDoctorBridge:
    def test_create(self):
        bridge = LibraryDoctorBridge(db=MagicMock(), worker_manager=MagicMock())
        assert bridge is not None
