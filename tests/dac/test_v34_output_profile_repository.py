"""DAC-V35-030 — persistencia de output profile (gates §402/§0I).

Migration: fresh->v2, v1->v2 preservando filas, v2 sin tabla DAC ->
health/provenance failure, cache rebuildable, LKG conserva profiles +
selection, versión futura -> fail closed.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from michi.application.audio_output_profile_service import AudioOutputProfileService
from michi.domain.audio_evidence import (
    CapabilityEvidence,
    EvidenceStrength,
    PcmTuple,
)
from michi.domain.audio_output import (
    AudioOutputProfile,
    AudioOutputSelection,
    FallbackKind,
    OutputPathPreference,
    RatePolicy,
    VolumePolicy,
    stable_direct_preset,
)
from michi.infrastructure.sqlite_audio_output_repository import (
    SqliteAudioOutputRepository,
)
from michi.infrastructure.sqlite_settings import (
    CURRENT_SCHEMA_VERSION,
    SchemaVersionError,
    SQLiteSettingsRepository,
    _candidate_matches_lkg,
)

DEVICE = "usb:2622:0105:DX5ABC123"


def _create_db(path: Path, statements: tuple[str, ...]) -> None:
    conn = sqlite3.connect(str(path))
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS settings ("
            "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        for statement in statements:
            conn.execute(statement)
        conn.commit()
    finally:
        conn.close()


def _v1_db(path: Path) -> None:
    _create_db(
        path,
        (
            "INSERT INTO settings(key, value) VALUES('schema_version', '1')",
            "INSERT INTO settings(key, value) VALUES('volume', '42')",
        ),
    )


def _v2_db(path: Path, *, tables: tuple[str, ...]) -> None:
    statements = ["INSERT INTO settings(key, value) VALUES('schema_version', '2')"]
    if "profiles" in tables:
        statements.append(
            "CREATE TABLE audio_output_profiles (profile_id TEXT PRIMARY KEY, "
            "stable_device_id TEXT, path TEXT NOT NULL, rate_policy TEXT NOT NULL, "
            "volume_policy TEXT NOT NULL, fallback_kind TEXT NOT NULL, "
            "fallback_device_id TEXT, resync_delay_ms INTEGER NOT NULL DEFAULT 0, "
            "created_at_ms INTEGER NOT NULL, updated_at_ms INTEGER NOT NULL)"
        )
    if "selection" in tables:
        statements.append(
            "CREATE TABLE audio_output_selection (singleton INTEGER PRIMARY KEY, "
            "selected_profile_id TEXT, selected_device_id TEXT, "
            "updated_at_ms INTEGER NOT NULL)"
        )
    _create_db(path, tuple(statements))


def _table_names(path: Path) -> set[str]:
    conn = sqlite3.connect(str(path))
    try:
        return {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    finally:
        conn.close()


def _schema_version(path: Path) -> str:
    conn = sqlite3.connect(str(path))
    try:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = 'schema_version'"
        ).fetchone()
        return row[0]
    finally:
        conn.close()


# ── migration ─────────────────────────────────────────────────────────
def test_fresh_database_is_schema_v2(tmp_path: Path) -> None:
    db = tmp_path / "settings.db"
    SQLiteSettingsRepository(db)
    assert _schema_version(db) == "2"
    assert CURRENT_SCHEMA_VERSION == 2
    tables = _table_names(db)
    assert {"audio_output_profiles", "audio_output_selection"} <= tables
    assert "dac_qualification_cache" in tables


def test_v1_database_migrates_to_v2_preserving_rows(tmp_path: Path) -> None:
    db = tmp_path / "settings.db"
    _v1_db(db)
    SQLiteSettingsRepository(db)
    assert _schema_version(db) == "2"
    conn = sqlite3.connect(str(db))
    try:
        row = conn.execute("SELECT value FROM settings WHERE key = 'volume'").fetchone()
    finally:
        conn.close()
    assert row == ("42",), "la migración preserva las filas autoritativas previas"


def test_v2_missing_dac_table_is_health_failure(tmp_path: Path) -> None:
    db = tmp_path / "settings.db"
    _v2_db(db, tables=("profiles",))  # falta audio_output_selection
    diagnostic = SQLiteSettingsRepository.inspect_path(db)
    assert diagnostic.health.value == "malformed_data"
    assert "V2 DAC tables missing" in (diagnostic.message or "")


def test_future_schema_version_fails_closed(tmp_path: Path) -> None:
    db = tmp_path / "settings.db"
    _create_db(
        db,
        ("INSERT INTO settings(key, value) VALUES('schema_version', '99')",),
    )
    with pytest.raises(SchemaVersionError):
        SQLiteSettingsRepository(db)


def test_cache_loss_allows_rebuild_and_lkg_equality(tmp_path: Path) -> None:
    a, b = tmp_path / "a.db", tmp_path / "b.db"
    for path in (a, b):
        SQLiteSettingsRepository(path)
    repo_a = SqliteAudioOutputRepository(a)
    repo_a.replace_qualification_cache(
        DEVICE,
        (
            CapabilityEvidence(
                stable_device_id=DEVICE,
                tuple=PcmTuple(96000, "S32_LE", 2, 24),
                supported=True,
                strength=EvidenceStrength.OPENED,
                source="michi-alsa-probe",
                observed_at_ns=1,
                environment_fingerprint="fp",
                evidence_refs=("probe:1",),
            ),
        ),
    )
    assert _candidate_matches_lkg(a, b) is True, (
        "la cache rebuildable nunca invalida la provenance LKG"
    )


def test_lkg_equality_includes_profiles_and_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "michi.infrastructure.sqlite_audio_output_repository.time.time_ns",
        lambda: 1_000_000_000_000,
    )
    a, b = tmp_path / "a.db", tmp_path / "b.db"
    for path in (a, b):
        SQLiteSettingsRepository(path)
    repo_a = SqliteAudioOutputRepository(a)
    repo_a.save_profile(stable_direct_preset("p1", DEVICE))
    repo_a.save_selection(AudioOutputSelection("p1", DEVICE, 5))
    assert _candidate_matches_lkg(a, b) is False, (
        "profiles/selection son autoritativos: deben invalidar LKG"
    )
    repo_b = SqliteAudioOutputRepository(b)
    repo_b.save_profile(stable_direct_preset("p1", DEVICE))
    repo_b.save_selection(AudioOutputSelection("p1", DEVICE, 5))
    assert _candidate_matches_lkg(a, b) is True


# ── profiles / selection / cache ──────────────────────────────────────
def test_profile_round_trip(tmp_path: Path) -> None:
    db = tmp_path / "settings.db"
    SQLiteSettingsRepository(db)
    repo = SqliteAudioOutputRepository(db)
    profile = stable_direct_preset("p1", DEVICE)
    repo.save_profile(profile)
    loaded = repo.load_profiles()
    assert len(loaded) == 1
    assert loaded[0].profile_id == "p1"
    assert loaded[0].stable_device_id == DEVICE
    assert loaded[0].path is OutputPathPreference.HARDWARE_DIRECT
    assert loaded[0].rate_policy is RatePolicy.SOURCE_NATIVE
    assert loaded[0].volume_policy is VolumePolicy.FIXED
    assert loaded[0].fallback is FallbackKind.STOP
    assert loaded[0].resync_delay_ms == 0


def test_profile_upsert_does_not_duplicate(tmp_path: Path) -> None:
    db = tmp_path / "settings.db"
    SQLiteSettingsRepository(db)
    repo = SqliteAudioOutputRepository(db)
    profile = stable_direct_preset("p1", DEVICE)
    repo.save_profile(profile)
    repo.save_profile(profile)
    assert len(repo.load_profiles()) == 1


def test_unique_device_index_rejects_second_profile(tmp_path: Path) -> None:
    db = tmp_path / "settings.db"
    SQLiteSettingsRepository(db)
    repo = SqliteAudioOutputRepository(db)
    repo.save_profile(stable_direct_preset("p1", DEVICE))
    with pytest.raises(sqlite3.IntegrityError):
        repo.save_profile(stable_direct_preset("p2", DEVICE))


def test_schema_stores_no_card_index_columns(tmp_path: Path) -> None:
    db = tmp_path / "settings.db"
    SQLiteSettingsRepository(db)
    conn = sqlite3.connect(str(db))
    try:
        for table in ("audio_output_profiles", "audio_output_selection"):
            cols = {
                row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
            }
            assert not any("card" in col for col in cols), (
                f"{table} no debe almacenar índices de card"
            )
    finally:
        conn.close()


def test_selection_round_trip_and_default(tmp_path: Path) -> None:
    db = tmp_path / "settings.db"
    SQLiteSettingsRepository(db)
    repo = SqliteAudioOutputRepository(db)
    empty = repo.load_selection()
    assert empty.selected_profile_id is None and empty.selected_device_id is None
    repo.save_profile(stable_direct_preset("p1", DEVICE))
    repo.save_selection(AudioOutputSelection("p1", DEVICE, 7))
    loaded = repo.load_selection()
    assert loaded == AudioOutputSelection("p1", DEVICE, 7)


def test_selection_fk_rejects_unknown_profile(tmp_path: Path) -> None:
    db = tmp_path / "settings.db"
    SQLiteSettingsRepository(db)
    repo = SqliteAudioOutputRepository(db)
    with pytest.raises(sqlite3.IntegrityError):
        repo.save_selection(AudioOutputSelection("no-existe", DEVICE, 7))


def test_cache_round_trip_and_replace(tmp_path: Path) -> None:
    db = tmp_path / "settings.db"
    SQLiteSettingsRepository(db)
    repo = SqliteAudioOutputRepository(db)
    evidence = CapabilityEvidence(
        stable_device_id=DEVICE,
        tuple=PcmTuple(96000, "S32_LE", 2, 24),
        supported=True,
        strength=EvidenceStrength.OPENED,
        source="michi-alsa-probe",
        observed_at_ns=123,
        environment_fingerprint="fp-1",
        evidence_refs=("probe:1", "probe:2"),
    )
    repo.replace_qualification_cache(DEVICE, (evidence,))
    loaded = repo.load_qualification_cache(DEVICE)
    assert loaded == (evidence,)
    repo.replace_qualification_cache(DEVICE, ())
    assert repo.load_qualification_cache(DEVICE) == ()


def test_service_validates_invariants(tmp_path: Path) -> None:
    db = tmp_path / "settings.db"
    SQLiteSettingsRepository(db)
    service = AudioOutputProfileService(SqliteAudioOutputRepository(db))
    with pytest.raises(ValueError):
        service.save_profile(
            AudioOutputProfile(
                profile_id="p",
                stable_device_id=2,  # type: ignore[arg-type]
                path=OutputPathPreference.HARDWARE_DIRECT,
                rate_policy=RatePolicy.SOURCE_NATIVE,
                volume_policy=VolumePolicy.FIXED,
                allow_resample=False,
                allow_remix=False,
                allow_processing=False,
                fallback=FallbackKind.STOP,
            )
        )
    with pytest.raises(ValueError):
        service.save_profile(
            AudioOutputProfile(
                profile_id="p",
                stable_device_id=None,
                path=OutputPathPreference.HARDWARE_DIRECT,
                rate_policy=RatePolicy.SOURCE_NATIVE,
                volume_policy=VolumePolicy.FIXED,
                allow_resample=False,
                allow_remix=False,
                allow_processing=False,
                fallback=FallbackKind.SPECIFIC_DEVICE,
            )
        )
    service.save_profile(stable_direct_preset("p1", DEVICE))
    assert len(service.load_profiles()) == 1
