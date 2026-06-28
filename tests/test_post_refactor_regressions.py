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


# ── 7. Hardening — watcher, DB encapsulation, safe mode local, backfill ──


class TestHardening:
    """Anti-regression tests for structural hardening."""

    def test_file_watcher_uses_remove_paths(self):
        """FileWatcher must use removePaths, not directories().clear()."""
        content = _read(os.path.join(_root(), "library", "file_watcher.py"))
        assert "removePaths" in content, "FileWatcher must use removePaths"
        assert "directories().clear()" not in content, (
            "directories().clear() is unreliable")

    def test_ci_local_uses_michi_safe_mode(self):
        """ci_local.sh must set MICHI_SAFE_MODE=1 for both smoke and pytest."""
        content = _read(os.path.join(_root(), "scripts", "ci_local.sh"))
        assert content.count("MICHI_SAFE_MODE=1") >= 2, (
            "ci_local.sh must set MICHI_SAFE_MODE=1 for both smoke_startup and pytest")
        smoke_section = content.split("python3 scripts/smoke_startup.py")[0]
        pytest_section = content.split("python3 -m pytest")[0]
        assert "MICHI_SAFE_MODE=1" in smoke_section, "smoke startup missing safe mode"
        assert "MICHI_SAFE_MODE=1" in pytest_section, "pytest missing safe mode"

    def test_backfill_scheduled_only_by_library_controller(self):
        """Backfill must be scheduled in LibraryController, not window.py."""
        window = _read(os.path.join(_root(), "ui", "window.py"))
        lib_ctrl = _read(os.path.join(_root(), "ui", "controllers",
                                      "library_controller.py"))
        assert "backfill_missing_metadata" not in window, (
            "window.py must not schedule backfill_missing_metadata")
        assert "backfill_missing_album_art" not in window, (
            "window.py must not schedule backfill_missing_album_art")
        assert "backfill_missing_metadata" in lib_ctrl, (
            "LibraryController must schedule backfill_missing_metadata")
        assert "backfill_missing_album_art" in lib_ctrl, (
            "LibraryController must schedule backfill_missing_album_art")

    def test_indexer_does_not_call_global_remove_missing(self):
        """Indexer must not call global remove_missing()."""
        content = _read(os.path.join(_root(), "library", "indexer.py"))
        assert "remove_missing()" not in content, (
            "Indexer must not call global remove_missing()")

    def test_no_external_librarydb_private_conn(self):
        """External modules must not access LibraryDB._conn directly."""
        import glob
        forbidden_patterns = ["self._db._conn", "db._conn", "_db._conn"]
        allowed_prefixes = (
            "library/library_db.py",
            "tests/conftest.py",
            "tests/test_",
            "tools/",
        )
        errors = []
        for path in glob.glob("**/*.py", root_dir=_root(), recursive=True):
            if path.startswith(allowed_prefixes):
                continue
            if ".venv/" in path or "build/" in path or "__pycache__" in path:
                continue
            full = os.path.join(_root(), path)
            if not os.path.isfile(full):
                continue
            content = _read(full)
            for pattern in forbidden_patterns:
                if pattern in content:
                    errors.append(f"{path}: contains {pattern}")
        assert not errors, "Private _conn access detected:\n" + "\n".join(errors)

    def test_cleanup_missing_under_unavailable_root_returns_zero(self, tmp_path):
        """cleanup_missing_under_root must return 0 for non-existent root."""
        from library.library_db import LibraryDB
        db_path = str(tmp_path / "lib.db")
        db = LibraryDB(db_path)
        try:
            missing_root = str(tmp_path / "offline")
            result = db.cleanup_missing_under_root(missing_root)
            assert result == 0, (
                f"Expected 0 for unavailable root, got {result}")
        finally:
            db.close()

    def test_library_db_no_silent_critical_passes(self):
        """library_db.py must not silently swallow critical errors."""
        content = _read(os.path.join(_root(), "library", "library_db.py"))
        forbidden = [
            "except sqlite3.Error:\n            pass",
            "except Exception:\n                pass",
            "except Exception:\n            pass",
        ]
        for pattern in forbidden:
            assert pattern not in content, (
                f"library_db.py must not silently swallow: {pattern!r}")

    def test_library_db_logs_degradable_errors(self):
        """library_db.py must log FTS5 and embedded cover errors."""
        content = _read(os.path.join(_root(), "library", "library_db.py"))
        assert "FTS5" in content, "library_db.py should log FTS5 errors"
        assert "Failed to cache embedded cover" in content, (
            "library_db.py should log embedded cover cache failures")

    def test_action_log_no_silent_exceptions(self):
        """ActionLog must not silently swallow exceptions in get_recent/total_actions."""
        content = _read(os.path.join(_root(), "integrations", "ai_assistant",
                                     "action_log.py"))
        assert "except Exception:\n            return []" not in content, (
            "get_recent() must log before returning []")
        assert "except Exception:\n            return 0" not in content, (
            "total_actions() must log before returning 0")
        assert "get_recent failed" in content, (
            "get_recent() must have logger.debug for errors")
        assert "total_actions failed" in content, (
            "total_actions() must have logger.debug for errors")


class TestMicroStability:
    """Micro-stability: HomePage, smoke labels, noise overlay."""

    def test_home_page_does_not_silently_swallow_stats_errors(self):
        content = _read(os.path.join(_root(), "ui", "hubs", "home_page.py"))
        assert "except Exception:\n            pass" not in content
        assert "Home stats unavailable" in content

    def test_smoke_startup_step_labels_are_consistent(self):
        content = _read(os.path.join(_root(), "scripts", "smoke_startup.py"))
        assert "[1/7] Environment" in content
        assert "[7/7] Summary" in content
        assert "[1/8]" not in content
        assert "[8/8]" not in content

    def test_noise_overlay_uses_cached_tiled_texture(self):
        content = _read(os.path.join(_root(), "ui", "effects", "michi_glass.py"))
        assert "drawTiledPixmap" in content
        assert "_NOISE_TILE_CACHE" in content
        assert "for y in range(h)" not in content
        assert "for x in range(w)" not in content


class TestRouteSidebarSeparation:
    """Route/sidebar state separation must be maintained."""

    def test_window_has_route_key(self):
        content = _read(os.path.join(_root(), "ui", "window.py"))
        assert "_current_route_key: str = " in content

    def test_window_has_sidebar_key(self):
        content = _read(os.path.join(_root(), "ui", "window.py"))
        assert "_current_sidebar_key: str = " in content

    def test_nav_configure_header_sets_route_and_sidebar(self):
        content = _read(os.path.join(_root(), "ui", "controllers",
                                     "navigation_controller.py"))
        assert "w._current_route_key = " in content
        assert "w._current_sidebar_key = " in content
        assert "resolve_sidebar_active_key" in content

    def test_dispatch_passes_route_key_to_configure_header(self):
        content = _read(os.path.join(_root(), "ui", "controllers",
                                     "navigation_controller.py"))
        assert "self.configure_header(section_key, route_key=key)" in content

    def test_smoke_ui_route_asserts_route_and_sidebar(self):
        content = _read(os.path.join(_root(), "scripts", "smoke_ui_routes.py"))
        assert "_current_route_key" in content
        assert "_current_sidebar_key" in content


class TestCiLocalNumbering:
    """ci_local.sh must have consistent [1/10]-[10/10] labels."""

    def test_ci_local_labels_are_1_to_10(self):
        content = _read(os.path.join(_root(), "scripts", "ci_local.sh"))
        for i in range(1, 11):
            assert f"[{i}/10]" in content, f"Missing label [{i}/10]"
        assert "[1/8]" not in content
        assert "[9/9]" not in content

    def test_ci_local_michi_safe_mode_count(self):
        content = _read(os.path.join(_root(), "scripts", "ci_local.sh"))
        assert content.count("MICHI_SAFE_MODE=1") >= 2

    def test_ci_local_has_both_smoke_scripts(self):
        content = _read(os.path.join(_root(), "scripts", "ci_local.sh"))
        assert "scripts/smoke_startup.py" in content
        assert "scripts/smoke_ui_routes.py" in content

    def test_ci_local_runs_ruff_check(self):
        content = _read(os.path.join(_root(), "scripts", "ci_local.sh"))
        assert "python3 -m ruff check ." in content, (
            "ci_local.sh must run ruff check, not only print lint OK")


class TestSmokeStartupIsRuntimeBase:
    """smoke_startup.py must not contain deep UI smoke."""

    def test_smoke_startup_is_runtime_base_only(self):
        content = _read(os.path.join(_root(), "scripts", "smoke_startup.py"))
        forbidden = [
            "from ui.window import MainWindow",
            "_check_main_window",
            "w._nav_ctrl.dispatch",
            "sections = [",
            "_view_router.on_mode_changed",
        ]
        for pattern in forbidden:
            assert pattern not in content, (
                f"smoke_startup.py must not contain deep UI smoke: {pattern}")


class TestSmokeUiRoutesHardening:
    """smoke_ui_routes.py must close MainWindow in finally and enforce route/sidebar."""

    def test_smoke_ui_routes_closes_mainwindow_in_finally(self):
        content = _read(os.path.join(_root(), "scripts", "smoke_ui_routes.py"))
        assert "finally:" in content
        assert "w.close()" in content
        assert "w.deleteLater()" in content
        assert "app.quit()" in content
        assert "_os._exit(0)" in content

    def test_smoke_ui_route_sidebar_is_mandatory(self):
        content = _read(os.path.join(_root(), "scripts", "smoke_ui_routes.py"))
        assert "route/sidebar attributes not yet" not in content
        assert "hasattr(w, '_current_route_key')" not in content
        assert "hasattr(w, '_current_sidebar_key')" not in content
        assert 'assert w._current_route_key == "pl:123"' in content
        assert 'assert w._current_sidebar_key == "playlist_hub"' in content
        assert 'resolve_sidebar_active_key("srv:navidrome") == "connections_hub"' in content
        assert 'resolve_sidebar_active_key("dev:usb") == "devices_page"' in content

    def test_smoke_ui_asserts_route_and_sidebar(self):
        content = _read(os.path.join(_root(), "scripts", "smoke_ui_routes.py"))
        assert "_current_route_key" in content
        assert "_current_sidebar_key" in content


class TestRebuildSidebarUsesCurrentSidebarKey:
    """_rebuild_sidebar() must use _current_sidebar_key as primary source."""

    def test_rebuild_sidebar_uses_current_sidebar_key(self):
        content = _read(os.path.join(_root(), "ui", "window.py"))
        marker = "def _rebuild_sidebar"
        assert marker in content
        section = content.split(marker, 1)[1].split("\n    def ", 1)[0]
        assert "_current_sidebar_key" in section
        assert 'resolve_sidebar_active_key(getattr(self, "_current_route_key", "home"))' in section


class TestBackfillGuard:
    """Backfill must be guarded by both safe mode and settings."""

    def test_load_guards_by_safe_mode(self):
        content = _read(os.path.join(_root(), "ui", "controllers",
                                     "library_controller.py"))
        assert "_safe_mode" in content, (
            "LibraryController.load() must check safe mode before backfill")

    def test_load_guards_by_setting(self):
        content = _read(os.path.join(_root(), "ui", "controllers",
                                     "library_controller.py"))
        assert "get_bool" in content, (
            "LibraryController.load() must check get_bool setting")
        assert "auto_backfill_enabled" in content, (
            "LibraryController.load() must check auto_backfill_enabled setting")
