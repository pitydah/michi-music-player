"""M5.C6 — theme + window geometry persistence (domain, repo, service, bridge)."""

import json
import logging
import sqlite3

from michi.application.settings_service import SettingsService
from michi.domain.settings import SettingsState, WindowGeometry
from michi.infrastructure.sqlite_settings import SQLiteSettingsRepository

_LOGGER_NAME = "michi.infrastructure.sqlite_settings"


def _write_raw_rows(db_path, rows):
    """Fabricate DB state using controlled raw SQL (test-only)."""
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS settings ("
            "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        conn.executemany("INSERT OR REPLACE INTO settings VALUES (?, ?)", rows)


def _read_raw_rows(db_path):
    uri = f"{db_path.resolve().as_uri()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        return dict(conn.execute("SELECT key, value FROM settings").fetchall())


def _warnings(caplog, key):
    return [r.getMessage() for r in caplog.records if f"'{key}'" in r.getMessage()]


def _expect_warning_logging(caplog):
    caplog.set_level(logging.WARNING, logger=_LOGGER_NAME)


def _valid_geometry_json(x=None, y=None, width=1100, height=700, maximized=False):
    return json.dumps(
        {
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "maximized": maximized,
        }
    )


class TestWindowGeometryDomain:
    def test_geometry_defaults(self):
        g = WindowGeometry()
        assert g.x is None
        assert g.y is None
        assert g.width == 1100
        assert g.height == 700
        assert g.maximized is False

    def test_theme_default(self):
        s = SettingsState()
        assert s.theme == "dark"
        assert s.window_geometry == WindowGeometry()


class TestRepoThemeGeometry:
    def test_repo_theme_round_trip(self, tmp_path):
        db = tmp_path / "theme.db"
        repo = SQLiteSettingsRepository(db)
        repo.save(SettingsState(theme="light"))
        fresh = SQLiteSettingsRepository(db)
        assert fresh.load().theme == "light"

    def test_repo_geometry_round_trip(self, tmp_path):
        db = tmp_path / "geo.db"
        geometry = WindowGeometry(x=-5, y=10, width=1200, height=800, maximized=True)
        repo = SQLiteSettingsRepository(db)
        repo.save(SettingsState(window_geometry=geometry))
        fresh = SQLiteSettingsRepository(db)
        assert fresh.load().window_geometry == geometry

    def test_repo_malformed_geometry_row(self, tmp_path, caplog):
        db = tmp_path / "badgeo.db"
        _write_raw_rows(db, [("window_geometry", "not json")])
        _expect_warning_logging(caplog)
        state = SQLiteSettingsRepository(db).load()
        assert state.window_geometry == WindowGeometry()
        assert len(_warnings(caplog, "window_geometry")) == 1

    def test_repo_invalid_geometry_dimensions(self, tmp_path, caplog):
        _expect_warning_logging(caplog)
        db0 = tmp_path / "w0.db"
        _write_raw_rows(db0, [("window_geometry", _valid_geometry_json(width=0))])
        state = SQLiteSettingsRepository(db0).load()
        assert state.window_geometry == WindowGeometry()
        assert len(_warnings(caplog, "window_geometry")) == 1

        caplog.clear()
        db1 = tmp_path / "hneg.db"
        _write_raw_rows(db1, [("window_geometry", _valid_geometry_json(height=-10))])
        state = SQLiteSettingsRepository(db1).load()
        assert state.window_geometry == WindowGeometry()
        assert len(_warnings(caplog, "window_geometry")) == 1

    def test_repo_missing_geometry_row(self, tmp_path, caplog):
        db = tmp_path / "nogeo.db"
        _write_raw_rows(db, [("volume", "42")])
        _expect_warning_logging(caplog)
        state = SQLiteSettingsRepository(db).load()
        assert state.window_geometry == WindowGeometry()
        assert _warnings(caplog, "window_geometry") == []

    def test_repo_malformed_theme(self, tmp_path, caplog):
        db = tmp_path / "badtheme.db"
        # TEXT column affinity turns an int into the string '42' (a valid
        # theme); inject a BLOB to represent genuine non-text garbage.
        _write_raw_rows(db, [("theme", b"\xff\x00")])
        _expect_warning_logging(caplog)
        state = SQLiteSettingsRepository(db).load()
        assert state.theme == "dark"
        assert len(_warnings(caplog, "theme")) == 1

    def test_field_level_isolation(self, tmp_path, caplog):
        db = tmp_path / "iso.db"
        _write_raw_rows(
            db,
            [
                ("window_geometry", "{broken"),
                ("volume", "55"),
                ("muted", "true"),
                ("last_directory", "/music"),
                ("recent_files", json.dumps(["a.flac"])),
            ],
        )
        _expect_warning_logging(caplog)
        state = SQLiteSettingsRepository(db).load()
        assert state.window_geometry == WindowGeometry()
        assert state.volume == 55
        assert state.muted is True
        assert state.last_directory == "/music"
        assert state.recent_files == ["a.flac"]


class TestServiceThemeGeometry:
    def test_service_set_theme_persists(self, tmp_path):
        db = tmp_path / "svc-theme.db"
        service = SettingsService(SQLiteSettingsRepository(db))
        service.set_theme("light")
        assert _read_raw_rows(db)["theme"] == "light"
        reloaded = SettingsService(SQLiteSettingsRepository(db)).load()
        assert reloaded.theme == "light"

    def test_service_set_geometry_persists(self, tmp_path):
        db = tmp_path / "svc-geo.db"
        service = SettingsService(SQLiteSettingsRepository(db))
        geometry = WindowGeometry(x=-20, y=5, width=1280, height=900, maximized=True)
        service.set_window_geometry(geometry)
        raw = json.loads(_read_raw_rows(db)["window_geometry"])
        assert raw == {
            "x": -20,
            "y": 5,
            "width": 1280,
            "height": 900,
            "maximized": True,
        }
        reloaded = SettingsService(SQLiteSettingsRepository(db)).load()
        assert reloaded.window_geometry == geometry


class TestBridgeThemeGeometry:
    def test_bridge_theme_properties(self, tmp_path):
        from michi.presentation.settings_bridge import SettingsBridge

        service = SettingsService(SQLiteSettingsRepository(tmp_path / "b.db"))
        bridge = SettingsBridge(service)
        assert bridge.property("theme") == "dark"
        bridge.set_theme("light")
        assert bridge.property("theme") == "light"
        assert service.state.theme == "light"

    def test_bridge_geometry_slot(self, tmp_path):
        from michi.presentation.settings_bridge import SettingsBridge

        service = SettingsService(SQLiteSettingsRepository(tmp_path / "g.db"))
        bridge = SettingsBridge(service)
        geometry = json.dumps(
            {"x": 10, "y": 20, "width": 900, "height": 600, "maximized": True}
        )
        bridge.set_window_geometry(geometry)
        assert bridge.property("windowGeometry") == geometry
        bridge.set_window_geometry("not json")
        assert bridge.property("windowGeometry") == geometry
