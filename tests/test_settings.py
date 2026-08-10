"""Tests for SQLite settings persistence."""

from michi.domain.settings import SettingsState
from michi.infrastructure.sqlite_settings import SQLiteSettingsRepository


class TestSQLiteSettings:
    def test_defaults_on_new_db(self, tmp_path):
        repo = SQLiteSettingsRepository(tmp_path / "test.db")
        state = repo.load()
        assert state.volume == 80
        assert state.muted is False

    def test_save_and_reload(self, tmp_path):
        repo = SQLiteSettingsRepository(tmp_path / "test.db")
        state = SettingsState(volume=42, muted=True, last_directory="/music")
        repo.save(state)

        loaded = repo.load()
        assert loaded.volume == 42
        assert loaded.muted is True
        assert loaded.last_directory == "/music"

    def test_reopen_preserves_data(self, tmp_path):
        db_path = tmp_path / "test.db"
        repo1 = SQLiteSettingsRepository(db_path)
        repo1.save(SettingsState(volume=33))

        repo2 = SQLiteSettingsRepository(db_path)
        assert repo2.load().volume == 33
