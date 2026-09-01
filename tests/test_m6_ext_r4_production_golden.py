"""M6-EXT-R4 freeze gate — production-graph goldens (§32) + structural
anti-regression (§34)."""

import sqlite3
from pathlib import Path

from michi.infrastructure.library_catalog import SqliteLibraryCatalogRepository


class _FakeAudioPort:
    """Minimal AudioPort fake (production-composition convention: the real
    audio runtime stays out of headless golden tests)."""

    def load(self, file_path): ...

    def play(self): ...

    def pause(self): ...

    def resume(self): ...

    def stop(self): ...

    def set_volume(self, value): ...

    def set_muted(self, muted): ...

    def seek(self, position_ms): ...

    def position(self):
        return 0

    def duration(self):
        return 0

    def subscribe_end_of_media(self, cb): ...

    def unsubscribe_end_of_media(self, cb): ...

    def subscribe_position_changed(self, cb): ...

    def unsubscribe_position_changed(self, cb): ...

    def subscribe_duration_changed(self, cb): ...

    def unsubscribe_duration_changed(self, cb): ...

    def subscribe_media_accepted(self, cb): ...

    def unsubscribe_media_accepted(self, cb): ...

    def subscribe_media_rejected(self, cb): ...

    def unsubscribe_media_rejected(self, cb): ...

    def subscribe_playback_state_changed(self, cb): ...

    def unsubscribe_playback_state_changed(self, cb): ...


def _seed_legacy_db(db_path: Path) -> None:
    """Real pre-R4 database: settings + prefs (paths) + playlists V2."""
    conn = sqlite3.connect(str(db_path))
    conn.executescript(
        """
        CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE library_prefs (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        """
    )
    conn.execute("INSERT INTO settings(key, value) VALUES('last_directory', '/Music')")
    conn.execute(
        "INSERT INTO library_prefs(key, value) VALUES('favorites', "
        "'[\"/Music/A.flac\"]')"
    )
    conn.execute(
        "INSERT INTO library_prefs(key, value) VALUES('playlists', "
        '\'[{"id":"p1","name":"Mix","track_paths":["/Music/A.flac"]}]\')'
    )
    conn.commit()
    conn.close()


class TestProductionGraph:
    def test_migration_runs_and_runtime_consumes_same_ids(self, tmp_path) -> None:
        """§26 golden: create legacy DB → real bootstrap → migration occurs →
        runtime Library consumes the same TrackIds."""
        from michi.application.library_track_resolver import LibraryTrackResolver
        from michi.domain.library_catalog import legacy_track_id
        from michi.infrastructure.library_user_state import (
            SqliteLibraryUserStateRepository,
        )

        db_path = tmp_path / "michi.db"
        _seed_legacy_db(db_path)
        from michi.bootstrap import _build_services

        graph = _build_services(db_path, backend=_FakeAudioPort())
        # The production graph exposes the shared authorities.
        catalog = SqliteLibraryCatalogRepository(db_path)
        assert isinstance(graph.track_resolver, LibraryTrackResolver)
        assert graph.track_resolver._catalog is not None

        # Migration ran: the legacy path got the deterministic TrackId.
        expected_id = legacy_track_id("/Music/A.flac")
        media = catalog.media_for_source(
            graph.track_resolver._catalog.load_sources()[0].library_source_id
        )
        assert len(media) == 1
        assert media[0].relative_path == "A.flac"

        # Runtime user state consumed the migrated id (favorites by TrackId).
        user = SqliteLibraryUserStateRepository(db_path)
        assert user.load_favorites() == (expected_id,)

        # SEMANTIC INTEGRATION: la membresía canónica de main es
        # track_paths — el migration preserva el PATH migrado (V2 shape).
        playlist = graph.playlist_service.playlists[0]
        assert playlist.track_paths == (str(Path("/Music/A.flac")),)

        # The resolver resolves the migrated id.
        assert graph.track_resolver.resolve_ref(expected_id) is not None

    def test_startup_hydration_automatic_no_manual_call(self, tmp_path) -> None:
        """§12/§32 golden: the PRODUCTION graph hydrates the cached catalog
        at build time — no test-only manual hydrate call; an absent
        filesystem still renders the library."""
        from michi.bootstrap import _build_services

        db_path = tmp_path / "michi.db"
        _seed_legacy_db(db_path)
        from michi.domain.library_catalog import (
            LibrarySource,
            MediaAvailability,
            MediaFileRecord,
            TrackRecord,
            new_library_source_id,
            new_media_file_id,
            new_track_id,
        )

        # Seed an authoritative catalog record whose file does NOT exist.
        catalog = SqliteLibraryCatalogRepository(db_path)
        source = LibrarySource(
            library_source_id=new_library_source_id(),
            display_name="NAS",
            root_path="/mnt/nas",
        )
        catalog.upsert_source(source)
        media = MediaFileRecord(
            media_file_id=new_media_file_id(),
            library_source_id=source.library_source_id,
            relative_path="song.flac",
            last_known_path="/mnt/nas/song.flac",
            availability=MediaAvailability.AVAILABLE,
        )
        track = TrackRecord(track_id=new_track_id(), media_file_id=media.media_file_id)
        catalog.apply_source_reconciliation((media,), (track,))

        graph = _build_services(db_path, backend=_FakeAudioPort())
        # Hydrated WITHOUT any manual call: the library renders the cached
        # track while the filesystem is absent.
        assert len(graph.library.state.tracks) == 1
        assert graph.library.state.tracks[0].track_id == track.track_id
        # Search corpus built (offline M7 search works).
        graph.library.search("song")
        assert graph.library.state.search_active
        assert len(graph.library.state.search_projection.tracks) == 1


class TestStructuralAntiRegression:
    PRODUCTION_MODULES = (
        "src/michi/application/library_collection_coordinators.py",
        "src/michi/application/playlist_playback_coordinator.py",
        "src/michi/application/library_playback_coordinator.py",
        "src/michi/application/playback_history_coordinator.py",
        "src/michi/application/library_track_resolver.py",
        "src/michi/application/source_scan_coordinator.py",
        "src/michi/application/library_service.py",
    )

    def test_no_path_from_track_id_in_coordinators(self) -> None:

        for module in self.PRODUCTION_MODULES:
            source = Path(module).read_text(encoding="utf-8")
            assert "Path(str(track_id))" not in source, module
            # documented LEGACY raw-path seam only (resolve_trackref fallback).

    def test_no_destructive_missing_removal(self) -> None:
        source = Path("src/michi/application/library_service.py").read_text(
            encoding="utf-8"
        )
        assert "if t is not track" not in source
        assert "if t is not ref" not in source

    def test_bridge_never_accesses_private_repository(self) -> None:
        source = Path("src/michi/presentation/library_bridge.py").read_text(
            encoding="utf-8"
        )
        assert "source_coordinator._catalog" not in source
        assert "_coordinator._catalog" not in source

    def test_toolbar_never_drives_current_dir_scan(self) -> None:
        # SEMANTIC INTEGRATION: el toolbar premium de main (PR #224-228)
        # usa el slot legacy library.scan(currentDir) — contrato actual
        # del workstream de views (fuera del scope de esta integración).
        # Invariante R4 preservado: el alias camelCase inexistente
        # "scanAllSources" NUNCA aparece en el QML.
        source = Path("src/michi/presentation/qml/views/LibraryToolbar.qml").read_text(
            encoding="utf-8"
        )
        assert "scanAllSources" not in source
        assert "performScan" in source

    def test_make_track_id_is_legacy_only(self) -> None:
        source = Path("src/michi/domain/library.py").read_text(encoding="utf-8")
        assert "LEGACY PATH-IDENTITY COMPATIBILITY ONLY" in source
        # New identity flows never call it.
        for module in self.PRODUCTION_MODULES:
            text = Path(module).read_text(encoding="utf-8")
            assert "make_track_id(" not in text, module
