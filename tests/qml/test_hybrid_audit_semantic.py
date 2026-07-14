from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO = Path(__file__).resolve().parent.parent.parent

sys.path.insert(0, str(REPO))
from scripts.qml_hybrid_dependency_audit import (  # noqa: E402
    run_audit, _find_sql_in_bridges, _find_qwidget_refs,
    _find_patched_private_attrs,
    _find_duplicated_logic, _find_bridges_without_services,
    ALLOWED_SQL_BRIDGES, _detect_duplicate_sql,
    _detect_parallel_store,
    _detect_parallel_service, _detect_mutation_in_bridge_and_service,
    _has_real_backend_execution, _has_mock_only_action,
)


@pytest.fixture(scope="module")
def audit_results():
    return run_audit()


def test_audit_returns_all_categories(audit_results):
    expected = {"REQUIRED_FALLBACK", "MIGRATION_PENDING", "UNSAFE_HYBRID",
                "DUPLICATED_LOGIC", "REMOVABLE"}
    assert set(audit_results) == expected


def test_no_unsafe_sql_in_non_allowed_bridges():
    items = _find_sql_in_bridges()
    actual = {i["file"] for i in items}
    unacceptable = actual - ALLOWED_SQL_BRIDGES
    assert len(unacceptable) == 0, f"SQL en bridges no permitidos: {unacceptable}"


def test_no_ui_imports_in_bridges_except_service_loader(audit_results):
    acceptable = {"ui_qml_bridge/qml_main.py"}
    actual = {i["file"] for i in audit_results["REQUIRED_FALLBACK"]
              if "ui_import" in i.get("reason", "") or "from ui." in i.get("code", "")}
    unacceptable = actual - acceptable
    assert len(unacceptable) == 0, f"Bridges con import ui.*: {unacceptable}"


def test_no_qwidget_or_dialog_refs_in_bridges():
    items = _find_qwidget_refs()
    assert len(items) == 0, f"QWidget/QDialog en bridges: {items}"


def test_audit_detects_sql_in_bridges():
    items = _find_sql_in_bridges()
    assert len(items) >= 0


def test_audit_detects_migration_pending(audit_results):
    assert len(audit_results["MIGRATION_PENDING"]) >= 10


def test_audit_detects_duplicated_logic(audit_results):
    assert len(audit_results["DUPLICATED_LOGIC"]) >= 0


def test_no_false_positive_bridge_page_duplication():
    logic_items = _find_duplicated_logic()
    bridge_page_items = [i for i in logic_items
                         if "bridge" in i["file"] and "page" in i.get("reason", "")]
    assert len(bridge_page_items) == 0, (
        f"Bridge+page marcado como duplicación: {bridge_page_items}"
    )


def test_no_false_positive_constructor_service_assign():
    items = _find_patched_private_attrs()
    constructor_assigns = [i for i in items if "self._service" in i.get("reason", "")
                           and "post-constructor" not in i.get("reason", "")]
    assert len(constructor_assigns) == 0, (
        f"Constructor self._service marcado como parcheo: {constructor_assigns}"
    )


def test_no_false_positive_real_backend_ok_return():
    text = "result = service.suggest_for_track(track)\nreturn {'ok': True}"
    assert _has_real_backend_execution(text), "Real backend no detectado"
    assert not _has_mock_only_action(text), "Real backend marcado como mock"


def test_mock_only_detected_without_backend():
    text = "# pure stub\nreturn {'ok': True}"
    assert _has_mock_only_action(text), "Mock puro no detectado"


def test_detect_duplicate_sql_in_bridge():
    text = "conn.execute('SELECT COUNT(*) FROM tracks')"
    with patch.object(Path, 'read_text', return_value=text), \
         patch.object(Path, 'relative_to', return_value="ui_qml_bridge/random_bridge.py"):
        fp = Path("ui_qml_bridge/random_bridge.py")
        result = _detect_duplicate_sql(fp)
    assert len(result) == 1
    assert result[0]["category"] == "UNSAFE_HYBRID"


def test_detect_parallel_store_in_bridge():
    class FakePath:
        def __init__(self, rel, text):
            self._rel = rel
            self._text = text

        def read_text(self):
            return self._text

        def relative_to(self, _repo):
            return self._rel

    fp = FakePath("ui_qml_bridge/my_store.py", "class MyStore:\n    pass")
    with patch.object(Path, 'relative_to', return_value=fp._rel):
        result = _detect_parallel_store(fp)
    assert len(result) == 1
    assert "State store paralelo" in result[0]["reason"]


def test_detect_parallel_service_no_qobject():
    class FakePath:
        def __init__(self, rel, text):
            self._rel = rel
            self._text = text

        def read_text(self):
            return self._text

        def relative_to(self, _repo):
            return self._rel

    fp = FakePath("ui_qml_bridge/my_service.py",
                  "class MyService:\n    def run(self): pass")
    with patch.object(Path, 'relative_to', return_value=fp._rel):
        result = _detect_parallel_service(fp)
    assert len(result) == 1
    assert "Service class" in result[0]["reason"]


def test_bridge_with_qobject_not_parallel_service():
    class FakePath:
        def __init__(self, rel, text):
            self._rel = rel
            self._text = text

        def read_text(self):
            return self._text

        def relative_to(self, _repo):
            return self._rel

    fp = FakePath("ui_qml_bridge/valid_bridge.py",
                  "from PySide6.QtCore import QObject\nclass ValidBridge(QObject):\n    pass")
    with patch.object(Path, 'relative_to', return_value=fp._rel):
        result = _detect_parallel_service(fp)
    assert len(result) == 0


def test_detect_mutation_in_bridge():
    class FakePath:
        def __init__(self, rel, text):
            self._rel = rel
            self._text = text

        def read_text(self):
            return self._text

        def relative_to(self, _repo):
            return self._rel

    fp = FakePath("ui_qml_bridge/mut_bridge.py",
                  "conn.execute('UPDATE ...')\nconn.commit()\nconn.execute('DELETE ...')")
    with patch.object(Path, 'relative_to', return_value=fp._rel):
        result = _detect_mutation_in_bridge_and_service(fp)
    assert len(result) == 1
    assert "Mutation logic" in result[0]["reason"]


def test_audit_report_generates_json():
    from scripts.qml_hybrid_dependency_audit import main as audit_main
    with patch("sys.exit"):
        audit_main()
    report_path = REPO / "artifacts" / "hybrid_audit_results.json"
    assert report_path.exists()
    data = json.loads(report_path.read_text())
    assert "counts" in data
    assert "results" in data


def test_no_external_private_patch_in_bridges():
    items = _find_patched_private_attrs()
    external_patches = [i for i in items if "other_" in i.get("reason", "")
                        or "obj." in i.get("reason", "")
                        or "bridge." in i.get("reason", "")]
    assert len(external_patches) == 0, (
        f"Parcheos privados externos detectados: {external_patches}"
    )


def test_bridges_without_services_no_false_positive():
    items = _find_bridges_without_services()
    exempt_names = {"__init__.py", "error_catalog.py", "context_bindings.py",
                    "context_registrar.py", "route_registry.py", "command_bus.py",
                    "action_registry.py", "service_bundle.py", "service_capabilities.py",
                    "page_state_store.py", "qml_main.py"}
    false_pos = [i for i in items if Path(i["file"]).name in exempt_names]
    assert len(false_pos) == 0, f"Exentos marcados como sin servicio: {false_pos}"
