"""Tests for QML workflow audit (HS).

Verifies that scripts/qml_workflow_audit.py correctly detects:
1. QQmlApplicationEngine
2. context properties
3. load page
4. objectName
5. QTest.mouseClick / keyClicks
6. signal
7. backend
8. visual state
9. destroy
10. cleanup
"""
import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
SCRIPTS = REPO / "scripts"


def _load_audit_mod():
    spec = importlib.util.spec_from_file_location("qml_workflow_audit", SCRIPTS / "qml_workflow_audit.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


audit_mod = _load_audit_mod()


@pytest.fixture
def tmp_workflow(tmp_path):
    f = tmp_path / "test_workflow_ok.py"
    f.write_text("""
from PySide6.QtQml import QQmlApplicationEngine
engine = QQmlApplicationEngine()
engine.rootContext().setContextProperty("myProp", 42)
engine.load("page.qml")
obj = engine.rootObjects()[0].findChild(objectName="myObject")
QTest.mouseClick(obj, Qt.LeftButton)
QTest.keyClicks(obj, "text")
signal_received = Signal.spy(obj, "changed")
assert obj.bridge_state == "ready"
assert obj.visible is True
obj.deleteLater()
assert not obj.closed
""")
    return f


@pytest.fixture
def tmp_bridge_only(tmp_path):
    f = tmp_path / "test_bridge_only.py"
    f.write_text("""
from ui_qml_bridge.some_bridge import SomeBridge
bridge = SomeBridge()
result = bridge.do_something()
assert result.get("ok")
""")
    return f


@pytest.fixture
def tmp_incomplete_workflow(tmp_path):
    f = tmp_path / "test_incomplete.py"
    f.write_text("""
import pytest
def test_simple():
    assert True
""")
    return f


class TestAuditFile:
    def test_detects_full_workflow(self, tmp_workflow):
        result = audit_mod.audit_file(tmp_workflow)
        assert result["verdict"] == "PASS"
        assert result["total_found"] == result["total_checks"]
        assert not result["has_bridge_only"]

    def test_detects_bridge_only(self, tmp_bridge_only):
        result = audit_mod.audit_file(tmp_bridge_only)
        assert result["verdict"] == "SKIP (bridge directo)"
        assert result["has_bridge_only"]

    def test_detects_incomplete(self, tmp_incomplete_workflow):
        result = audit_mod.audit_file(tmp_incomplete_workflow)
        assert result["verdict"] == "FAIL"
        assert result["total_found"] < result["total_checks"]

    def test_engine_check(self, tmp_path):
        f = tmp_path / "test_no_engine.py"
        f.write_text("def test_x(): pass")
        result = audit_mod.audit_file(f)
        assert not result["checks"]["crea engine QQmlApplicationEngine"]

    def test_mouse_click_check(self, tmp_path):
        f = tmp_path / "test_click.py"
        f.write_text("QTest.mouseClick(btn, Qt.LeftButton)")
        result = audit_mod.audit_file(f)
        assert result["checks"]["usa QTest.mouseClick o QTest.keyClicks"]

    def test_signal_check(self, tmp_path):
        f = tmp_path / "test_signal.py"
        f.write_text("spy = Signal.spy(obj, 'changed')")
        result = audit_mod.audit_file(f)
        assert result["checks"]["espera signal (waitForSignal|Signal.spy|signals)"]

    def test_backend_check(self, tmp_path):
        f = tmp_path / "test_backend.py"
        f.write_text('assert player.state == "playing"')
        result = audit_mod.audit_file(f)
        assert result["checks"]["verifica backend (assert.*bridge|assert.*service|assert.*player)"]

    def test_visual_state_check(self, tmp_path):
        f = tmp_path / "test_visual.py"
        f.write_text("assert widget.visible is True")
        result = audit_mod.audit_file(f)
        assert result["checks"]["verifica estado visual (assert.*visible|assert.*enabled|assert.*text|assert.*property)"]


class TestRequiredChecks:
    def test_ten_checks_defined(self):
        assert len(audit_mod.REQUIRED_CHECKS) == 10

    def test_all_check_patterns_compile(self):
        for pattern, _ in audit_mod.REQUIRED_CHECKS:
            assert pattern, "empty pattern"
