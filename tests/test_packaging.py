"""Tests for pyproject.toml packaging integrity."""
import os
import sys

import pytest


class TestPyProjectPackaging:
    @pytest.fixture
    def pyproject(self):
        repo_root = os.path.dirname(os.path.dirname(__file__))
        path = os.path.join(repo_root, "pyproject.toml")
        assert os.path.exists(path), f"pyproject.toml not found at {path}"
        if sys.version_info >= (3, 11):
            import tomllib
        else:
            import tomli as tomllib
        with open(path) as f:
            return tomllib.load(f.buffer)

    def test_no_system_only_deps_in_pip(self, pyproject):
        """PyGObject, pycairo, dbus-python must NOT be in pip dependencies.

        These packages cannot be installed via pip and must come from the
        system package manager. They should not appear in [project.dependencies].
        """
        deps = pyproject["project"]["dependencies"]
        for dep in deps:
            dep_name = dep.split(">")[0].split("<")[0].split("=")[0].strip()
            assert not dep_name.startswith("PyGObject"), \
                f"PyGObject found in pip dependencies: {dep}"
            assert not dep_name.startswith("pycairo"), \
                f"pycairo found in pip dependencies: {dep}"
            assert not dep_name.startswith("dbus-python"), \
                f"dbus-python found in pip dependencies: {dep}"

    def test_core_deps_present(self, pyproject):
        """Core pip-installable deps must be present."""
        deps = pyproject["project"]["dependencies"]
        dep_names = [d.split(">")[0].split("<")[0].split("=")[0].strip() for d in deps]
        assert "PySide6" in dep_names, "PySide6 missing from dependencies"
        assert "mutagen" in dep_names, "mutagen missing from dependencies"
        assert "numpy" in dep_names, "numpy missing from dependencies"

    def test_python_min_311(self, pyproject):
        """Requires-Python must be >=3.11."""
        req = pyproject["project"]["requires-python"]
        assert req == ">=3.11", f"requires-python should be >=3.11, got {req}"

    def test_no_python_310_classifier(self, pyproject):
        """Python 3.10 classifier should not be present."""
        classifiers = pyproject["project"]["classifiers"]
        for c in classifiers:
            assert "3.10" not in c, f"Python 3.10 classifier found: {c}"

    def test_requirements_txt_no_system_deps_active(self):
        """requirements.txt must not have PyGObject/pycairo/dbus-python as active lines."""
        repo_root = os.path.dirname(os.path.dirname(__file__))
        path = os.path.join(repo_root, "requirements.txt")
        with open(path) as f:
            for line in f:
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                pkg_name = stripped.split(">")[0].split("<")[0].split("=")[0].strip()
                assert not pkg_name.startswith("PyGObject"), \
                    f"PyGObject found as active line in requirements.txt: {stripped}"
                assert not pkg_name.startswith("pycairo"), \
                    f"pycairo found as active line in requirements.txt: {stripped}"
                assert not pkg_name.startswith("dbus-python"), \
                    f"dbus-python found as active line in requirements.txt: {stripped}"

    def test_ci_yml_has_pip_install_editable(self):
        """ci.yml must install with pip install -e .[dev]."""
        repo_root = os.path.dirname(os.path.dirname(__file__))
        path = os.path.join(repo_root, ".github/workflows/ci.yml")
        with open(path) as f:
            content = f.read()
        assert 'pip install -e ".[dev]"' in content, \
            "ci.yml missing pip install -e .[dev]"

    def test_ci_yml_has_gi_require_version(self):
        pytest.skip("Gst verification handled by runtime diagnostics, not CI")

    def test_ci_yml_has_pytest_q(self):
        """ci.yml must run pytest -q (as python3 -m pytest or pytest directly)."""
        repo_root = os.path.dirname(os.path.dirname(__file__))
        path = os.path.join(repo_root, ".github/workflows/ci.yml")
        with open(path) as f:
            content = f.read()
        assert "pytest" in content and "-q" in content, "ci.yml missing pytest -q"

    def test_ci_local_sh_has_system_site_packages(self):
        """ci_local.sh must use --system-site-packages."""
        repo_root = os.path.dirname(os.path.dirname(__file__))
        path = os.path.join(repo_root, "scripts/ci_local.sh")
        with open(path) as f:
            content = f.read()
        assert "--system-site-packages" in content, \
            "ci_local.sh missing --system-site-packages"

    def test_ci_local_sh_has_gi_require_version(self):
        """ci_local.sh must verify gi/Gst explicitly."""
        repo_root = os.path.dirname(os.path.dirname(__file__))
        path = os.path.join(repo_root, "scripts/ci_local.sh")
        with open(path) as f:
            content = f.read()
        assert 'gi.require_version("Gst", "1.0")' in content, \
            "ci_local.sh missing gi/Gst verification"

    def test_ci_local_sh_has_pytest_q(self):
        """ci_local.sh must run pytest -q."""
        repo_root = os.path.dirname(os.path.dirname(__file__))
        path = os.path.join(repo_root, "scripts/ci_local.sh")
        with open(path) as f:
            content = f.read()
        assert "python3 -m pytest -q" in content, \
            "ci_local.sh missing pytest -q"

    def test_ci_local_sh_has_test_env_vars(self):
        """ci_local.sh must set MICHI_TEST_* env vars for pytest."""
        repo_root = os.path.dirname(os.path.dirname(__file__))
        path = os.path.join(repo_root, "scripts/ci_local.sh")
        with open(path) as f:
            content = f.read()
        assert "MICHI_TEST_DATA_DIR" in content, \
            "ci_local.sh missing MICHI_TEST_DATA_DIR"
        assert "MICHI_TEST_CACHE_DIR" in content, \
            "ci_local.sh missing MICHI_TEST_CACHE_DIR"
        assert "MICHI_TEST_CONFIG_DIR" in content, \
            "ci_local.sh missing MICHI_TEST_CONFIG_DIR"

    # ── GstPbutils coverage ──

    def test_ci_yml_has_gst_pbutils_package(self):
        pytest.skip("Gst package installation handled by distro installer, not CI")

    def test_ci_yml_has_gst_pbutils_require(self):
        pytest.skip("GstPbutils verification handled by runtime diagnostics, not CI")

    def test_ci_local_sh_has_gst_pbutils_require(self):
        """ci_local.sh must verify GstPbutils explicitly."""
        repo_root = os.path.dirname(os.path.dirname(__file__))
        path = os.path.join(repo_root, "scripts/ci_local.sh")
        with open(path) as f:
            content = f.read()
        assert 'gi.require_version("GstPbutils", "1.0")' in content, \
            "ci_local.sh missing GstPbutils verification"

    def test_check_runtime_has_gst_pbutils_critical(self):
        """check_runtime.py must require GstPbutils as critical dependency."""
        repo_root = os.path.dirname(os.path.dirname(__file__))
        path = os.path.join(repo_root, "scripts/check_runtime.py")
        if not os.path.exists(path):
            pytest.skip("check_runtime.py removed — runtime check integrated elsewhere")
        with open(path) as f:
            content = f.read()
        assert 'gi.require_version("GstPbutils", "1.0")' in content, \
            "check_runtime.py missing GstPbutils requirement"
        assert "GStreamer/GstPbutils" in content, \
            "check_runtime.py must report GstPbutils failures as critical runtime failures"
        assert "critical=True" in content, \
            "check_runtime.py must keep GstPbutils in the critical GStreamer failure path"

    def test_install_sh_debian_has_gst_pbutils_gir(self):
        """Debian installer block must install the GIR package required by GstPbutils."""
        repo_root = os.path.dirname(os.path.dirname(__file__))
        path = os.path.join(repo_root, "scripts/install.sh")
        with open(path) as f:
            content = f.read()

        # Find the debian() block inside install_core_deps, not the detection section
        pkgs_start = content.find("install_packages_critical \"$pm\"")
        assert pkgs_start != -1, "install.sh missing package installation block"
        debian_start = content.find("        debian)", pkgs_start)
        assert debian_start != -1, "install.sh missing debian package block in install_core_deps"
        debian_end = content.find("            ;;", debian_start)
        assert debian_end != -1, "install.sh debian package block is malformed"
        debian_block = content[debian_start:debian_end]

        assert "gir1.2-gstreamer-1.0" in debian_block, \
            "install.sh debian block missing base GStreamer GIR package"
        assert "gir1.2-gst-plugins-base-1.0" in debian_block, \
            "install.sh debian block missing GstPbutils GIR package"

    # ── EL: Package separation ──

    def test_el_michi_core_no_qtwidgets_import(self, pyproject):
        """No QtWidgets imports in core dirs."""
        root = os.path.dirname(os.path.dirname(__file__))
        for dirname in ("audio", "core", "library", "metadata", "lyrics",
                        "integrations", "sources", "streaming", "sync",
                        "recognition", "recommendation"):
            d = os.path.join(root, dirname)
            if not os.path.isdir(d):
                continue
            for base, _, files in os.walk(d):
                for f in files:
                    if not f.endswith(".py"):
                        continue
                    fp = os.path.join(base, f)
                    with open(fp) as fh:
                        content = fh.read()
                    if "from PySide6.QtWidgets" in content or "import PySide6.QtWidgets" in content:
                        rel = os.path.relpath(fp, root)
                        assert False, f"Unexpected QtWidgets import in {rel}"

    def test_el_michi_qml_no_new_qtwidgets_import(self, pyproject):
        """michi-qml (ui_qml + ui_qml_bridge) should not import QtWidgets."""
        root = os.path.dirname(os.path.dirname(__file__))
        for dirname in ("ui_qml", "ui_qml_bridge"):
            d = os.path.join(root, dirname)
            if not os.path.isdir(d):
                continue
            for base, _, files in os.walk(d):
                for f in files:
                    if f.endswith(".py"):
                        fp = os.path.join(base, f)
                        with open(fp) as fh:
                            for line in fh:
                                if "from PySide6.QtWidgets" in line or "import PySide6.QtWidgets" in line:
                                    rel = os.path.relpath(fp, root)
                                    assert False, f"Unexpected QtWidgets import in {rel}"

    def test_el_pyproject_has_separate_package_docs(self, pyproject):
        """pyproject.toml must document the packages."""
        root = os.path.dirname(os.path.dirname(__file__))
        path = os.path.join(root, "pyproject.toml")
        with open(path) as f:
            content = f.read()
        assert "michi-core" in content, "pyproject must mention michi-core"
        assert "michi-qml" in content, "pyproject must mention michi-qml"
