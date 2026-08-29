"""LOCAL-05 favorites / history / recently-added (persisted) — Phase-1 RED tests.

On the current baseline the module-level import of the new domain symbol
(LibraryPrefs) fails at collection (ImportError) — that IS the expected
Phase-1 red evidence. The tests encode the target contract and must pass
once the production changes land (michi/domain/library.py LibraryPrefs +
LibraryState favorite/history/recently-added fields with HISTORY_CAP=50 and
RECENT_CAP=50, michi/application/ports.py LibraryPrefsPort, michi/
infrastructure/library_prefs.py SqliteLibraryPrefsRepository, LibraryService
prefs init + toggle_favorite/set_favorite + _on_queue_changed history
recording + scan-driven recently-added, LibraryBridge favoritePaths/
historyPaths/recentlyAddedPaths/songPaths/favoriteRows/historyRows/
recentlyAddedRows + toggle_favorite slot, and the LibraryView.qml tabs).

Helpers reuse the existing fakes: FakeScanner/FakeExtractor from
tests.test_library_metadata, FakeAudioPort from tests.conftest,
FailingScanner from tests.test_library_artwork. FakePrefsPort is defined
here (in-memory, seedable, records every save).

Coverage:
- Favorites: toggle add/remove, explicit set, deterministic sorted order,
  prefs round-trip init, best-effort persistence via the port
- History: queue commit records, consecutive dedupe, 50 cap most-recent-first,
  nothing recorded while a play request is pending, persisted via the port
- Recently added: canonical merge (LOCAL-STABILIZATION-01.6.5) — new tracks
  from the current scan first (most recent scan order, reversed), then previous
  recently-added entries still in the library; deduplicated and 50-cap;
  an identical rescan MUST preserve the list, removed tracks fall out once they
  leave the library, failed scan untouched, persisted via port.
  CONTRACT CHANGE: the old rule rebuilt recently added from the per-scan delta,
  so an unchanged rescan erased it; the tests that encoded that rule were
  updated (test_identical_rescan_preserves_recently_added replaces
  test_rescan_no_changes_no_update, test_new_scan_paths_prepended and
  test_recently_added_capped now assert preservation across rescans).
- Bridge: row/toggle surface, songPaths parallel to files, missing paths
  skipped in rows
- Reference-persistence audit (LOCAL-STABILIZATION-01.6.6): favorites survive
  missing-track activation, favorites/history survive identical rescans,
  failed scans preserve all three references, missing favorite hidden from
  rows but kept in the reference tuple
- Sqlite repository: round trip, empty fresh db, missing file never raises,
  settings table untouched (shared db)
- QML smoke: LibraryView.qml still instantiates with the real bridge
  (forward pin for the three new tabs + star toggles — passes trivially on
  baseline)
"""

import os
import sqlite3
import sys
from pathlib import Path

import pytest
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine

from michi.application.library_port import LibraryFilesystemError
from michi.application.library_service import LibraryService
from michi.application.playback_service import PlaybackService
from michi.application.playback_session_service import PlaybackSessionService
from michi.application.queue_service import QueueService
from michi.domain.library import LibraryDiagnosticCode, LibraryPrefs
from michi.infrastructure.library_prefs import SqliteLibraryPrefsRepository
from michi.presentation.library_bridge import LibraryBridge
from tests.conftest import FakeAudioPort
from tests.test_library_artwork import FailingScanner
from tests.test_library_metadata import FakeExtractor, FakeScanner

QML_DIR = Path(__file__).resolve().parents[1] / "src" / "michi" / "presentation" / "qml"

HISTORY_CAP = 50
RECENT_CAP = 50


class FakePrefsPort:
    """In-memory LibraryPrefsPort: seedable; every save is recorded.

    load() returns the stored prefs (or empty LibraryPrefs when never
    seeded/saved); save() stores the prefs and appends them to ``saved``.
    Never raises — mirrors the best-effort port contract.
    """

    def __init__(self, prefs=None) -> None:
        self._stored = prefs if prefs is not None else LibraryPrefs()
        self.saved: list[LibraryPrefs] = []

    def load(self) -> LibraryPrefs:
        return self._stored

    def save(self, prefs: LibraryPrefs) -> None:
        self._stored = prefs
        self.saved.append(prefs)


def _make_library_and_queue(scanner, prefs_port=None, extractor=None):
    """Build LibraryService with a real queue + the shared FakeAudioPort.

    Returns (library, queue, audio): ``audio`` is needed to trigger the
    media-acceptance path that commits pending queue plays.
    """
    audio = FakeAudioPort()
    playback = PlaybackService(audio)
    queue = QueueService()
    session = PlaybackSessionService(playback, queue)
    from michi.application.playback_history_coordinator import (
        PlaybackHistoryCoordinator,
    )

    if extractor is None:
        library = LibraryService(scanner, library_prefs=prefs_port)
    else:
        library = LibraryService(
            scanner, metadata_extractor=extractor, library_prefs=prefs_port
        )
    # M4-R1: History is PLAYBACK-COMMIT driven — the coordinator records it.
    history = PlaybackHistoryCoordinator(session, library)
    history.start()
    return library, queue, session, audio


def _write_tracks(tmp_path, names):
    """Create real (empty) track files and return their Paths."""
    paths = [tmp_path / name for name in names]
    for p in paths:
        p.write_bytes(b"x")
    return paths


class TestFavoritesService:
    def test_toggle_favorite_adds_and_removes(self, tmp_path):
        p = tmp_path / "one.mp3"
        p.write_bytes(b"x")
        library, _, _, _ = _make_library_and_queue(FakeScanner())
        library.toggle_favorite(p)
        assert str(p) in library.state.favorite_paths
        library.toggle_favorite(p)
        assert str(p) not in library.state.favorite_paths

    def test_set_favorite_explicit(self, tmp_path):
        p = tmp_path / "one.mp3"
        p.write_bytes(b"x")
        library, _, _, _ = _make_library_and_queue(FakeScanner())
        library.set_favorite(p, True)
        assert str(p) in library.state.favorite_paths
        library.set_favorite(p, False)
        assert str(p) not in library.state.favorite_paths

    def test_favorites_sorted_deterministic(self, tmp_path):
        p1 = tmp_path / "one.mp3"
        p2 = tmp_path / "two.mp3"
        for p in (p1, p2):
            p.write_bytes(b"x")
        first, _, _, _ = _make_library_and_queue(FakeScanner())
        first.toggle_favorite(p2)
        first.toggle_favorite(p1)
        second, _, _, _ = _make_library_and_queue(FakeScanner())
        second.toggle_favorite(p1)
        second.toggle_favorite(p2)
        expected = tuple(sorted((str(p1), str(p2))))
        assert first.state.favorite_paths == expected
        assert second.state.favorite_paths == expected

    def test_favorites_persisted_round_trip(self):
        port = FakePrefsPort(
            prefs=LibraryPrefs(favorite_paths=("/music/a.mp3", "/music/b.mp3"))
        )
        library, _, _, _ = _make_library_and_queue(FakeScanner(), prefs_port=port)
        assert library.state.favorite_paths == ("/music/a.mp3", "/music/b.mp3")

    def test_toggle_persists_via_port(self, tmp_path):
        p = tmp_path / "one.mp3"
        p.write_bytes(b"x")
        port = FakePrefsPort()
        library, _, _, _ = _make_library_and_queue(FakeScanner(), prefs_port=port)
        library.toggle_favorite(p)
        assert str(p) in port.saved[-1].favorite_paths


class TestHistoryRecording:
    def test_queue_commit_records_history(self):
        library, queue, session, audio = _make_library_and_queue(FakeScanner())
        path = Path("/music/one.mp3")
        queue.add(path)
        session.play_queue_index(0)
        audio.trigger_media_accepted(path)
        assert library.state.history_paths[0] == str(path)

    def test_history_dedupes_consecutive(self):
        library, queue, session, audio = _make_library_and_queue(FakeScanner())
        path = Path("/music/one.mp3")
        queue.add(path)
        session.play_queue_index(0)
        audio.trigger_media_accepted(path)
        session.previous()
        audio.trigger_media_accepted(path)
        assert library.state.history_paths == (str(path),)

    def test_history_capped_at_50(self):
        library, queue, session, audio = _make_library_and_queue(FakeScanner())
        paths = [Path(f"/music/t{i:02d}.mp3") for i in range(55)]
        for p in paths:
            queue.add(p)
        for i, p in enumerate(paths):
            session.play_queue_index(i)
            audio.trigger_media_accepted(p)
        assert len(library.state.history_paths) == HISTORY_CAP
        assert library.state.history_paths[0] == str(paths[-1])
        assert library.state.history_paths[-1] == str(paths[5])

    def test_history_not_recorded_when_no_commit(self):
        library, queue, session, _ = _make_library_and_queue(FakeScanner())
        path = Path("/music/one.mp3")
        queue.add(path)
        session.play_queue_index(0)  # pending, never accepted
        assert library.state.history_paths == ()

    def test_history_persisted(self):
        port = FakePrefsPort()
        library, queue, session, audio = _make_library_and_queue(
            FakeScanner(), prefs_port=port
        )
        path = Path("/music/one.mp3")
        queue.add(path)
        session.play_queue_index(0)
        audio.trigger_media_accepted(path)
        assert str(path) in port.saved[-1].history_paths


class TestRecentlyAdded:
    def test_new_scan_paths_prepended(self, tmp_path):
        """Contract change (LOCAL-STABILIZATION-01.6.5): this test previously
        asserted the delta-rebuild rule (recent == ONLY the new paths, so a
        scan erased earlier entries). Canonical rule: new paths first, then
        previously recently-added entries still in the library. scan A
        [p1,p2] -> recent (p2,p1); scan B [p1,p2,p3] -> new=[p3] -> recent
        (p3,p2,p1) (new first, then preserved)."""
        p1, p2, p3 = _write_tracks(tmp_path, ("one.mp3", "two.mp3", "three.mp3"))
        scanner = FakeScanner([p1, p2])
        library, _, _, _ = _make_library_and_queue(scanner)
        library.scan(str(tmp_path))
        assert library.state.recently_added_paths == (str(p2), str(p1))
        scanner.paths = [p1, p2, p3]
        library.scan(str(tmp_path))
        assert library.state.recently_added_paths == (str(p3), str(p2), str(p1))

    def test_identical_rescan_preserves_recently_added(self, tmp_path):
        """Contract change (LOCAL-STABILIZATION-01.6.5): the old test
        (test_rescan_no_changes_no_update) encoded the delta-rebuild rule that
        an identical rescan ERASES recently added (it asserted ()). Canonical
        rule: recently added = new tracks + previous recently-added entries
        still in the library, so an unchanged rescan MUST preserve (p2, p1)."""
        p1, p2 = _write_tracks(tmp_path, ("one.mp3", "two.mp3"))
        scanner = FakeScanner([p1, p2])
        library, _, _, _ = _make_library_and_queue(scanner)
        library.scan(str(tmp_path))
        assert library.state.recently_added_paths == (str(p2), str(p1))
        scanner.paths = [p1, p2]
        library.scan(str(tmp_path))
        assert library.state.recently_added_paths == (str(p2), str(p1))

    def test_recently_added_capped(self, tmp_path):
        """>cap new paths in one scan -> capped at RECENT_CAP (most recent
        scan order first); an identical rescan keeps the capped list intact
        (LOCAL-STABILIZATION-01.6.5 — a rescan must not erase it)."""
        paths = _write_tracks(tmp_path, [f"t{i:02d}.mp3" for i in range(60)])
        scanner = FakeScanner(paths)
        library, _, _, _ = _make_library_and_queue(scanner)
        library.scan(str(tmp_path))
        assert len(library.state.recently_added_paths) == RECENT_CAP
        # Most recent scan order first: the 50 newest scan entries reversed.
        assert library.state.recently_added_paths == tuple(
            str(p) for p in reversed(paths[-RECENT_CAP:])
        )
        scanner.paths = paths  # unchanged rescan
        library.scan(str(tmp_path))
        assert library.state.recently_added_paths == tuple(
            str(p) for p in reversed(paths[-RECENT_CAP:])
        )

    def test_failed_scan_preserves_recently_added(self, tmp_path):
        p1, p2 = _write_tracks(tmp_path, ("one.mp3", "two.mp3"))
        scanner = FailingScanner([p1, p2])
        library, _, _, _ = _make_library_and_queue(scanner)
        library.scan(str(tmp_path))
        before = library.state.recently_added_paths
        scanner.scan_error = LibraryFilesystemError(
            LibraryDiagnosticCode.IO_FAILURE, tmp_path, "i/o error"
        )
        library.scan(str(tmp_path))
        assert library.state.recently_added_paths == before

    def test_recently_added_persisted(self, tmp_path):
        """Saved prefs contain the canonical merged list (new first, then
        preserved entries) after a successful scan."""
        p1, p2 = _write_tracks(tmp_path, ("one.mp3", "two.mp3"))
        port = FakePrefsPort()
        library, _, _, _ = _make_library_and_queue(
            FakeScanner([p1, p2]), prefs_port=port
        )
        library.scan(str(tmp_path))
        assert port.saved[-1].recently_added_paths == (str(p2), str(p1))

    def test_recently_added_removed_tracks_fall_out(self, tmp_path):
        """Canonical removal rule (LOCAL-STABILIZATION-01.6.5): a removed
        track leaves recently added once it is no longer in the library while
        surviving tracks stay. scan [p1,p2] -> (p2,p1); delete p2 and rescan
        with only [p1] -> (p1,) — p2 fell out, p1 preserved."""
        p1, p2 = _write_tracks(tmp_path, ("one.mp3", "two.mp3"))
        scanner = FakeScanner([p1, p2])
        library, _, _, _ = _make_library_and_queue(scanner)
        library.scan(str(tmp_path))
        assert library.state.recently_added_paths == (str(p2), str(p1))
        p2.unlink()
        scanner.paths = [p1]
        library.scan(str(tmp_path))
        assert library.state.recently_added_paths == (str(p1),)

    def test_recently_added_duplicate_path_across_scans(self, tmp_path):
        """Duplicate paths in the scanner result collapse to one recently-added
        entry (the merge dedupes by path). scan [p1]; rescan [p1,p1] -> (p1,)."""
        p1 = tmp_path / "one.mp3"
        p1.write_bytes(b"x")
        scanner = FakeScanner([p1])
        library, _, _, _ = _make_library_and_queue(scanner)
        library.scan(str(tmp_path))
        assert library.state.recently_added_paths == (str(p1),)
        scanner.paths = [p1, p1]
        library.scan(str(tmp_path))
        assert library.state.recently_added_paths == (str(p1),)

    def test_recently_added_restart_persistence(self, tmp_path):
        """Restart: prefs restore recently added; an unchanged rescan of the
        same directory must preserve the restored list (canonical merge,
        LOCAL-STABILIZATION-01.6.5 — the old delta-rebuild erased it on the
        identical rescan)."""
        p1, p2 = _write_tracks(tmp_path, ("one.mp3", "two.mp3"))
        port = FakePrefsPort(
            prefs=LibraryPrefs(recently_added_paths=(str(p2), str(p1)))
        )
        scanner = FakeScanner([p1, p2])
        library, _, _, _ = _make_library_and_queue(scanner, prefs_port=port)
        library.scan(str(tmp_path))
        library.scan(str(tmp_path))  # unchanged rescan
        assert library.state.recently_added_paths == (str(p2), str(p1))
        assert port.saved[-1].recently_added_paths == (str(p2), str(p1))

    def test_merge_recently_added_pure_helper(self):
        """Direct unit tests of the canonical merge (LOCAL-STABILIZATION-01.6.5):
        new paths first (reversed scan order), then previous entries still in
        the library; dedup across new+previous and within new; cap; removal by
        library membership; empty cases. Import is local so a missing symbol on
        baseline surfaces as a per-test ImportError instead of a module-level
        collection failure."""
        from michi.domain.library import merge_recently_added

        # New-first ordering: reversed(new_paths) precede preserved entries.
        assert merge_recently_added(
            new_paths=("a", "b"),
            previous_recent=("x", "y"),
            current_library_paths={"a", "b", "x", "y"},
            cap=50,
        ) == ("b", "a", "x", "y")

        # Dedupe across new + previous (previous duplicate drops).
        assert merge_recently_added(
            new_paths=("a", "b"),
            previous_recent=("b", "x"),
            current_library_paths={"a", "b", "x"},
            cap=50,
        ) == ("b", "a", "x")

        # Dedupe within new (duplicate scanner results collapse).
        assert merge_recently_added(
            new_paths=("a", "a", "b"),
            previous_recent=(),
            current_library_paths={"a", "b"},
            cap=50,
        ) == ("b", "a")

        # Identical rescan: nothing new, previous entries preserved in order.
        assert merge_recently_added(
            new_paths=(),
            previous_recent=("b", "a"),
            current_library_paths={"a", "b"},
            cap=50,
        ) == ("b", "a")

        # Cap: preserved entries survive up to the cap after new paths.
        assert merge_recently_added(
            new_paths=("a", "b", "c"),
            previous_recent=("d", "e", "f"),
            current_library_paths={"a", "b", "c", "d", "e", "f"},
            cap=4,
        ) == ("c", "b", "a", "d")

        # Cap applies to preserved previous entries too.
        assert merge_recently_added(
            new_paths=(),
            previous_recent=("a", "b", "c"),
            current_library_paths={"a", "b", "c"},
            cap=2,
        ) == ("a", "b")

        # Removal by library membership: dropped tracks fall out.
        assert merge_recently_added(
            new_paths=(),
            previous_recent=("a", "b"),
            current_library_paths={"a"},
            cap=50,
        ) == ("a",)

        # Empty new + empty previous -> empty.
        assert merge_recently_added((), (), set(), 50) == ()

        # Empty previous with new paths -> just the new paths.
        assert merge_recently_added(
            new_paths=("a",),
            previous_recent=("gone",),
            current_library_paths={"a"},
            cap=50,
        ) == ("a",)


class TestBridgeFavoritesHistory:
    def test_bridge_rows_and_toggle(self, tmp_path):
        p1, p2, p3 = _write_tracks(tmp_path, ("one.mp3", "two.mp3", "three.mp3"))
        scanner = FakeScanner([p1, p2])
        library, queue, session, audio = _make_library_and_queue(
            scanner, extractor=FakeExtractor()
        )
        library.scan(str(tmp_path))
        bridge = LibraryBridge(library)
        bridge.toggle_favorite(str(p1))
        assert str(p1) in bridge.property("favoritePaths")
        assert bridge.property("favoriteRows") == [
            {"displayName": "T one", "path": str(p1)}
        ]
        queue.add(p1)
        session.play_queue_index(0)
        audio.trigger_media_accepted(p1)
        assert bridge.property("historyRows") == [
            {"displayName": "T one", "path": str(p1)}
        ]
        scanner.paths = [p1, p2, p3]
        library.scan(str(tmp_path))
        # Contract change (LOCAL-STABILIZATION-01.6.5): this assertion
        # previously encoded the delta-rebuild rule (recently added == ONLY
        # the new paths). Canonical: new first, then preserved entries —
        # [T three, T two, T one].
        assert bridge.property("recentlyAddedRows") == [
            {"displayName": "T three", "path": str(p3)},
            {"displayName": "T two", "path": str(p2)},
            {"displayName": "T one", "path": str(p1)},
        ]
        bridge.dispose()

    def test_song_paths_parallel_to_files(self, tmp_path):
        p1, p2 = _write_tracks(tmp_path, ("one.mp3", "two.mp3"))
        library, _, _, _ = _make_library_and_queue(FakeScanner([p1, p2]))
        library.scan(str(tmp_path))
        bridge = LibraryBridge(library)
        files = bridge.property("files")
        song_paths = bridge.property("songPaths")
        assert len(song_paths) == len(files) == 2
        assert song_paths[0] == str(p1)
        bridge.dispose()

    def test_missing_paths_skipped_in_rows(self, tmp_path):
        p1 = tmp_path / "one.mp3"
        p1.write_bytes(b"x")
        library, _, _, _ = _make_library_and_queue(FakeScanner([p1]))
        library.scan(str(tmp_path))
        bridge = LibraryBridge(library)
        ghost = tmp_path / "ghost.mp3"
        bridge.toggle_favorite(str(ghost))
        assert str(ghost) in bridge.property("favoritePaths")
        assert bridge.property("favoriteRows") == []
        bridge.dispose()


class _ValidatingScanner(FakeScanner):
    """FakeScanner whose validate_file raises a per-path error (TD-013)."""

    def __init__(self, paths=None, validate_errors=None) -> None:
        super().__init__(paths)
        self.validate_errors = validate_errors or {}

    def validate_file(self, path):
        error = self.validate_errors.get(path)
        if error is not None:
            raise error
        return None


class TestReferencePersistenceAudit:
    """LOCAL-STABILIZATION-01.6.6 audit: favorites/history/recently-added are
    REFERENCE PERSISTENCE — they survive library membership changes and
    filesystem unavailability, and are never erased by scans, missing-track
    removal, or scan failures. Current library membership is
    LibraryState.tracks; missing files fall out of the derived views
    (favoriteRows/historyRows/recentlyAddedRows) but not of the persisted
    reference tuples (favoritePaths/historyPaths/recentlyAddedPaths)."""

    def test_favorite_survives_missing_track_activation(self, tmp_path):
        """TD-013: activating a favorite whose file vanished must NOT erase
        identity or the persisted reference — the membership is preserved
        and marked MISSING."""
        p1 = tmp_path / "one.mp3"
        p1.write_bytes(b"x")
        scanner = _ValidatingScanner([p1])
        library, queue, session, _ = _make_library_and_queue(scanner)
        library.scan(str(tmp_path))
        library.toggle_favorite(p1)
        assert str(p1) in library.state.favorite_paths
        scanner.validate_errors = {
            p1: LibraryFilesystemError(LibraryDiagnosticCode.TRACK_MISSING, p1)
        }
        # TD-013 validation stays LibraryService-owned (M4-R1 §33).
        # M6-EXT-R4 freeze gate §10: play-missing NEVER removes identity —
        # the membership is PRESERVED and marked MISSING.
        track = library.state.tracks[0]
        assert library.validate_track_for_playback(track) is False
        assert len(library.state.tracks) == 1  # membership preserved
        assert library.state.tracks[0].availability.value == "missing"
        assert str(p1) in library.state.favorite_paths  # reference preserved
        assert library.state.diagnostic is not None
        assert library.state.diagnostic.code is LibraryDiagnosticCode.TRACK_MISSING
        assert queue.state.tracks == []
        assert session.state.current_index == -1  # queue untouched

    def test_favorites_and_history_survive_identical_rescan(self, tmp_path):
        """An identical rescan must not erase favorites or play history;
        recently added preservation is the LOCAL-STABILIZATION-01.6.5 rule
        and is pinned here too."""
        p1, p2 = _write_tracks(tmp_path, ("one.mp3", "two.mp3"))
        scanner = FakeScanner([p1, p2])
        library, queue, session, audio = _make_library_and_queue(scanner)
        library.scan(str(tmp_path))
        library.toggle_favorite(p1)
        queue.add(p1)
        session.play_queue_index(0)
        audio.trigger_media_accepted(p1)
        favorites_before = library.state.favorite_paths
        history_before = library.state.history_paths
        recent_before = library.state.recently_added_paths
        assert str(p1) in favorites_before
        assert str(p1) in history_before
        scanner.paths = [p1, p2]  # identical rescan
        library.scan(str(tmp_path))
        assert library.state.favorite_paths == favorites_before
        assert library.state.history_paths == history_before
        assert library.state.recently_added_paths == recent_before

    def test_failed_scan_preserves_favorites_and_history(self, tmp_path):
        """Scan failure (filesystem unavailable) must not erase the persisted
        references; recently added is covered by 6.5 — favorites and history
        are pinned here."""
        p1, p2 = _write_tracks(tmp_path, ("one.mp3", "two.mp3"))
        scanner = FailingScanner([p1, p2])
        library, queue, session, audio = _make_library_and_queue(scanner)
        library.scan(str(tmp_path))
        library.toggle_favorite(p1)
        queue.add(p1)
        session.play_queue_index(0)
        audio.trigger_media_accepted(p1)
        favorites_before = library.state.favorite_paths
        history_before = library.state.history_paths
        recent_before = library.state.recently_added_paths
        scanner.scan_error = LibraryFilesystemError(
            LibraryDiagnosticCode.IO_FAILURE, tmp_path, "i/o error"
        )
        library.scan(str(tmp_path))
        assert library.state.favorite_paths == favorites_before
        assert library.state.history_paths == history_before
        assert library.state.recently_added_paths == recent_before

    def test_missing_favorite_row_hidden_but_persisted(self, tmp_path):
        """Bridge view: a favorite whose file is not in the library stays in
        favoritePaths (persisted reference) but is excluded from favoriteRows
        (membership-derived view)."""
        p1 = tmp_path / "one.mp3"
        p1.write_bytes(b"x")
        library, _, _, _ = _make_library_and_queue(FakeScanner())  # never scanned
        library.toggle_favorite(p1)
        bridge = LibraryBridge(library)
        assert str(p1) in bridge.property("favoritePaths")
        assert bridge.property("favoriteRows") == []
        bridge.dispose()


class TestSqliteRepository:
    def test_repo_round_trip(self, tmp_path):
        db = tmp_path / "settings.db"
        prefs = LibraryPrefs(
            favorite_paths=("/music/a.mp3", "/music/b.mp3"),
            history_paths=("/music/h.mp3",),
            recently_added_paths=("/music/r.mp3",),
        )
        SqliteLibraryPrefsRepository(db).save(prefs)
        repo2 = SqliteLibraryPrefsRepository(db)
        assert repo2.load() == prefs

    def test_repo_empty_on_fresh_db(self, tmp_path):
        db = tmp_path / "settings.db"
        repo = SqliteLibraryPrefsRepository(db)
        assert repo.load() == LibraryPrefs()

    def test_repo_missing_file_returns_empty(self, tmp_path):
        db = tmp_path / "settings.db"
        repo = SqliteLibraryPrefsRepository(db)
        assert repo.load() == LibraryPrefs()  # never raises

    def test_repo_does_not_touch_settings_table(self, tmp_path):
        db = tmp_path / "settings.db"
        conn = sqlite3.connect(str(db))
        conn.execute(
            "CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        conn.execute("INSERT INTO settings VALUES ('volume', '80')")
        conn.commit()
        conn.close()
        repo = SqliteLibraryPrefsRepository(db)
        repo.save(LibraryPrefs(favorite_paths=("/music/a.mp3",)))
        conn = sqlite3.connect(str(db))
        try:
            settings_rows = conn.execute(
                "SELECT key, value FROM settings ORDER BY key"
            ).fetchall()
            assert settings_rows == [("volume", "80")]
            prefs_rows = conn.execute(
                "SELECT key FROM library_prefs ORDER BY key"
            ).fetchall()
            assert [k for (k,) in prefs_rows] == [
                "favorites",
                "history",
                "recently_added",
            ]
        finally:
            conn.close()


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(sys.argv)
    yield app


class TestQmlSmoke:
    def test_library_view_loads_with_new_tabs(self, qapp, tmp_path):
        p1 = tmp_path / "one.mp3"
        p1.write_bytes(b"x")
        library, _, _, _ = _make_library_and_queue(
            FakeScanner([p1]), extractor=FakeExtractor()
        )
        library.scan(str(tmp_path))
        bridge = LibraryBridge(library)
        engine = QQmlEngine()
        engine.addImportPath(str(QML_DIR))
        engine.rootContext().setContextProperty("library", bridge)
        component = QQmlComponent(engine, str(QML_DIR / "views/LibraryView.qml"))
        errs = "; ".join(e.toString() for e in component.errors())
        assert component.status() == QQmlComponent.Ready, f"LibraryView: {errs}"
        obj = component.create()
        assert obj is not None, "LibraryView: null object"
        obj.deleteLater()
        bridge.dispose()
