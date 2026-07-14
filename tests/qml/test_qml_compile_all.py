"""Tests for qml_compile_all.py — verifies 0 errors in QML compilation."""
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent.parent / "scripts"
QML_DIR = Path(__file__).resolve().parent.parent.parent / "ui_qml"


def _load_results():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "qml_compile_all", SCRIPTS / "qml_compile_all.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.run()


def _load_results():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "qml_compile_all", SCRIPTS / "qml_compile_all.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.run()


@pytest.fixture(scope="module")
def results(qapp):
    return _load_results()


class TestQmlCompileAll:
    def test_all_qml_files_loaded(self, results):
        assert results["loaded"] == results["total"], (
            f"Not all QML files loaded: {results['loaded']}/{results['total']}"
        )

    def test_zero_errors(self, results):
        assert results["summary"]["error_count"] == 0, (
            f"Found {results['summary']['error_count']} errors"
        )

    def test_no_reference_errors(self, results):
        ref_errors = [
            e for e in results["errors"]
            if "ReferenceError" in e["categories"]
        ]
        assert len(ref_errors) == 0, (
            f"ReferenceError(s) found: {len(ref_errors)}"
        )

    def test_no_type_errors(self, results):
        type_errors = [
            e for e in results["errors"]
            if "TypeError" in e["categories"]
        ]
        assert len(type_errors) == 0, (
            f"TypeError(s) found: {len(type_errors)}"
        )

    def test_all_qml_files_exist(self, results):
        qml_files = sorted(QML_DIR.rglob("*.qml"))
        assert len(qml_files) > 0, "No QML files found"
        assert results["total"] == len(qml_files), (
            f"File count mismatch: {results['total']} vs {len(qml_files)}"
        )
