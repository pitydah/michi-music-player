class TestBridgeFactoryNoPrivatePatching:
    def test_no_underscore_service_patch_outside_init(self):
        import ui_qml_bridge.bridge_factory as bf
        with open(bf.__file__) as f:
            lines = f.readlines()
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if '._service' in stripped and 'self._service' not in stripped and '._services' not in stripped and '._settings_service_cache' not in stripped and '._smart_tagging_service' not in stripped:
                raise AssertionError(f"Line {i}: unexpected ._service reference: {stripped}")

    def test_no_underscore_svc_patch_on_bridge(self):
        import ui_qml_bridge.bridge_factory as bf
        with open(bf.__file__) as f:
            lines = f.readlines()
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if '._svc' in stripped and 'self._svc' not in stripped and not stripped.startswith('#'):
                raise AssertionError(f"Line {i}: unexpected ._svc reference: {stripped}")

    def test_no_underscore_lib_fallback(self):
        import ui_qml_bridge.bridge_factory as bf
        with open(bf.__file__) as f:
            src = f.read()
        assert '._lib =' not in src, "Should not set private _lib attribute"

    def test_no_underscore_qe_fallback(self):
        import ui_qml_bridge.bridge_factory as bf
        with open(bf.__file__) as f:
            src = f.read()
        assert '._qe =' not in src, "Should not set private _qe attribute"

    def test_attach_library_coordinator_exists(self):
        import ui_qml_bridge.job_bridge as jb_module
import pytest
pytestmark = [pytest.mark.qml_module("worker_manager")]

        with open(jb_module.__file__) as f:
            src = f.read()
        assert 'def attach_library_coordinator' in src
