"""M6.3 incremental library engine — Phase-1 RED tests.

On the current baseline the module-level imports of the new domain symbols
(ScanClassification, classify_scan) fail at collection (ImportError) — that
IS the expected Phase-1 red evidence. The tests encode the target contract
and must pass once the M6.3 production changes land:

- michi/domain/library_index.py: ``ScanClassification`` + ``classify_scan``
  (pure classification of a scan delta against the known index entries)
- michi/application/ports.py: ``LibraryScannerPort`` gains ``fingerprint``
- michi/application/library_service.py: ``LibraryService.__init__`` gains
  ``library_index``; ``scan(directory)`` becomes INCREMENTAL when an index
  is wired: fingerprint -> classify -> extract ONLY added/modified ->
  reuse the index metadata for unchanged tracks (a reparse never happens)
  -> atomic commit with a single notify -> index upsert/remove. Without an
  index the CURRENT full-scan behavior is unchanged.

Coverage:
- Pure classification: added/modified/removed/unchanged, size vs mtime
  modification, empty known/discovered, deterministic ordering
- Incremental scan against a REAL SqliteLibraryIndexRepository and a scanner
  whose fingerprint reads real stat (file_size, mtime_ns)
- THE acceptance gate: an unchanged rescan performs ZERO extractions
- Golden add/modify/remove delta: extraction ONLY for the changed files, no
  removed references anywhere in the derived state, consistent counts
- Observable metadata reuse (index metadata wins for unchanged tracks) and
  re-extraction for modified tracks
- Failed scan AND failed fingerprinting: state + index preserved, diagnostic
  set (TD-013 semantics preserved on the incremental path)
- Full-scan compatibility regression guard (no index wired)
- Atomic commit: exactly ONE notify and the callback observes a COMPLETE
  state (never a half state)
"""

import os
import sqlite3

from michi.application.library_port import LibraryFilesystemError
from michi.application.library_service import LibraryService
from michi.application.playback_service import PlaybackService
from michi.application.queue_service import QueueService
from michi.domain.library import LibraryDiagnosticCode, TrackMetadata, make_track_id
from michi.domain.library_index import (
    LibraryIndexEntry,
    ScanClassification,
    classify_scan,
    encode_index_metadata,
)
from michi.infrastructure.library_index import SqliteLibraryIndexRepository
from tests.conftest import FakeAudioPort
from tests.test_library_metadata import FakeExtractor, FakeScanner


class StatScanner(FakeScanner):
    """FakeScanner whose fingerprint() reads the REAL stat.

    scan() returns the configured paths (or raises scan_error); fingerprint()
    returns (file_size, mtime_ns) from path.stat() — or raises the typed
    error registered for a path.
    """

    def __init__(self, paths=None, scan_error=None):
        super().__init__(paths)
        self.scan_error = scan_error
        self.fingerprint_errors = {}

    def scan(self, root):
        if self.scan_error is not None:
            raise self.scan_error
        return list(self.paths)

    def fingerprint(self, path):
        error = self.fingerprint_errors.get(path)
        if error is not None:
            raise error
        st = path.stat()
        return (st.st_size, st.st_mtime_ns)


class CountingExtractor:
    """Wraps a FakeExtractor and records every extracted path."""

    def __init__(self, factory=None) -> None:
        self.inner = FakeExtractor(factory=factory)
        self.calls = []

    def extract(self, file_path):
        self.calls.append(file_path)
        return self.inner.extract(file_path)


def _make_library(tmp_path, scanner, extractor, with_index=True):
    """Build LibraryService with a real queue; optionally wire the index."""
    audio = FakeAudioPort()
    playback = PlaybackService(audio)
    queue = QueueService(playback)
    if with_index:
        repo = SqliteLibraryIndexRepository(tmp_path / "michi.db")
        library = LibraryService(scanner, queue, extractor, library_index=repo)
        return library, repo
    library = LibraryService(scanner, queue, extractor)
    return library, None


def _bump_mtime(path, seconds=1) -> None:
    """Move the file's mtime forward deterministically (1s later)."""
    st = path.stat()
    new_ns = st.st_mtime_ns + seconds * 1_000_000_000
    os.utime(path, ns=(new_ns, new_ns))


def _entry(track_id, size, mtime_ns) -> LibraryIndexEntry:
    return LibraryIndexEntry(
        track_id=track_id,
        file_size=size,
        mtime_ns=mtime_ns,
        metadata=TrackMetadata(),
    )


class TestClassifyScan:
    """Pure delta classification (michi/domain/library_index.py)."""

    def test_classify_added_modified_removed_unchanged(self):
        known = {
            "a.mp3": _entry("a.mp3", 1, 1),
            "b.mp3": _entry("b.mp3", 2, 2),
            "c.mp3": _entry("c.mp3", 3, 3),
        }
        discovered = [("a.mp3", 1, 1), ("b.mp3", 9, 2), ("d.mp3", 4, 4)]

        result = classify_scan(known, discovered)

        assert isinstance(result, ScanClassification)
        assert result.added == ("d.mp3",)
        assert result.modified == ("b.mp3",)
        assert result.removed == ("c.mp3",)
        assert result.unchanged == ("a.mp3",)

    def test_classify_modified_by_size(self):
        known = {"a.mp3": _entry("a.mp3", 1, 100)}

        result = classify_scan(known, [("a.mp3", 2, 100)])

        assert result.modified == ("a.mp3",)
        assert result.unchanged == ()
        assert result.added == ()
        assert result.removed == ()

    def test_classify_modified_by_mtime(self):
        known = {"a.mp3": _entry("a.mp3", 1, 100)}

        result = classify_scan(known, [("a.mp3", 1, 200)])

        assert result.modified == ("a.mp3",)
        assert result.unchanged == ()
        assert result.added == ()
        assert result.removed == ()

    def test_classify_empty_known_all_added(self):
        result = classify_scan({}, [("a.mp3", 1, 1), ("b.mp3", 2, 2)])

        assert result.added == ("a.mp3", "b.mp3")
        assert result.unchanged == ()
        assert result.modified == ()
        assert result.removed == ()

    def test_classify_empty_discovered_all_removed(self):
        # Known insertion order is deliberately NOT sorted.
        known = {"b.mp3": _entry("b.mp3", 2, 2), "a.mp3": _entry("a.mp3", 1, 1)}

        result = classify_scan(known, [])

        assert result.removed == ("a.mp3", "b.mp3")  # sorted by track_id
        assert result.added == ()
        assert result.modified == ()
        assert result.unchanged == ()

    def test_classify_deterministic_orders(self):
        known = {
            "a.mp3": _entry("a.mp3", 1, 1),
            "b.mp3": _entry("b.mp3", 2, 2),
            "c.mp3": _entry("c.mp3", 3, 3),
            "zeta.mp3": _entry("zeta.mp3", 9, 9),
            "alpha.mp3": _entry("alpha.mp3", 8, 8),
        }
        discovered = [
            ("d.mp3", 4, 4),
            ("b.mp3", 9, 2),
            ("a.mp3", 1, 1),
            ("e.mp3", 5, 5),
            ("c.mp3", 3, 3),
        ]

        result = classify_scan(known, discovered)

        assert result.added == ("d.mp3", "e.mp3")  # discovered order
        assert result.unchanged == ("a.mp3", "c.mp3")  # discovered order
        assert result.modified == ("b.mp3",)
        assert result.removed == ("alpha.mp3", "zeta.mp3")  # sorted by track_id


class TestIncrementalScan:
    """Service-level incremental scan against a real index repository."""

    def test_initial_scan_populates_index_and_extracts_all(self, tmp_path):
        music = tmp_path / "music"
        music.mkdir()
        a = music / "a.mp3"
        b = music / "b.mp3"
        c = music / "c.mp3"
        for p in (a, b, c):
            p.write_bytes(b"x")
        scanner = StatScanner([a, b, c])
        extractor = CountingExtractor()
        library, repo = _make_library(tmp_path, scanner, extractor)

        library.scan(str(music))

        assert extractor.calls == [a, b, c]  # every path extracted (full scan)
        assert [t.file_path for t in library.state.tracks] == [a, b, c]
        assert [t.title for t in library.state.tracks] == ["T a", "T b", "T c"]
        loaded = repo.load_all()
        assert len(loaded) == 3
        assert {e.track_id for e in loaded} == {make_track_id(p) for p in (a, b, c)}
        assert (
            next(e for e in loaded if e.track_id == make_track_id(a)).metadata.title
            == "T a"
        )

    def test_unchanged_rescan_no_reparse(self, tmp_path):
        music = tmp_path / "music"
        music.mkdir()
        a = music / "a.mp3"
        b = music / "b.mp3"
        c = music / "c.mp3"
        for p in (a, b, c):
            p.write_bytes(b"x")
        scanner = StatScanner([a, b, c])
        extractor = CountingExtractor()
        library, repo = _make_library(tmp_path, scanner, extractor)
        library.scan(str(music))
        before_tracks = tuple(library.state.tracks)
        before_albums = library.state.albums
        before_rows = repo.load_all()

        extractor.calls.clear()
        library.scan(str(music))

        # THE acceptance gate: an unchanged rescan performs ZERO extractions.
        assert extractor.calls == []
        assert tuple(library.state.tracks) == before_tracks
        assert library.state.albums == before_albums
        assert repo.load_all() == before_rows

    def test_incremental_add_modified_remove(self, tmp_path):
        music = tmp_path / "music"
        music.mkdir()
        a = music / "a.mp3"
        b = music / "b.mp3"
        c = music / "c.mp3"
        for p in (a, b, c):
            p.write_bytes(b"x")

        def factory(path):
            stem = path.stem
            return TrackMetadata(
                title="Title " + stem,
                artist="Artist " + stem,
                album="Album " + stem,
                duration_ms=1000,
                genre="Genre " + stem,
                composer="Composer " + stem,
            )

        scanner = StatScanner([a, b, c])
        extractor = CountingExtractor(factory=factory)
        library, repo = _make_library(tmp_path, scanner, extractor)
        library.scan(str(music))
        assert len(repo.load_all()) == 3

        # Mutate the library: add D, modify B, remove C.
        d = music / "d.mp3"
        d.write_bytes(b"x")
        _bump_mtime(b)
        c.unlink()
        scanner.paths = [a, b, d]

        extractor.calls.clear()
        library.scan(str(music))

        # The golden delta: extraction ONLY for modified B and added D.
        assert set(extractor.calls) == {b, d}
        assert [t.file_path for t in library.state.tracks] == [a, b, d]
        assert [e.track_id for e in repo.load_all()] == sorted(
            make_track_id(p) for p in (a, b, d)
        )
        # NO C references anywhere in the derived state.
        album_paths = [tp for album in library.state.albums for tp in album.track_paths]
        assert c not in album_paths
        assert all(c.name not in str(tp) for tp in album_paths)
        assert c.name not in str(library.state.folders)
        assert "Artist c" not in [ar.name for ar in library.state.artists]
        assert "Album c" not in [al.title for al in library.state.albums]
        assert "Genre c" not in [g.name for g in library.state.genres]
        assert "Composer c" not in [co.name for co in library.state.composers]
        # Derived counts are consistent with the 3-track library.
        assert (
            sum(al.track_count for al in library.state.albums)
            == len(library.state.tracks)
            == 3
        )
        assert sum(ar.track_count for ar in library.state.artists) == 3
        assert sum(g.track_count for g in library.state.genres) == 3
        assert sum(co.track_count for co in library.state.composers) == 3
        assert sum(f.track_count for f in library.state.folders) == 3
        # recently_added keeps its delta semantics (new paths from the delta).
        assert str(d) in library.state.recently_added_paths
        assert str(c) not in library.state.recently_added_paths

    def test_unchanged_reuses_index_metadata(self, tmp_path):
        music = tmp_path / "music"
        music.mkdir()
        a = music / "a.mp3"
        b = music / "b.mp3"
        a.write_bytes(b"x")
        b.write_bytes(b"x")
        scanner = StatScanner([a, b])
        extractor = CountingExtractor()
        library, repo = _make_library(tmp_path, scanner, extractor)
        library.scan(str(music))
        assert next(t for t in library.state.tracks if t.file_path == a).title == "T a"

        # Manually edit A's index row (fingerprint columns untouched): the
        # index now claims a DIFFERENT title than the extractor would give.
        with sqlite3.connect(str(tmp_path / "michi.db")) as conn:
            conn.execute(
                "UPDATE library_index SET metadata = ? WHERE track_id = ?",
                (
                    encode_index_metadata(
                        TrackMetadata(
                            title="EDITED", artist="A", album="B", duration_ms=1234
                        )
                    ),
                    make_track_id(a),
                ),
            )

        extractor.calls.clear()
        library.scan(str(music))

        # The OBSERVABLE reuse: A was NOT re-extracted — its TrackRef comes
        # from the index metadata (the extractor would have said "T a").
        assert extractor.calls == []
        a_ref = next(t for t in library.state.tracks if t.file_path == a)
        assert a_ref.title == "EDITED"
        assert len(repo.load_all()) == 2

    def test_modified_re_extracts_metadata(self, tmp_path):
        music = tmp_path / "music"
        music.mkdir()
        a = music / "a.mp3"
        b = music / "b.mp3"
        a.write_bytes(b"x")
        b.write_bytes(b"x")
        scanner = StatScanner([a, b])
        extractor = CountingExtractor()
        library, repo = _make_library(tmp_path, scanner, extractor)
        library.scan(str(music))

        # Modify B on disk AND plant stale metadata in the index.
        _bump_mtime(b)
        with sqlite3.connect(str(tmp_path / "michi.db")) as conn:
            conn.execute(
                "UPDATE library_index SET metadata = ? WHERE track_id = ?",
                (
                    encode_index_metadata(
                        TrackMetadata(
                            title="STALE", artist="A", album="B", duration_ms=1234
                        )
                    ),
                    make_track_id(b),
                ),
            )

        extractor.calls.clear()
        library.scan(str(music))

        assert set(extractor.calls) == {b}  # only the modified track re-extracted
        b_ref = next(t for t in library.state.tracks if t.file_path == b)
        assert b_ref.title == "T b"  # fresh extraction, NOT the stale index value
        row = next(e for e in repo.load_all() if e.track_id == make_track_id(b))
        assert row.metadata.title == "T b"  # index upserted with fresh metadata

    def test_incremental_failed_scan_preserves_everything(self, tmp_path):
        music = tmp_path / "music"
        music.mkdir()
        a = music / "a.mp3"
        b = music / "b.mp3"
        a.write_bytes(b"x")
        b.write_bytes(b"x")
        scanner = StatScanner([a, b])
        extractor = CountingExtractor()
        library, repo = _make_library(tmp_path, scanner, extractor)
        library.scan(str(music))
        before = (
            tuple(library.state.tracks),
            library.state.albums,
            library.state.artists,
            library.state.genres,
            library.state.composers,
            library.state.folders,
        )
        before_rows = repo.load_all()

        missing = music / "gone"
        scanner.scan_error = LibraryFilesystemError(
            LibraryDiagnosticCode.DIRECTORY_MISSING, path=missing, detail="gone"
        )
        library.scan(str(missing))

        assert library.state.diagnostic is not None
        assert library.state.diagnostic.code is LibraryDiagnosticCode.DIRECTORY_MISSING
        assert (
            tuple(library.state.tracks),
            library.state.albums,
            library.state.artists,
            library.state.genres,
            library.state.composers,
            library.state.folders,
        ) == before
        assert repo.load_all() == before_rows  # no partial index writes

    def test_scan_without_index_full_behavior(self, tmp_path):
        music = tmp_path / "music"
        music.mkdir()
        a = music / "a.mp3"
        b = music / "b.mp3"
        a.write_bytes(b"x")
        b.write_bytes(b"x")
        scanner = StatScanner([a, b])
        extractor = CountingExtractor()
        library, repo = _make_library(tmp_path, scanner, extractor, with_index=False)
        assert repo is None

        library.scan(str(music))

        assert extractor.calls == [a, b]  # every path extracted (full-scan compat)
        assert [t.file_path for t in library.state.tracks] == [a, b]
        assert sum(al.track_count for al in library.state.albums) == len(
            library.state.tracks
        )

    def test_atomic_commit_single_notify_complete_state(self, tmp_path):
        music = tmp_path / "music"
        music.mkdir()
        a = music / "a.mp3"
        b = music / "b.mp3"
        c = music / "c.mp3"
        for p in (a, b, c):
            p.write_bytes(b"x")
        scanner = StatScanner([a, b, c])
        extractor = CountingExtractor()
        library, _ = _make_library(tmp_path, scanner, extractor)
        library.scan(str(music))

        snapshots = []

        def observe():
            s = library.state
            snapshots.append((len(s.tracks), sum(al.track_count for al in s.albums)))

        library.subscribe_changed(observe)

        d = music / "d.mp3"
        d.write_bytes(b"x")
        _bump_mtime(b)
        c.unlink()
        scanner.paths = [a, b, d]
        library.scan(str(music))

        assert len(snapshots) == 1  # exactly ONE notify for the transition
        tracks_len, album_sum = snapshots[0]
        assert tracks_len == 3
        assert album_sum == tracks_len  # COMPLETE state, never a half state

    def test_fingerprint_typed_error(self, tmp_path):
        music = tmp_path / "music"
        music.mkdir()
        a = music / "a.mp3"
        b = music / "b.mp3"
        a.write_bytes(b"x")
        b.write_bytes(b"x")
        scanner = StatScanner([a, b])
        extractor = CountingExtractor()
        library, repo = _make_library(tmp_path, scanner, extractor)
        library.scan(str(music))
        before_tracks = tuple(library.state.tracks)
        before_rows = repo.load_all()

        # Fingerprinting A now fails with a typed filesystem error.
        scanner.fingerprint_errors = {
            a: LibraryFilesystemError(
                LibraryDiagnosticCode.ACCESS_FAILURE, a, "permission denied"
            )
        }
        library.scan(str(music))

        # The scan wraps fingerprint errors like scan errors: preserve state,
        # set the diagnostic from the raised error's code.
        assert library.state.diagnostic is not None
        assert library.state.diagnostic.code is LibraryDiagnosticCode.ACCESS_FAILURE
        assert tuple(library.state.tracks) == before_tracks
        assert repo.load_all() == before_rows  # no partial index writes
