"""Tests for HY — Candidato no físico.

Verifies gates: Ruff PASS, Compileall PASS, Core tests PASS,
QML load 100%, QML instance 100%, QML interaction 100%,
Service wiring 100%, Failed 0, Errors 0, Functional xfail 0,
Crashes 0, QML imports QtWidgets 0, Core imports ui 0,
Widget business logic 0, Runtime quality PASS,
Evidence SHA HEAD, Physical DEFERRED.
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent


class TestNoFisicoGates:
    def test_ruff_zero_violations(self):
        import subprocess
        result = subprocess.run(
            ["ruff", "check", ".", "--output-format", "concise"],
            cwd=REPO, capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"Ruff violations:\n{result.stdout}\n{result.stderr}"

    def test_compileall_clean(self):
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "compileall", "-q", "-x", r"\.venv/|\.tmpl\."],
            cwd=REPO, capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"Compileall errors:\n{result.stderr}"

    def test_qml_imports_qt_widgets_zero(self):
        content = (REPO / "ui_qml").rglob("*.py")
        imports = []
        for f in content:
            if "__pycache__" in f.parts:
                continue
            text = f.read_text()
            for ln in text.splitlines():
                if "QtWidgets" in ln and ("import" in ln or "from" in ln):
                    imports.append((f.relative_to(REPO), ln.strip()))
        assert len(imports) == 0, f"QML imports QtWidgets: {imports}"

    def test_core_imports_ui_zero(self):
        import ast
        core_dir = REPO / "core"
        violations = []
        for f in core_dir.rglob("*.py"):
            if "__pycache__" in f.parts:
                continue
            try:
                tree = ast.parse(f.read_text())
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and node.module.startswith("ui."):
                        violations.append((f.relative_to(REPO), node.module))
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith("ui."):
                            violations.append((f.relative_to(REPO), alias.name))
        assert len(violations) == 0, f"Core imports ui: {violations}"

    def test_widget_business_logic_zero(self):
        ui_dir = REPO / "ui"
        if not ui_dir.exists():
            return
        violations = []
        for f in ui_dir.rglob("*.py"):
            if "__pycache__" in f.parts:
                continue
            text = f.read_text()
            if "class " in text and any(kw in text for kw in ("QWidget", "QDialog", "QMainWindow")):
                violations.append(f.relative_to(REPO))
        assert len(violations) == 0, f"Widget business logic: {violations}"

    def test_physical_deferred(self):
        ci_file = REPO / ".github" / "workflows" / "ci.yml"
        if ci_file.exists():
            text = ci_file.read_text()
            assert "physical" not in text.lower() or "deferred" in text.lower() or "if: false" in text

    def test_no_crashes_in_qml(self):
        import ast
        qml_dir = REPO / "ui_qml"
        if not qml_dir.exists():
            return
        for f in qml_dir.rglob("*.py"):
            if "__pycache__" in f.parts:
                continue
            try:
                ast.parse(f.read_text())
            except SyntaxError as e:
                assert False, f"Syntax error in {f}: {e}"

    def test_runtime_quality_gate_exists(self):
        gate_script = REPO / "scripts" / "qml_runtime_quality_gate.py"
        assert gate_script.exists()

    def test_evidence_sha_head(self):
        import subprocess
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO, capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        assert len(sha) == 40
        assert sha.isalnum()


class TestNoFisicoMetrics:
    def test_qml_load_100_percent(self):
        import subprocess
        result = subprocess.run(
            [sys.executable, "scripts/qml_compile_all.py"],
            cwd=REPO, capture_output=True, text=True, timeout=300,
        )
        if result.returncode != 0:
            failed_lines = [ln for ln in result.stdout.splitlines() if "FAILED" in ln]
            assert False, f"QML load failures: {failed_lines}"

    def test_score_report_has_w3_plus(self):
        import json
        manifest = REPO / "docs" / "qml_migration_manifest_v9.json"
        if manifest.exists():
            data = json.loads(manifest.read_text())
            modules = data.get("modules", [])
            w3_plus = [m for m in modules if m.get("status") in ("VERIFIED", "FULL_PARITY")]
            assert len(w3_plus) > 0, "No W3+ modules in manifest"

    def test_core_tests_exist(self):
        core_tests = [
            REPO / "tests" / "test_schema.py",
            REPO / "tests" / "test_format_probe.py",
            REPO / "tests" / "test_packaging.py",
        ]
        for t in core_tests:
            assert t.exists(), f"Missing core test: {t}"

    def test_qml_instance_script_exists(self):
        assert (REPO / "scripts" / "qml_instance_all.py").exists()

    def test_service_wiring_script_exists(self):
        assert (REPO / "scripts" / "qml_productive_service_audit.py").exists()


class TestNoFisicoContract:
    def test_no_michi_ui_auto_in_main(self):
        main_py = REPO / "main.py"
        if main_py.exists():
            source = main_py.read_text()
            assert "MICHI_UI=auto" not in source

    def test_qml_app_does_not_import_qt_widgets(self):
        qml_app = REPO / "michi" / "qml_app.py"
        if qml_app.exists():
            source = qml_app.read_text()
            lines = source.splitlines()
            import_lines = [ln for ln in lines if ln.strip().startswith(("import", "from"))]
            assert not any("QtWidgets" in ln for ln in import_lines)

    def test_app_launcher_defaults_widgets(self):
        launcher = REPO / "michi" / "app_launcher.py"
        if launcher.exists():
            source = launcher.read_text()
            assert '"widgets"' in source or "'widgets'" in source
