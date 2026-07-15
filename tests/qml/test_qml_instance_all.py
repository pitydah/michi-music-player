from __future__ import annotations
"""Tests for qml_instance_all.py — verifica carga, instancia e interacción."""

import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["MICHI_SAFE_MODE"] = "1"

from pathlib import Path
import sys as _sys
import pytest

REPO = Path(__file__).resolve().parent.parent.parent
_sys.path.insert(0, str(REPO))


SCRIPTS = REPO / "scripts"
QML_DIR = Path(__file__).resolve().parent.parent.parent / "ui_qml"


@pytest.fixture(scope="module")
def instance_results():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "qml_instance_all", SCRIPTS / "qml_instance_all.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.run()


class TestQmlInstanceAll:
    def test_all_qml_files_loaded(self, instance_results):
        s = instance_results["summary"]
        assert s["loaded"] == s["total"], (
            f"Not all loaded: {s['loaded']}/{s['total']}"
        )

    def test_zero_reference_errors(self, instance_results):
        assert not instance_results["summary"]["has_reference_errors"]

    def test_zero_type_errors(self, instance_results):
        assert not instance_results["summary"]["has_type_errors"]

    def test_all_files_instanced(self, instance_results):
        assert instance_results["summary"]["instanced"] == instance_results["summary"]["total"], (
            f"Instance: {instance_results['summary']['instanced']}/{instance_results['summary']['total']}"
        )

    def test_instance_rate_reported(self, instance_results):
        s = instance_results["summary"]
        rate = s["instanced"] / max(1, s["total"]) * 100
        assert rate > 0, "Instance rate should be > 0%"

    def test_no_critical_errors(self, instance_results):
        assert instance_results["summary"]["error_count"] == 0, (
            f"Errors: {instance_results['summary']['error_count']}"
        )

    def test_all_qml_files_exist(self, instance_results):
        qml_files = sorted(QML_DIR.rglob("*.qml"))
        assert len(qml_files) > 0, "No QML files found"
        assert instance_results["summary"]["total"] == len(qml_files), (
            f"File count mismatch: {instance_results['summary']['total']} vs {len(qml_files)}"
        )

    def test_binding_loops_reported(self, instance_results):
        assert isinstance(instance_results["summary"]["binding_loops"], int)
