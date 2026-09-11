"""DAC-V35-030 — SqliteAudioOutputRepository (spec §402/§0I).

Persiste en la MISMA base SQLite del settings (schema v2):
- audio_output_profiles / audio_output_selection: estado autoritativo;
- dac_qualification_cache: evidencia rebuildable (excluida de LKG).

Ningún índice de card ALSA se guarda: solo stable_device_id.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

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
)

_PROFILE_COLUMNS = (
    "profile_id, stable_device_id, path, rate_policy, volume_policy, "
    "fallback_kind, fallback_device_id, resync_delay_ms"
)


class SqliteAudioOutputRepository:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path), timeout=0.2)
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    # ── profiles ──────────────────────────────────────────────────────
    def load_profiles(self) -> tuple[AudioOutputProfile, ...]:
        conn = self._connect()
        try:
            rows = conn.execute(
                f"SELECT {_PROFILE_COLUMNS} FROM audio_output_profiles "
                "ORDER BY profile_id"
            ).fetchall()
        finally:
            conn.close()
        return tuple(self._profile_from_row(row) for row in rows)

    def save_profile(self, profile: AudioOutputProfile) -> None:
        now_ms = time.time_ns() // 1_000_000
        conn = self._connect()
        try:
            conn.execute(
                """
                INSERT INTO audio_output_profiles
                    (profile_id, stable_device_id, path, rate_policy,
                     volume_policy, fallback_kind, fallback_device_id,
                     resync_delay_ms, created_at_ms, updated_at_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(profile_id) DO UPDATE SET
                    stable_device_id = excluded.stable_device_id,
                    path = excluded.path,
                    rate_policy = excluded.rate_policy,
                    volume_policy = excluded.volume_policy,
                    fallback_kind = excluded.fallback_kind,
                    fallback_device_id = excluded.fallback_device_id,
                    resync_delay_ms = excluded.resync_delay_ms,
                    updated_at_ms = excluded.updated_at_ms
                """,
                (
                    profile.profile_id,
                    profile.stable_device_id,
                    profile.path.value,
                    profile.rate_policy.value,
                    profile.volume_policy.value,
                    profile.fallback.value,
                    profile.fallback_device_id,
                    profile.resync_delay_ms,
                    now_ms,
                    now_ms,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _profile_from_row(row: tuple) -> AudioOutputProfile:
        (
            profile_id,
            stable_device_id,
            path,
            rate_policy,
            volume_policy,
            fallback_kind,
            fallback_device_id,
            resync_delay_ms,
        ) = row
        return AudioOutputProfile(
            profile_id=profile_id,
            stable_device_id=stable_device_id,
            path=OutputPathPreference(path),
            rate_policy=RatePolicy(rate_policy),
            volume_policy=VolumePolicy(volume_policy),
            allow_resample=False,
            allow_remix=False,
            allow_processing=False,
            fallback=FallbackKind(fallback_kind),
            fallback_device_id=fallback_device_id,
            resync_delay_ms=int(resync_delay_ms),
        )

    # ── selection ─────────────────────────────────────────────────────
    def load_selection(self) -> AudioOutputSelection:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT selected_profile_id, selected_device_id, updated_at_ms "
                "FROM audio_output_selection WHERE singleton = 1"
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return AudioOutputSelection(None, None, 0)
        return AudioOutputSelection(row[0], row[1], int(row[2]))

    def save_selection(self, selection: AudioOutputSelection) -> None:
        conn = self._connect()
        try:
            conn.execute(
                """
                INSERT INTO audio_output_selection
                    (singleton, selected_profile_id, selected_device_id,
                     updated_at_ms)
                VALUES (1, ?, ?, ?)
                ON CONFLICT(singleton) DO UPDATE SET
                    selected_profile_id = excluded.selected_profile_id,
                    selected_device_id = excluded.selected_device_id,
                    updated_at_ms = excluded.updated_at_ms
                """,
                (
                    selection.selected_profile_id,
                    selection.selected_device_id,
                    selection.updated_at_ms,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    # ── qualification cache (rebuildable) ─────────────────────────────
    def load_qualification_cache(
        self, stable_device_id: str
    ) -> tuple[CapabilityEvidence, ...]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT stable_device_id, environment_fingerprint, rate_hz, "
                "transport_format, channels, significant_bits, supported, "
                "strength, source, observed_at_ns, evidence_json "
                "FROM dac_qualification_cache WHERE stable_device_id = ? "
                "ORDER BY rate_hz, transport_format, channels",
                (stable_device_id,),
            ).fetchall()
        finally:
            conn.close()
        return tuple(self._evidence_from_row(row) for row in rows)

    def replace_qualification_cache(
        self, stable_device_id: str, evidence: tuple[CapabilityEvidence, ...]
    ) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "DELETE FROM dac_qualification_cache WHERE stable_device_id = ?",
                (stable_device_id,),
            )
            for item in evidence:
                conn.execute(
                    """
                    INSERT INTO dac_qualification_cache
                        (stable_device_id, environment_fingerprint, rate_hz,
                         transport_format, channels, significant_bits,
                         supported, strength, source, observed_at_ns,
                         evidence_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item.stable_device_id,
                        item.environment_fingerprint,
                        item.tuple.rate_hz,
                        item.tuple.transport_format,
                        item.tuple.channels,
                        item.tuple.significant_bits,
                        None if item.supported is None else int(item.supported),
                        item.strength.value,
                        item.source,
                        item.observed_at_ns,
                        json.dumps({"evidence_refs": list(item.evidence_refs)}),
                    ),
                )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _evidence_from_row(row: tuple) -> CapabilityEvidence:
        (
            stable_device_id,
            environment_fingerprint,
            rate_hz,
            transport_format,
            channels,
            significant_bits,
            supported,
            strength,
            source,
            observed_at_ns,
            evidence_json,
        ) = row
        try:
            refs = tuple(json.loads(evidence_json).get("evidence_refs", []))
        except (TypeError, ValueError):
            refs = ()
        return CapabilityEvidence(
            stable_device_id=stable_device_id,
            tuple=PcmTuple(
                rate_hz=int(rate_hz),
                transport_format=transport_format,
                channels=int(channels),
                significant_bits=(
                    int(significant_bits) if significant_bits is not None else None
                ),
            ),
            supported=None if supported is None else bool(supported),
            strength=EvidenceStrength(strength),
            source=source,
            observed_at_ns=int(observed_at_ns),
            environment_fingerprint=environment_fingerprint,
            evidence_refs=refs,
        )
