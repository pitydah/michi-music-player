"""Smoke test for MainWindow in safe mode — detects wiring failures."""


class TestMainWindowSmoke:
    """Minimal smoke test: instantiate MainWindow in safe/offscreen mode."""

    def test_mainwindow_smoke_safe_mode(self, qapp, monkeypatch, tmp_path):
        monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
        monkeypatch.setenv("MICHI_SAFE_MODE", "1")
        monkeypatch.setenv("MICHI_TEST_DATA_DIR", str(tmp_path / "data"))
        monkeypatch.setenv("MICHI_TEST_CACHE_DIR", str(tmp_path / "cache"))
        monkeypatch.setenv("MICHI_TEST_CONFIG_DIR", str(tmp_path / "config"))

        from ui.window import MainWindow
        w = MainWindow()
        try:
            assert w.windowTitle(), "Window title should be set"
            assert hasattr(w, "_nav_ctrl"), "Missing _nav_ctrl"
            assert hasattr(w, "_lib_ctrl"), "Missing _lib_ctrl"
            assert hasattr(w, "_player_bar"), "Missing _player_bar"
            assert hasattr(w, "_ctx"), "Missing _ctx"
            assert hasattr(w, "_playlist_ctrl"), "Missing _playlist_ctrl"
        finally:
            w.close()
            w.deleteLater()
            qapp.processEvents()
