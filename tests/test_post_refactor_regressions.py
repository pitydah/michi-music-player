"""Anti-regression tests for post-refactor stabilisation.

Ensures that known regressions (private access re-introduction,
removal of CI runtime validation, premature RC versioning, etc.)
do not reappear. These tests are textual/static — they scan source
files for forbidden patterns.
"""

import os
import re


def _root():
    return os.path.join(os.path.dirname(__file__), "..")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


# ── 1. _quality_badge — no external private access ──


class TestQualityBadgeEncapsulation:
    """No access to ._quality_badge outside nowplaying_bar.py or settings."""

    def test_window_uses_public_signal(self):
        """window.py must connect to quality_details_requested, not _quality_badge."""
        content = _read(os.path.join(_root(), "ui", "window.py"))
        assert "._quality_badge" not in content, (
            "window.py must not access _quality_badge directly")

    def test_playback_controller_uses_facade(self):
        """playback_controller.py must use _player_bar_ctrl, not _quality_badge."""
        content = _read(os.path.join(_root(), "core", "playback_controller.py"))
        assert "._quality_badge" not in content, (
            "playback_controller.py must not access _quality_badge directly")
        assert "_player_bar_ctrl.set_route_tooltip" in content, (
            "playback_controller.py must use _player_bar_ctrl facade")

    def test_nowplaying_bar_has_public_signal(self):
        """NowPlayingBar must expose quality_details_requested signal."""
        content = _read(os.path.join(_root(), "ui", "nowplaying_bar.py"))
        assert "quality_details_requested = Signal()" in content

    def test_nowplaying_bar_has_set_route_tooltip(self):
        """NowPlayingBar must expose public set_route_tooltip method."""
        content = _read(os.path.join(_root(), "ui", "nowplaying_bar.py"))
        assert "def set_route_tooltip" in content

    def test_player_bar_controller_has_set_route_tooltip(self):
        """PlayerBarController must expose set_route_tooltip method."""
        content = _read(os.path.join(_root(), "ui", "controllers",
                                     "player_bar_controller.py"))
        assert "def set_route_tooltip" in content


# ── 2. Tray — no private access ──


class TestTrayEncapsulation:
    """TrayController must be created and accessed through public API."""

    def test_window_no_tray_private_icon(self):
        """window.py must not access _tray_ctrl._icon."""
        content = _read(os.path.join(_root(), "ui", "window.py"))
        assert "_tray_ctrl._icon" not in content

    def test_setup_tray_calls_setup(self):
        """_setup_tray must call .setup()."""
        content = _read(os.path.join(_root(), "ui", "window.py"))
        match = re.search(r"def _setup_tray\(self\):(.*?)(?=\n    def )", content, re.DOTALL)
        assert match is not None, "could not find _setup_tray method"
        body = match.group(1)
        assert ".setup()" in body, "_setup_tray must call .setup()"

    def test_notify_track_no_setup(self):
        """_notify_track must not call .setup()."""
        content = _read(os.path.join(_root(), "ui", "window.py"))
        match = re.search(r"def _notify_track\(self[^)]*\):(.*?)(?=\n    def )", content, re.DOTALL)
        if match:
            body = match.group(1)
            assert ".setup()" not in body, "_notify_track must not call .setup()"

    def test_tray_controller_has_icon_property(self):
        """TrayController must expose a public 'icon' property."""
        content = _read(os.path.join(_root(), "ui", "controllers",
                                     "tray_controller.py"))
        assert "def icon" in content or "icon = property" in content


# ── 3. GitHub Actions CI — runtime validation ──


class TestCIRuntimeValidation:
    """CI workflow must have a runtime job with GStreamer/smoke validation."""

    @staticmethod
    def _ci() -> str:
        return _read(os.path.join(_root(), ".github", "workflows", "ci.yml"))

    def test_has_system_site_packages(self):
        assert "--system-site-packages" in self._ci()

    def test_has_python3_gi(self):
        assert "python3-gi" in self._ci()

    def test_has_gir_gst(self):
        assert "gir1.2-gstreamer-1.0" in self._ci()

    def test_has_gir_gst_pbutils(self):
        assert "gir1.2-gst-plugins-base-1.0" in self._ci()

    def test_has_gi_require_gst(self):
        assert 'gi.require_version("Gst", "1.0")' in self._ci()

    def test_has_gi_require_gst_pbutils(self):
        assert 'gi.require_version("GstPbutils", "1.0")' in self._ci()

    def test_has_smoke_startup(self):
        assert "smoke_startup.py" in self._ci()

    def test_has_michi_test_data_dir(self):
        assert "MICHI_TEST_DATA_DIR" in self._ci()

    def test_has_michi_test_cache_dir(self):
        assert "MICHI_TEST_CACHE_DIR" in self._ci()

    def test_has_michi_test_config_dir(self):
        assert "MICHI_TEST_CONFIG_DIR" in self._ci()

    def test_has_michi_safe_mode(self):
        """CI runtime must set MICHI_SAFE_MODE."""
        assert "MICHI_SAFE_MODE" in self._ci()

    def test_smoke_startup_has_michi_safe_mode(self):
        """Smoke job in CI must set MICHI_SAFE_MODE."""
        ci = self._ci()
        smoke_section = ci.split("smoke_startup.py")[0]
        assert "MICHI_SAFE_MODE" in smoke_section

    def test_no_timeout_without_dependency(self):
        """If --timeout is in CI, pytest-timeout must be in pyproject.toml."""
        ci = self._ci()
        if "--timeout" in ci:
            pp = _read(os.path.join(_root(), "pyproject.toml"))
            assert "pytest-timeout" in pp or "pytest_timeout" in pp


# ── 4. Versioning — no premature RC ──


class TestVersioningHonesty:
    """Project must not declare RC/pre-release prematurely."""

    def test_no_rc1_in_pyproject(self):
        content = _read(os.path.join(_root(), "pyproject.toml"))
        assert "rc1" not in content, "pyproject.toml must not declare rc1"

    def test_release_notes_not_rc(self):
        content = _read(os.path.join(_root(), "RELEASE_NOTES.md"))
        assert "Release Candidate" not in content, (
            "RELEASE_NOTES.md must not declare Release Candidate")
        assert "Pre-release" in content or "draft" in content.lower()

    def test_create_release_has_ci_local_guard(self):
        content = _read(os.path.join(_root(), "scripts", "create_release.sh"))
        assert "ci_local.sh" in content, (
            "create_release.sh must invoke ci_local.sh before building")

    def test_estado_not_static_metrics(self):
        """ESTADO.md must not declare fixed test counts."""
        content = _read(os.path.join(_root(), "ESTADO.md"))
        lines = content.split("\n")
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("**Tests:**") or stripped.startswith("Tests:"):
                assert "ejecutados" in stripped or "verificar" in stripped.lower(), (
                    f"Static metric in ESTADO.md: {stripped}")

    def test_no_static_counts_in_markdown_tables(self):
        """Verify no markdown tables have hardcoded test/ruff counts as second-column values."""
        STATIC_METRIC_PATTERNS = [
            r"\|\s*Tests\s*\|\s*\d+\s*\|",
            r"\|\s*Ruff\s*\|\s*0\b",
            r"\*\*Tests:\*\*\s*\d+",
            r"Tests:\s*\d+",
            r"Ruff:\s*0\b",
            r"\d+\s+pasando",
        ]
        SAFE_WORDS = {"verificar", "pendiente", "ejecutar", "comando", "run", "dinámico"}
        docs = ["ESTADO.md", "RELEASE_NOTES.md", "README.md", "AGENTS.md"]
        for doc in docs:
            path = os.path.join(_root(), doc)
            if not os.path.exists(path):
                continue
            content = _read(path)
            for i, line in enumerate(content.split("\n"), 1):
                stripped = line.strip()
                # Skip lines with verifiable commands or safe words
                if any(w in stripped.lower() for w in SAFE_WORDS):
                    continue
                for pattern in STATIC_METRIC_PATTERNS:
                    if re.search(pattern, stripped):
                        raise AssertionError(
                            f"Static metric in {doc}:{i}: {stripped}")


# ── 5. Test isolation — no sys.modules contamination ──


class TestGIIsolation:
    """Player engine tests must not permanently contaminate sys.modules with fake gi."""

    def test_player_engine_no_direct_gi_assignment(self):
        """test_player_engine.py must not assign to sys.modules['gi'] directly."""
        path = os.path.join(_root(), "tests", "test_player_engine.py")
        content = _read(path)
        forbidden = [
            'sys.modules["gi"] =',
            'sys.modules["gi.repository"] =',
            'sys.modules["gi.repository.Gst"] =',
            'sys.modules["gi.repository.GLib"] =',
            'sys.modules["gi.repository.GstPbutils"] =',
        ]
        for pattern in forbidden:
            assert pattern not in content, (
                f"Direct sys.modules assignment forbidden: {pattern}")
        assert 'patch.dict("sys.modules"' in content, (
            "Must use patch.dict for sys.modules isolation")

    def test_create_release_compileall_excludes_venv_and_tmpl(self):
        """create_release.sh must exclude .venv/ and .tmpl in compileall."""
        path = os.path.join(_root(), "scripts", "create_release.sh")
        content = _read(path)
        assert "compileall -q -x" in content
        assert ".venv/" in content
        assert ".tmpl" in content
