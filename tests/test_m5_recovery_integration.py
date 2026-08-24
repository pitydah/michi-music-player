"""M5.C7 recovery/LKG integration for the new durable state — RED/GREEN tests.

Contract (M5 spec §35-38, §47): the session snapshot, theme, and
window_geometry rows live in the SAME settings key/value table as the
classic settings, so they must participate in last-known-good logical-row
equality automatically. The session row (key "session_snapshot", written by
SqliteSessionRepository) is part of the full row set compared by
_candidate_matches_lkg; a candidate staged from an OLDER LKG with a
different session/theme must be REJECTED (provenance fail-closed), and the
CURRENT LKG's state becomes authoritative.

These tests reuse the test_persistence_recovery_install.py patterns:
_make_healthy_with_lkg, corrupt-primary construction with sidecar removal,
and quarantine assertions. The M11.2 machinery itself is untouched — the
assertions below encode the EXACT current behavior of the recovery flow.

Discriminator note (tests 2/3): the current M11.2 recovery fails CLOSED on
a pre-existing stale candidate (PersistenceStartupError; the stale candidate
is preserved as untrusted material, the corrupt primary is untouched) rather
than re-staging in the same call. Each discriminator therefore runs two
phases: (1) the stale candidate is rejected, proving the differing row
participates in candidate/LKG equivalence; (2) after the stale candidate is
cleared, recovery from the CURRENT LKG succeeds and its state is
authoritative. If the differing row were NOT part of the comparison, phase 1
would install the stale candidate instead of raising — that is the exact
failure these tests discriminate against.
"""

import json
import os
import sqlite3
from pathlib import Path

import pytest

from michi.domain.persistence_health import PersistenceHealth
from michi.domain.queue import RepeatMode
from michi.domain.session import (
    FORMAT_VERSION,
    PersistedQueueEntry,
    PersistedSessionContext,
    PlaybackSessionSnapshot,
    fresh_snapshot,
)
from michi.domain.settings import SettingsState
from michi.infrastructure.session_repository import SqliteSessionRepository
from michi.infrastructure.sqlite_settings import (
    PersistenceStartupError,
    SQLiteSettingsRepository,
)

_SESSION_KEY = "session_snapshot"

_V1_SETTINGS_ROWS = [
    ("schema_version", "1"),
    ("volume", "42"),
    ("muted", "true"),
    ("last_directory", "/m"),
    ("recent_files", json.dumps(["a.mp3", "b.mp3"])),
]


def _snapshot(label: str) -> PlaybackSessionSnapshot:
    """A valid, full playback session snapshot whose identity is label-tagged."""
    entries = (
        PersistedQueueEntry(file_path=f"/tracks/{label}-1.mp3", title=f"{label} One"),
        PersistedQueueEntry(file_path=f"/tracks/{label}-2.mp3", title=f"{label} Two"),
    )
    return PlaybackSessionSnapshot(
        format_version=FORMAT_VERSION,
        queue_entries=entries,
        context=PersistedSessionContext(
            context_type="queue", source_id=None, entries=entries, current_index=1
        ),
        playback_path=f"/tracks/{label}-2.mp3",
        position_ms=234000,
        repeat_mode=RepeatMode.ALL,
        shuffle_enabled=True,
        shuffle_seed=4242,
    )


def _healthy_state(**overrides) -> SettingsState:
    fields = {
        "volume": 42,
        "muted": True,
        "last_directory": "/m",
        "recent_files": ["a.mp3", "b.mp3"],
    }
    fields.update(overrides)
    return SettingsState(**fields)


def _write_raw_rows(db_path, rows):
    """Fabricate DB state using controlled raw SQL (test-only)."""
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS settings ("
            "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        conn.executemany("INSERT OR REPLACE INTO settings VALUES (?, ?)", rows)


def _read_raw_settings(db_path):
    """Settings rows as a dict, read-only, without mutating the database."""
    uri = f"{db_path.resolve().as_uri()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        return dict(conn.execute("SELECT key, value FROM settings").fetchall())


def _remove_wal_sidecars(db_path):
    for suffix in ("-wal", "-shm"):
        sidecar = Path(str(db_path) + suffix)
        if sidecar.exists():
            sidecar.unlink()


def _make_healthy_with_lkg(db_path, state=None):
    """Healthy v1 primary + LKG (established helper pattern)."""
    repo = SQLiteSettingsRepository(db_path)
    repo.save(state or _healthy_state())
    diag = SQLiteSettingsRepository.refresh_last_known_good(db_path)
    assert diag.health is PersistenceHealth.HEALTHY
    return repo


def _corrupt_primary(db_path, payload=b"THIS IS NOT SQLITE"):
    """Overwrite the primary with garbage on a NEW inode (os.replace).

    A lingering WAL-mode connection from a preceding test in the same
    process may finalize (GC) after the corruption and checkpoint through
    its OLD inode, resurrecting a healthy DB over in-place write_bytes.
    Replacing the path with a fresh inode makes such close-time writes
    harmless (they land on the unlinked old inode)."""
    _remove_wal_sidecars(db_path)
    tmp = Path(str(db_path) + ".corrupt-tmp")
    tmp.write_bytes(payload)
    os.replace(tmp, db_path)
    return payload


def _quarantine_generations(db_path):
    """Sorted recovery-* generations under <db>.quarantine, if the root exists."""
    qroot = Path(str(db_path) + ".quarantine")
    if not qroot.is_dir():
        return []
    return sorted(p for p in qroot.iterdir() if p.name.startswith("recovery-"))


def _session_from(db_path) -> PlaybackSessionSnapshot:
    return SqliteSessionRepository(db_path).load()


def _stage_stale_candidate(old_lkg_bytes, old_db_path, candidate_path):
    """Stage a candidate from an OLDER LKG snapshot via the real staging helper.

    Fabricates an "old db" whose deterministic .lkg sibling holds the older
    LKG bytes, then stages from it into the real candidate path. This reuses
    stage_recovery_from_last_known_good() exactly as the contract requires
    ("call stage_recovery_from_last_known_good with the old lkg path into a
    candidate path").
    """
    old_db_path.write_bytes(b"unused - only the .lkg sibling matters")
    Path(str(old_db_path) + ".lkg").write_bytes(old_lkg_bytes)
    diag = SQLiteSettingsRepository.stage_recovery_from_last_known_good(
        old_db_path, candidate_path
    )
    assert diag.health is PersistenceHealth.HEALTHY
    return candidate_path


class TestLkgV1RecoveryPreservesSession:
    def test_lkg_v1_recovery_preserves_session(self, tmp_path):
        db = tmp_path / "michi.db"
        _make_healthy_with_lkg(db)
        assert _read_raw_settings(db)["schema_version"] == "1"
        session_a = _snapshot("A")
        SqliteSessionRepository(db).save(session_a)
        assert (
            SQLiteSettingsRepository.refresh_last_known_good(db).health
            is PersistenceHealth.HEALTHY
        )
        lkg = SQLiteSettingsRepository.last_known_good_path(db)
        # LKG captured the session snapshot AND the schema_version row.
        assert _session_from(lkg) == session_a
        assert _read_raw_settings(lkg)["schema_version"] == "1"
        lkg_bytes = lkg.read_bytes()

        corrupt = _corrupt_primary(db)
        recovered = SQLiteSettingsRepository.open_for_startup(db)

        assert isinstance(recovered, SQLiteSettingsRepository)
        assert (
            SQLiteSettingsRepository.inspect_path(db).health
            is PersistenceHealth.HEALTHY
        )
        # The session snapshot survived recovery; the schema stayed v1.
        assert _session_from(db) == session_a
        assert _read_raw_settings(db)["schema_version"] == "1"
        assert (
            _read_raw_settings(db)["session_snapshot"]
            == _read_raw_settings(lkg)["session_snapshot"]
        )
        # LKG preserved byte-exact; candidate consumed on success.
        assert lkg.read_bytes() == lkg_bytes
        assert not SQLiteSettingsRepository.recovery_candidate_path(db).exists()

        # The corrupt original was quarantined byte-exact as evidence.
        generations = _quarantine_generations(db)
        assert len(generations) == 1
        files = [p for p in generations[0].iterdir() if p.is_file()]
        assert len(files) == 1
        assert files[0].read_bytes() == corrupt


class TestSessionRowEquivalence:
    def test_session_row_participates_in_equivalence(self, tmp_path):
        db = tmp_path / "michi.db"
        _make_healthy_with_lkg(db)
        session_a = _snapshot("A")
        session_b = _snapshot("B")
        lkg = SQLiteSettingsRepository.last_known_good_path(db)

        # LKG generation 1 captures session A.
        SqliteSessionRepository(db).save(session_a)
        assert (
            SQLiteSettingsRepository.refresh_last_known_good(db).health
            is PersistenceHealth.HEALTHY
        )
        assert _session_from(lkg) == session_a
        old_lkg_bytes = lkg.read_bytes()

        # LKG generation 2 captures session B (current LKG).
        SqliteSessionRepository(db).save(session_b)
        assert (
            SQLiteSettingsRepository.refresh_last_known_good(db).health
            is PersistenceHealth.HEALTHY
        )
        assert _session_from(lkg) == session_b
        lkg_bytes = lkg.read_bytes()

        # Pre-stage a candidate from the OLD LKG, carrying session A.
        candidate = SQLiteSettingsRepository.recovery_candidate_path(db)
        _stage_stale_candidate(old_lkg_bytes, tmp_path / "old_michi.db", candidate)
        assert _session_from(candidate) == session_a

        corrupt = _corrupt_primary(db)

        # Phase 1 (discriminator): the stale candidate must be REJECTED.
        # If the session row were NOT part of the comparison, this stale
        # candidate (identical settings, different session) would pass
        # provenance and install with session A.
        with pytest.raises(PersistenceStartupError) as exc_info:
            SQLiteSettingsRepository.open_for_startup(db)
        assert (
            exc_info.value.primary_diagnostic.health
            is PersistenceHealth.CORRUPT_DATABASE
        )
        # Rejection is non-destructive: stale candidate and corrupt primary
        # are both preserved as untrusted/evidence material.
        assert candidate.exists()
        assert _session_from(candidate) == session_a
        assert db.read_bytes() == corrupt
        assert lkg.read_bytes() == lkg_bytes
        assert not Path(str(db) + ".quarantine").exists()

        # Phase 2: with the stale candidate cleared, the CURRENT LKG's
        # session B becomes authoritative.
        candidate.unlink()
        recovered = SQLiteSettingsRepository.open_for_startup(db)
        assert isinstance(recovered, SQLiteSettingsRepository)
        assert _session_from(db) == session_b
        assert (
            _read_raw_settings(db)["session_snapshot"]
            == _read_raw_settings(lkg)["session_snapshot"]
        )


class TestThemeGeometryEquivalence:
    def test_theme_geometry_rows_participate(self, tmp_path):
        db = tmp_path / "michi.db"
        # LKG generation 1: theme "dark" (the older state).
        _make_healthy_with_lkg(db, _healthy_state(theme="dark"))
        lkg = SQLiteSettingsRepository.last_known_good_path(db)
        assert _read_raw_settings(lkg)["theme"] == "dark"
        old_lkg_bytes = lkg.read_bytes()

        # LKG generation 2: theme "light" (the current LKG).
        repo = SQLiteSettingsRepository(db)
        repo.save(_healthy_state(theme="light"))
        assert (
            SQLiteSettingsRepository.refresh_last_known_good(db).health
            is PersistenceHealth.HEALTHY
        )
        assert _read_raw_settings(lkg)["theme"] == "light"
        lkg_bytes = lkg.read_bytes()

        # Pre-stage a candidate from the OLD LKG, carrying theme "dark".
        candidate = SQLiteSettingsRepository.recovery_candidate_path(db)
        _stage_stale_candidate(old_lkg_bytes, tmp_path / "old_michi.db", candidate)
        assert _read_raw_settings(candidate)["theme"] == "dark"

        corrupt = _corrupt_primary(db)

        # Phase 1 (discriminator): the stale theme must be REJECTED.
        with pytest.raises(PersistenceStartupError) as exc_info:
            SQLiteSettingsRepository.open_for_startup(db)
        assert (
            exc_info.value.primary_diagnostic.health
            is PersistenceHealth.CORRUPT_DATABASE
        )
        assert candidate.exists()
        assert _read_raw_settings(candidate)["theme"] == "dark"
        assert db.read_bytes() == corrupt
        assert lkg.read_bytes() == lkg_bytes
        assert not Path(str(db) + ".quarantine").exists()

        # Phase 2: the CURRENT LKG's theme "light" becomes authoritative.
        candidate.unlink()
        recovered = SQLiteSettingsRepository.open_for_startup(db)
        assert isinstance(recovered, SQLiteSettingsRepository)
        assert _read_raw_settings(db)["theme"] == "light"


class TestMalformedSessionRow:
    def test_malformed_session_row_does_not_break_recovery(self, tmp_path):
        db = tmp_path / "michi.db"
        _make_healthy_with_lkg(db)
        valid_session = _snapshot("VALID")
        # LKG holds a valid session.
        SqliteSessionRepository(db).save(valid_session)
        assert (
            SQLiteSettingsRepository.refresh_last_known_good(db).health
            is PersistenceHealth.HEALTHY
        )
        lkg = SQLiteSettingsRepository.last_known_good_path(db)
        assert _session_from(lkg) == valid_session

        # The primary alone now carries a malformed session row. A field-level
        # malformation stays HEALTHY per inspect_path (M11.2C field fallback),
        # so nothing here crashes — the corrupt primary is what routes to
        # recovery.
        garbage = "this is not a session snapshot"
        conn = sqlite3.connect(str(db))
        try:
            conn.execute(
                "INSERT INTO settings(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (_SESSION_KEY, garbage),
            )
            conn.commit()
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        finally:
            conn.close()
        assert (
            SQLiteSettingsRepository.inspect_path(db).health
            is PersistenceHealth.HEALTHY
        )

        corrupt = _corrupt_primary(db)
        recovered = SQLiteSettingsRepository.open_for_startup(db)

        # No crash: recovery succeeded, restoring the LKG truth.
        assert isinstance(recovered, SQLiteSettingsRepository)
        assert (
            SQLiteSettingsRepository.inspect_path(db).health
            is PersistenceHealth.HEALTHY
        )
        assert _session_from(db) == valid_session
        assert (
            _read_raw_settings(db)["session_snapshot"]
            == _read_raw_settings(lkg)["session_snapshot"]
        )

        # The malformed original (baked into the corrupt primary) is
        # quarantined byte-exact as evidence.
        generations = _quarantine_generations(db)
        assert len(generations) == 1
        files = [p for p in generations[0].iterdir() if p.is_file()]
        assert len(files) == 1
        assert files[0].read_bytes() == corrupt


class TestGarbageDbPolicy:
    def test_garbage_db_policy(self, tmp_path):
        """Garbage primary, NO LKG: controlled typed failure, evidence kept.

        Exact current behavior: the M11.2 preflight classifies the garbage
        primary CORRUPT_DATABASE, recovery requires a healthy LKG, and with
        none the flow raises PersistenceStartupError BEFORE staging or
        quarantining — the garbage file is never deleted or overwritten
        (evidence preserved in place), and no quarantine generation or
        recovery candidate is created.
        """
        db = tmp_path / "michi.db"
        garbage = _corrupt_primary(db)
        assert not SQLiteSettingsRepository.last_known_good_path(db).exists()
        assert not SQLiteSettingsRepository.recovery_candidate_path(db).exists()

        with pytest.raises(PersistenceStartupError) as exc_info:
            SQLiteSettingsRepository.open_for_startup(db)

        assert (
            exc_info.value.primary_diagnostic.health
            is PersistenceHealth.CORRUPT_DATABASE
        )
        # The garbage evidence is preserved byte-exact in place.
        assert db.read_bytes() == garbage
        assert not Path(str(db) + ".quarantine").exists()
        assert not SQLiteSettingsRepository.recovery_candidate_path(db).exists()

    def test_garbage_db_recovers_from_valid_lkg(self, tmp_path):
        """Garbage primary + valid LKG (with session): recovery preserves it."""
        db = tmp_path / "michi.db"
        _make_healthy_with_lkg(db)
        session = _snapshot("Z")
        SqliteSessionRepository(db).save(session)
        assert (
            SQLiteSettingsRepository.refresh_last_known_good(db).health
            is PersistenceHealth.HEALTHY
        )
        lkg = SQLiteSettingsRepository.last_known_good_path(db)
        assert _session_from(lkg) == session
        lkg_bytes = lkg.read_bytes()

        corrupt = _corrupt_primary(db)
        recovered = SQLiteSettingsRepository.open_for_startup(db)

        assert isinstance(recovered, SQLiteSettingsRepository)
        assert (
            SQLiteSettingsRepository.inspect_path(db).health
            is PersistenceHealth.HEALTHY
        )
        assert _session_from(db) == session
        assert _read_raw_settings(db)["schema_version"] == "1"
        assert lkg.read_bytes() == lkg_bytes
        assert not SQLiteSettingsRepository.recovery_candidate_path(db).exists()

        generations = _quarantine_generations(db)
        assert len(generations) == 1
        files = [p for p in generations[0].iterdir() if p.is_file()]
        assert len(files) == 1
        assert files[0].read_bytes() == corrupt


class TestV0LkgRecovery:
    def test_v0_lkg_recovery_migrates_then_session(self, tmp_path):
        db = tmp_path / "michi.db"
        # Healthy v0 primary: raw rows, no schema_version, no session.
        _write_raw_rows(
            db,
            [
                ("volume", "37"),
                ("muted", "true"),
                ("last_directory", "/music"),
                ("recent_files", json.dumps(["a.mp3", "b.mp3"])),
            ],
        )
        assert (
            SQLiteSettingsRepository.refresh_last_known_good(db).health
            is PersistenceHealth.HEALTHY
        )
        lkg = SQLiteSettingsRepository.last_known_good_path(db)
        assert "schema_version" not in _read_raw_settings(lkg)
        assert "session_snapshot" not in _read_raw_settings(lkg)

        _corrupt_primary(db)
        recovered = SQLiteSettingsRepository.open_for_startup(db)

        # The v0 LKG copy was installed, then the writable open migrated it.
        assert isinstance(recovered, SQLiteSettingsRepository)
        rows = _read_raw_settings(db)
        assert rows["schema_version"] == "1"
        assert rows["volume"] == "37"
        assert rows["muted"] == "true"
        # No session was ever persisted: fresh, never corruption.
        assert _session_from(db) == fresh_snapshot()
        assert "session_snapshot" not in _read_raw_settings(db)
