"""Tests for core.paths centralized path resolution."""
import os


class TestCorePaths:
    def test_database_path_default(self, monkeypatch):
        """database_path() returns XDG data dir + library.db."""
        monkeypatch.delenv("MICHI_TEST_DATA_DIR", raising=False)
        monkeypatch.setenv("XDG_DATA_HOME", "/tmp/test_xdg_data")
        # Re-import to pick up cleared env
        import importlib
        import core.paths
        importlib.reload(core.paths)
        from core.paths import database_path
        path = database_path()
        assert path == "/tmp/test_xdg_data/michi-music-player/library.db"

    def test_database_path_overridden(self, monkeypatch):
        """database_path() respects MICHI_TEST_DATA_DIR override."""
        monkeypatch.setenv("MICHI_TEST_DATA_DIR", "/tmp/michi_test_data")
        from core.paths import database_path
        path = database_path()
        assert path == "/tmp/michi_test_data/library.db"

    def test_app_data_dir_override(self, monkeypatch):
        monkeypatch.setenv("MICHI_TEST_DATA_DIR", "/tmp/override")
        from core.paths import app_data_dir
        assert app_data_dir() == "/tmp/override"

    def test_app_cache_dir_override(self, monkeypatch):
        monkeypatch.setenv("MICHI_TEST_CACHE_DIR", "/tmp/cache_override")
        from core.paths import app_cache_dir
        assert app_cache_dir() == "/tmp/cache_override"

    def test_app_config_dir_override(self, monkeypatch):
        monkeypatch.setenv("MICHI_TEST_CONFIG_DIR", "/tmp/config_override")
        from core.paths import app_config_dir
        assert app_config_dir() == "/tmp/config_override"

    def test_database_path_used_by_librarydb(self):
        """LibraryDB default path follows core.paths convention."""
        from core.paths import app_data_dir, database_path
        assert database_path().endswith("library.db")
        assert database_path() == os.path.join(app_data_dir(), "library.db")

    def test_covers_cache_dir(self, monkeypatch):
        monkeypatch.setenv("XDG_CACHE_HOME", "/tmp/xdg_cache")
        from core.paths import covers_cache_dir
        path = covers_cache_dir()
        assert "covers" in path
        assert "local" in path
