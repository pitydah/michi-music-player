"""Lifecycle regression tests — protect full-state preservation."""

from michi.application.playback_service import PlaybackService
from michi.application.settings_service import SettingsService
from michi.domain.settings import SettingsState
from tests.conftest import FakeAudioPort, FakeSettingsRepo


class TestSettingsLifecycle:
    def test_full_state_preserved_after_shutdown(self):
        repo = FakeSettingsRepo()
        repo.save(
            SettingsState(
                volume=20,
                muted=False,
                last_directory="/music",
                recent_files=["a.mp3", "b.mp3"],
            )
        )
        settings = SettingsService(repo)
        s = settings.load()
        audio = FakeAudioPort()
        playback = PlaybackService(audio)
        playback.restore_volume(s.volume, s.muted)
        playback.set_volume(73)
        playback.set_muted(True)
        vol, muted = playback.snapshot_volume()
        settings.set_playback_preferences(vol, muted)
        settings.save()
        settings2 = SettingsService(repo)
        s2 = settings2.load()
        assert s2.volume == 73
        assert s2.muted is True
        assert s2.last_directory == "/music"
        assert s2.recent_files == ["a.mp3", "b.mp3"]

    def test_playback_preferences_via_public_api(self):
        repo = FakeSettingsRepo()
        settings = SettingsService(repo)
        settings.set_playback_preferences(99, True)
        settings.save()
        s = repo.load()
        assert s.volume == 99
        assert s.muted is True

    def test_volume_clamping(self):
        repo = FakeSettingsRepo()
        settings = SettingsService(repo)
        settings.set_playback_preferences(150, False)
        assert settings.state.volume == 100
        settings.set_playback_preferences(-10, False)
        assert settings.state.volume == 0


class TestAlbumArtworkSourcePersistence:
    """POST-R4 E2 (12.4): la elección de fuente de artwork por álbum se
    persiste (round-trip) con decode tolerante."""

    def test_round_trip(self, tmp_path):
        from michi.infrastructure.sqlite_settings import (
            SQLiteSettingsRepository,
        )

        db = tmp_path / "settings.db"
        repo = SQLiteSettingsRepository.open_for_startup(db)
        service = SettingsService(repo)
        service.set_album_artwork_source("album-1", "external")
        service.set_album_artwork_source("album-2", "local")

        reloaded = SettingsService(SQLiteSettingsRepository.open_for_startup(db))
        assert reloaded.album_artwork_source("album-1") == "external"
        assert reloaded.album_artwork_source("album-2") == "local"
        assert reloaded.album_artwork_source("album-3") == ""

    def test_invalid_sources_ignored(self, tmp_path):
        from michi.infrastructure.sqlite_settings import (
            SQLiteSettingsRepository,
        )

        db = tmp_path / "settings.db"
        repo = SQLiteSettingsRepository.open_for_startup(db)
        service = SettingsService(repo)
        service.set_album_artwork_source("album-1", "nonsense")
        assert service.album_artwork_source("album-1") == ""
        service.set_album_artwork_source("album-1", "")
        assert service.album_artwork_source("album-1") == ""

    def test_malformed_persisted_value_decodes_empty(self, tmp_path):
        import sqlite3

        from michi.infrastructure.sqlite_settings import (
            SQLiteSettingsRepository,
        )

        db = tmp_path / "settings.db"
        SQLiteSettingsRepository.open_for_startup(db)
        conn = sqlite3.connect(str(db))
        conn.execute(
            "INSERT OR REPLACE INTO settings VALUES (?, ?)",
            ("album_artwork_source", "{not-json"),
        )
        conn.commit()
        conn.close()
        repo = SQLiteSettingsRepository.open_for_startup(db)
        service = SettingsService(repo)
        assert service.album_artwork_source("album-1") == ""


class TestStudioListMetadataLevelRemovedFromSchema:
    """POST-R4 P5 (auditoría): studioList.metadataLevel ya no vive en la
    autoridad del dominio — el decoder tolera el JSON histórico y el
    re-save ya no lo emite (sin deuda ficticia persistida)."""

    def test_historical_json_with_metadata_level_decodes_and_resaves_clean(self):
        from michi.domain.settings import (
            LibraryViewPreferences,
            library_view_preferences_from_json,
            library_view_preferences_to_json,
        )

        historical = (
            '{"activeMode": "list", "studioList": {"density": "standard", '
            '"artworkSize": "small", "metadataLevel": "detailed", '
            '"precisionMetadata": true}}'
        )
        prefs, malformed = library_view_preferences_from_json(historical)
        assert malformed is False
        assert prefs.studio_list.density == "standard"
        # el JSON histórico decodifica sin romper…
        import json as _json

        reserialized = _json.loads(library_view_preferences_to_json(prefs))
        assert "metadataLevel" not in reserialized["studioList"], (
            "el re-save ya no emite metadataLevel del studio list"
        )
        # …y el campo sobrevive donde SÍ es productivo (gallery/flow)
        assert "metadataLevel" in reserialized["gallery"]
        assert "metadataLevel" in reserialized["vinyl"]

    def test_round_trip_persists_clean_schema(self, tmp_path):
        from michi.infrastructure.sqlite_settings import (
            SQLiteSettingsRepository,
        )

        db = tmp_path / "settings.db"
        repo = SQLiteSettingsRepository.open_for_startup(db)
        service = SettingsService(repo)
        service.save()
        reloaded = SettingsService(SQLiteSettingsRepository.open_for_startup(db))
        raw = reloaded.state.library_views
        from michi.domain.settings import library_view_preferences_to_json

        import json as _json

        serialized = _json.loads(library_view_preferences_to_json(raw))
        assert "metadataLevel" not in serialized["studioList"], (
            "el studio list persistido ya no lleva metadataLevel"
        )
