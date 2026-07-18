"""Audit: verify services layer has zero Qt/PySide dependencies."""
from __future__ import annotations


def _check_no_qt(module_path: str) -> list[str]:
    """Check that a module file does not import QtWidgets/QtGui (QtCore/QtQml are OK)."""
    violations = []
    with open(module_path) as f:
        for i, line in enumerate(f, 1):
            stripped = line.strip()
            if stripped.startswith("#") or stripped == "":
                continue
            if "PySide6.QtWidgets" in stripped or "PyQt6.QtWidgets" in stripped:
                violations.append(f"  Line {i}: {stripped}")
            if "from PySide6.QtGui" in stripped or "import PySide6.QtGui" in stripped:
                violations.append(f"  Line {i}: {stripped}")
    return violations


def _check_no_window_py(module_path: str) -> list[str]:
    violations = []
    with open(module_path) as f:
        for i, line in enumerate(f, 1):
            if "window.py" in line or "MainWindow" in line:
                violations.append(f"  Line {i}: {line.strip()}")
    return violations


class TestServicesNoQt:
    def test_all_service_files_have_no_qt(self):
        import os
        base = os.path.join(os.path.dirname(__file__),
                           "..", "..", "integrations", "michi_link", "services")
        base = os.path.normpath(base)
        total_violations = []
        for fname in sorted(os.listdir(base)):
            if not fname.endswith(".py"):
                continue
            path = os.path.join(base, fname)
            v = _check_no_qt(path)
            if v:
                total_violations.append(f"\n{fname}:")
                total_violations.extend(v)
        assert not total_violations, "Qt violations found:\n" + "\n".join(total_violations)

    def test_all_service_files_have_no_window_py(self):
        import os
        base = os.path.join(os.path.dirname(__file__),
                           "..", "..", "integrations", "michi_link", "services")
        base = os.path.normpath(base)
        total_violations = []
        for fname in sorted(os.listdir(base)):
            if not fname.endswith(".py"):
                continue
            path = os.path.join(base, fname)
            v = _check_no_window_py(path)
            if v:
                total_violations.append(f"\n{fname}:")
                total_violations.extend(v)
        assert not total_violations, "window.py references found:\n" + "\n".join(total_violations)

    def test_all_service_files_return_result(self):
        import os
        base = os.path.join(os.path.dirname(__file__),
                           "..", "..", "integrations", "michi_link", "services")
        base = os.path.normpath(base)
        exceptions = {"result.py", "__init__.py", "diagnostics_service.py",
                       "compatibility_report.py", "album_import_worker.py"}
        for fname in sorted(os.listdir(base)):
            if not fname.endswith(".py") or fname in exceptions:
                continue
            path = os.path.join(base, fname)
            with open(path) as f:
                content = f.read()
            assert "from integrations.michi_link.services.result import Result" in content or \
                   "from integrations.michi_link.services import Result" in content or \
                   "from .result import Result" in content, \
                   f"{fname} does not import Result"

    def test_result_has_expected_fields(self):
        from integrations.michi_link.services.result import Result
        r = Result.success({"key": "val"}, "it works")
        assert r.ok is True
        assert r.code == "OK"
        assert r.message == "it works"
        assert r.data == {"key": "val"}
        assert r.error is None

        r2 = Result.fail("ERR_CODE", "something went wrong")
        assert r2.ok is False
        assert r2.code == "ERR_CODE"
        assert r2.message == "something went wrong"
        assert r2.error == "something went wrong"

        d = r2.to_dict()
        assert d["code"] == "ERR_CODE"
        assert d["ok"] is False
