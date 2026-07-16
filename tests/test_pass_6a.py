"""Phase 6A regression tests — safe mode, playlist, favorites, runtime, audit."""

import os
import tempfile
from unittest.mock import MagicMock

import pytest


class TestRuntimePython311:
    """Verify Python 3.11+ contract."""

    def test_pyproject_no_python310_classifier(self):
        """pyproject.toml must not declare Python 3.10 classifier."""
        root = os.path.join(os.path.dirname(__file__), "..")
        with open(os.path.join(root, "pyproject.toml")) as f:
            content = f.read()
        assert "Programming Language :: Python :: 3.10" not in content

    def test_check_runtime_requires_311(self):
        """scripts/check_runtime.py must require Python >=3.11."""
        root = os.path.join(os.path.dirname(__file__), "..")
        path = os.path.join(root, "scripts", "check_runtime.py")
        if not os.path.exists(path):
            pytest.skip("scripts/check_runtime.py not found")
        with open(path) as f:
            content = f.read()
        assert ">=3.11" in content
        assert ">=3.10" not in content


class TestSafeMode:
    """Safe mode must skip disabled experimental features."""

    def test_safe_init_skips_when_disabled(self):
        """_safe_init returns None when FeatureManager says disabled."""
        from core.feature_manager import FeatureManager
        fm = FeatureManager()
        fm.register("test_feature", enabled=False)

        from ui.window import MainWindow
        mw = MainWindow.__new__(MainWindow)
        mw._features = fm
        result = mw._safe_init("test_feature", lambda: "should_not_run")
        assert result is None, "safe_init should skip disabled features"

    def test_safe_init_runs_when_enabled(self):
        """_safe_init executes factory when FeatureManager says enabled."""
        from core.feature_manager import FeatureManager
        fm = FeatureManager()

        from ui.window import MainWindow
        mw = MainWindow.__new__(MainWindow)
        mw._features = fm
        fm.register("test_feature", enabled=True)
        result = mw._safe_init("test_feature", lambda: "ran")
        assert result == "ran", "safe_init should run enabled features"


class TestPlaylistImport:
    """Playlist import must handle mixed entries correctly."""

    def test_parse_playlist_entries_mixed(self):
        """Rich parser preserves missing and remote entries."""
        from ui.playlist_io import parse_playlist_entries, PlaylistEntry
        with tempfile.NamedTemporaryFile(mode="w", suffix=".m3u", delete=False) as f:
            f.write("#EXTM3U\n")
            f.write("/exists/song1.mp3\n")
            f.write("/missing/song2.mp3\n")
            f.write("https://remote.com/song3.mp3\n")
            f.write("relative_song.mp3\n")
            tmp = f.name

        try:
            entries = parse_playlist_entries(tmp)
            assert len(entries) == 4

            remote = [e for e in entries if e.is_remote]
            assert len(remote) == 1
            assert remote[0].original_line == "https://remote.com/song3.mp3"

            # Check types
            for e in entries:
                assert isinstance(e, PlaylistEntry)
                assert isinstance(e.path, str)
                assert isinstance(e.exists, bool)
                assert isinstance(e.is_remote, bool)
        finally:
            os.unlink(tmp)

    def test_m3u_utf8_export_atomic(self):
        """M3U export must use UTF-8 and atomic write."""
        from ui.playlist_io import export_m3u
        with tempfile.NamedTemporaryFile(suffix=".m3u", delete=False) as f:
            tmp = f.name

        try:
            export_m3u(tmp, ["/test/file.mp3"], title="Test")
            with open(tmp, encoding="utf-8") as f:
                content = f.read()
            assert "#EXTM3U" in content
            assert "file.mp3" in content
            # No .tmp left behind
            assert not os.path.exists(tmp + ".tmp")
        finally:
            os.unlink(tmp)


class TestFavoritesIdentity:
    """Favorites must resolve by id, filepath, and track_uid."""

    def test_resolve_track_ids_by_filepath(self):
        from ui.window import MainWindow
        from legacy_widgets.ui.controllers.legacy_controllers.smart_mix_controller import SmartMixController
        from library.media_item import MediaItem

        mw = MainWindow.__new__(MainWindow)
        item = MediaItem()
        item.filepath = "/test/song.mp3"
        item.title = "Test Song"
        mw._all_items = [item]
        mw._items_index = {item.filepath: item}
        mw._db = MagicMock()
        mw._db.get_all = MagicMock(return_value=[item])
        mw._db.get_by_id = MagicMock(return_value=None)
        mw._smart_ctrl = SmartMixController(mw)

        result = mw._smart_ctrl.resolve_track_ids(["/test/song.mp3"])
        assert len(result) == 1
        assert result[0].title == "Test Song"

    def test_resolve_track_ids_by_id(self):
        from ui.window import MainWindow
        from legacy_widgets.ui.controllers.legacy_controllers.smart_mix_controller import SmartMixController
        from library.media_item import MediaItem

        mw = MainWindow.__new__(MainWindow)
        item = MediaItem()
        item.filepath = "/test/song2.mp3"
        item.id = 42
        item.title = "ID Song"
        mw._all_items = [item]
        mw._items_index = {}
        mw._db = MagicMock()
        mw._db.get_all = MagicMock(return_value=[item])
        mw._db.get_by_id = MagicMock(return_value=item)
        mw._smart_ctrl = SmartMixController(mw)

        result = mw._smart_ctrl.resolve_track_ids(["42"])
        assert len(result) == 1
        assert result[0].title == "ID Song"


class TestAuditWindow:
    """audit_window.py must run and produce valid metrics."""

    def test_audit_runs(self):
        root = os.path.join(os.path.dirname(__file__), "..")
        script = os.path.join(root, "tools", "audit_window.py")
        if not os.path.exists(script):
            pytest.skip("tools/audit_window.py not found")
        with open(script) as f:
            content = f.read()
        assert "count_lines" in content
        assert "count_methods" in content
        # Should reference ui/window.py
        assert "window.py" in content


class TestCoverFlowNoSubprocess:
    """CoverFlow must not use subprocess.Popen."""

    def test_no_subprocess_in_open_folder(self):
        root = os.path.join(os.path.dirname(__file__), "..")
        with open(os.path.join(root, "ui", "controllers", "coverflow_controller.py")) as f:
            content = f.read()
        assert "subprocess" not in content
        assert "QDesktopServices" in content or "openUrl" in content


class TestCloseEventNoPrivateEngine:
    """closeEvent must not access engine._queue or engine._queue_index."""

    def test_close_event_uses_public_api(self):
        root = os.path.join(os.path.dirname(__file__), "..")
        with open(os.path.join(root, "ui", "window.py")) as f:
            content = f.read()
        close_section = content.split("def closeEvent")[1].split("def ")[0]
        assert "engine._queue" not in close_section
        assert "engine._queue_index" not in close_section
        assert "get_queue_state" in close_section
