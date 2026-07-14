"""Tests for QML Hybrid Dependency Audit — verifies audit execution and zero blockers."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent

sys.path.insert(0, str(REPO))
from scripts.qml_hybrid_dependency_audit import run_audit, _find_sql_in_bridges  # noqa: E402
from scripts.qml_hybrid_dependency_audit import _find_qwidget_refs  # noqa: E402


@pytest.fixture(scope="module")
def audit_results():
    return run_audit()


def test_audit_returns_all_categories(audit_results):
    expected = {"REQUIRED_FALLBACK", "MIGRATION_PENDING", "UNSAFE_HYBRID",
                "DUPLICATED_LOGIC", "REMOVABLE"}
    assert set(audit_results) == expected


def test_no_unsafe_hybrid_sql_in_non_repo_bridges():
    items = _find_sql_in_bridges()
    bridge_files = {i["file"] for i in items}
    acceptable = {"ui_qml_bridge/library_doctor_bridge.py",
                  "ui_qml_bridge/library_query_service.py",
                   "ui_qml_bridge/diagnostics_bridge.py",
                   "ui_qml_bridge/diagnostics_repository.py",
                   "ui_qml_bridge/history_bridge.py",
                  "ui_qml_bridge/global_search_bridge.py",
                  "ui_qml_bridge/library_bridge.py"}
    unacceptable = bridge_files - acceptable
    assert len(unacceptable) == 0, f"SQL in non-repository bridges: {unacceptable}"


def test_no_ui_imports_in_bridges_except_service_loader(audit_results):
    acceptable = {"ui_qml_bridge/qml_main.py"}
    actual = {i["file"] for i in audit_results["REQUIRED_FALLBACK"]}
    unacceptable = actual - acceptable
    assert len(unacceptable) == 0, f"Bridges still reference ui.* modules: {unacceptable}"


def test_no_qwidget_or_dialog_refs_in_bridges():
    items = _find_qwidget_refs()
    assert len(items) == 0, f"QWidget/QDialog/QMainWindow/QFileDialog refs in bridges: {items}"


def test_audit_detects_sql_in_bridges():
    items = _find_sql_in_bridges()
    assert len(items) >= 5


def test_audit_detects_migration_pending(audit_results):
    assert len(audit_results["MIGRATION_PENDING"]) >= 10


def test_audit_detects_duplicated_logic(audit_results):
    assert len(audit_results["DUPLICATED_LOGIC"]) >= 1


def test_audit_detects_removable(audit_results):
    assert len(audit_results["REMOVABLE"]) >= 1


def test_audit_report_generates_json():
    from scripts.qml_hybrid_dependency_audit import main as audit_main
    from unittest.mock import patch
    with patch("sys.exit"):
        audit_main()
    report_path = REPO / "artifacts" / "hybrid_audit_results.json"
    assert report_path.exists()
    data = json.loads(report_path.read_text())
    assert "counts" in data
    assert "results" in data
