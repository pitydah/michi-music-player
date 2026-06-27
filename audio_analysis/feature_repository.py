"""Feature repository — SQLite storage for audio features, jobs, and similarity cache."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
import uuid

from audio_analysis.schemas import AudioFeature

logger = logging.getLogger("michi.audio_analysis.repository")

_DB_PATH = os.path.expanduser("~/.local/share/michi/audio_analysis/audio_features.db")  # keep for compat

def _default_db_path() -> str:
    from core.paths import audio_features_db_path
    return audio_features_db_path()


class FeatureRepository:
    def __init__(self, db_path: str | None = None):
        if db_path is None:
            db_path = _default_db_path()
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._run_migrations()

    def _run_migrations(self):
        sql_path = os.path.join(
            os.path.dirname(__file__), "migrations", "001_audio_features.sql"
        )
        if os.path.exists(sql_path):
            with open(sql_path) as f:
                self._conn.executescript(f.read())
            self._conn.commit()

    def upsert_feature(self, track_key: str, feat: AudioFeature):
        row = self._conn.execute(
            "SELECT id FROM audio_feature WHERE track_key=?", (track_key,)
        ).fetchone()
        if row:
            self._conn.execute(
                """UPDATE audio_feature SET duration=?, bpm=?, bpm_confidence=?,
                energy=?, dynamic_range=?, spectral_centroid=?, spectral_rolloff=?,
                zero_crossing_rate=?, mfcc_json=?, chroma_json=?, backend=?,
                status=?, error=?, analyzed_at=?
                WHERE track_key=?""",
                (feat.duration, feat.bpm, feat.bpm_confidence,
                 feat.energy, feat.dynamic_range,
                 feat.spectral_centroid, feat.spectral_rolloff,
                 feat.zero_crossing_rate, feat.mfcc_json, feat.chroma_json,
                 feat.backend, feat.status, feat.error,
                 time.strftime("%Y-%m-%dT%H:%M:%S"), track_key),
            )
        else:
            self._conn.execute(
                """INSERT INTO audio_feature (track_key, duration, bpm, bpm_confidence,
                energy, dynamic_range, spectral_centroid, spectral_rolloff,
                zero_crossing_rate, mfcc_json, chroma_json, backend, status, error)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (track_key, feat.duration, feat.bpm, feat.bpm_confidence,
                 feat.energy, feat.dynamic_range,
                 feat.spectral_centroid, feat.spectral_rolloff,
                 feat.zero_crossing_rate, feat.mfcc_json, feat.chroma_json,
                 feat.backend, feat.status, feat.error),
            )
        self._conn.commit()

    def get_feature(self, track_key: str) -> AudioFeature | None:
        row = self._conn.execute(
            "SELECT * FROM audio_feature WHERE track_key=?", (track_key,)
        ).fetchone()
        if row:
            return _row_to_feature(row)
        return None

    def get_all_features(self) -> list[AudioFeature]:
        rows = self._conn.execute(
            "SELECT * FROM audio_feature WHERE status='completed'"
        ).fetchall()
        return [_row_to_feature(r) for r in rows]

    def has_features(self, track_key: str) -> bool:
        row = self._conn.execute(
            "SELECT id FROM audio_feature WHERE track_key=? AND status='completed'",
            (track_key,),
        ).fetchone()
        return row is not None

    def count_features(self) -> int:
        return self._conn.execute(
            "SELECT COUNT(*) FROM audio_feature WHERE status='completed'"
        ).fetchone()[0]

    def count_missing(self, all_track_keys: list[str]) -> int:
        if not all_track_keys:
            return 0
        placeholders = ",".join("?" * len(all_track_keys))
        existing = self._conn.execute(
            f"SELECT track_key FROM audio_feature WHERE track_key IN ({placeholders}) AND status='completed'",
            all_track_keys,
        ).fetchall()
        existing_keys = {r[0] for r in existing}
        return sum(1 for k in all_track_keys if k not in existing_keys)

    def add_job(self, track_key: str, priority: int = 5) -> str:
        job_id = str(uuid.uuid4())[:12]
        self._conn.execute(
            "INSERT OR IGNORE INTO audio_analysis_job (job_id, track_key, status, priority) VALUES (?,?,?,?)",
            (job_id, track_key, "pending", priority),
        )
        self._conn.commit()
        return job_id

    def update_job(self, job_id: str, status: str, error: str = ""):
        if status == "running":
            self._conn.execute(
                "UPDATE audio_analysis_job SET status=?, started_at=? WHERE job_id=?",
                (status, time.strftime("%Y-%m-%dT%H:%M:%S"), job_id),
            )
        else:
            self._conn.execute(
                "UPDATE audio_analysis_job SET status=?, finished_at=?, error=? WHERE job_id=?",
                (status, time.strftime("%Y-%m-%dT%H:%M:%S"), error, job_id),
            )
        self._conn.commit()

    def get_pending_jobs(self, limit: int = 50) -> list[dict]:
        rows = self._conn.execute(
            "SELECT job_id, track_key FROM audio_analysis_job WHERE status='pending' ORDER BY priority ASC, created_at ASC LIMIT ?",
            (limit,),
        ).fetchall()
        return [{"job_id": r[0], "track_key": r[1]} for r in rows]

    def count_active_jobs(self) -> int:
        return self._conn.execute(
            "SELECT COUNT(*) FROM audio_analysis_job WHERE status='running'"
        ).fetchone()[0]

    def cache_similarity(self, seed_key: str, strategy: str, results: list):
        self._conn.execute(
            "DELETE FROM audio_similarity_cache WHERE seed_track_key=? AND strategy=?",
            (seed_key, strategy),
        )
        self._conn.execute(
            "INSERT INTO audio_similarity_cache (seed_track_key, strategy, result_json) VALUES (?,?,?)",
            (seed_key, strategy, json.dumps(results, ensure_ascii=False)),
        )
        self._conn.commit()

    def get_similarity_cache(self, seed_key: str, strategy: str) -> list | None:
        row = self._conn.execute(
            "SELECT result_json FROM audio_similarity_cache WHERE seed_track_key=? AND strategy=? "
            "AND datetime(expires_at) > datetime('now')",
            (seed_key, strategy),
        ).fetchone()
        if row:
            return json.loads(row[0])
        return None

    def close(self):
        self._conn.close()


def _row_to_feature(row: tuple) -> AudioFeature:
    return AudioFeature(
        track_key=str(row[1] or ""),
        duration=float(row[2] or 0),
        bpm=float(row[3] or 0),
        bpm_confidence=float(row[4] or 0),
        energy=float(row[5] or 0),
        dynamic_range=float(row[6] or 0),
        spectral_centroid=float(row[7] or 0),
        spectral_rolloff=float(row[8] or 0),
        zero_crossing_rate=float(row[9] or 0),
        mfcc_json=str(row[10] or "[]"),
        chroma_json=str(row[11] or "[]"),
        backend=str(row[12] or ""),
        status=str(row[14] or "pending"),
        error=str(row[15] or ""),
    )
