"""Recommendation repository — SQLite cache and feedback storage."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import time

logger = logging.getLogger("michi.recommendation.repository")

_DB_PATH = os.path.expanduser("~/.local/share/michi/recommendations/recommendations.db")  # legacy compat

def _default_db_path() -> str:
    from core.paths import recommendation_dir
    return os.path.join(recommendation_dir(), "recommendations.db")


class RecommendationRepository:
    def __init__(self, db_path: str | None = None):
        if db_path is None:
            db_path = _default_db_path()
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._run_migrations()

    def _run_migrations(self):
        sql_path = os.path.join(
            os.path.dirname(__file__), "migrations", "001_recommendations.sql"
        )
        if os.path.exists(sql_path):
            with open(sql_path) as f:
                self._conn.executescript(f.read())
            self._conn.commit()

    def cache_recommendation(self, rec_id: str, seed_type: str, seed_value: str,
                              strategy: str, tracks: list, explanations: list,
                              cache_days: int = 7):
        self._conn.execute(
            "INSERT OR REPLACE INTO recommendation_cache "
            "(recommendation_id, seed_type, seed_value, strategy, tracks_json, "
            "explanation_json, raw_score_json) VALUES (?,?,?,?,?,?,?)",
            (rec_id, seed_type, seed_value, strategy,
             json.dumps([_trk_to_dict(t) for t in tracks], ensure_ascii=False),
             json.dumps([_expl_to_dict(e) for e in explanations], ensure_ascii=False),
             json.dumps([{"track_id": t.track_id, "score": t.score} for t in tracks], ensure_ascii=False)),
        )
        self._conn.commit()

    def get_cached(self, rec_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM recommendation_cache WHERE recommendation_id=? "
            "AND datetime(expires_at) > datetime('now')",
            (rec_id,),
        ).fetchone()
        if not row:
            return None
        return {
            "recommendation_id": row[1], "seed_type": row[2],
            "seed_value": row[3], "strategy": row[4],
            "tracks": json.loads(row[6] or "[]"),
            "explanations": json.loads(row[7] or "[]"),
        }

    def record_feedback(self, rec_id: str, track_key: str, feedback: str):
        self._conn.execute(
            "INSERT INTO recommendation_feedback (recommendation_id, track_key, feedback) VALUES (?,?,?)",
            (rec_id, track_key, feedback),
        )
        self._conn.commit()

    def get_feedback(self, rec_id: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT track_key, feedback, timestamp FROM recommendation_feedback WHERE recommendation_id=?",
            (rec_id,),
        ).fetchall()
        return [{"track_key": r[0], "feedback": r[1], "timestamp": r[2]} for r in rows]

    def save_profile(self, profile_json: str):
        self._conn.execute(
            "INSERT OR REPLACE INTO recommendation_profile "
            "(id, profile_name, enabled, updated_at, top_artists_json, top_genres_json) "
            "VALUES (1, 'default', 1, ?, ?, ?)",
            (time.strftime("%Y-%m-%dT%H:%M:%S"), "[]", "[]"),
        )
        self._conn.commit()

    def close(self):
        self._conn.close()


def _trk_to_dict(t) -> dict:
    return {
        "track_id": t.track_id, "title": t.title, "artist": t.artist,
        "album": t.album, "year": t.year, "genre": t.genre,
        "duration": t.duration, "format": t.format,
        "score": t.score, "reasons": t.reasons, "strategy": t.strategy,
    }


def _expl_to_dict(e) -> dict:
    return {
        "track_id": e.track_id, "score": e.score,
        "reason_summary": e.reason_summary, "detailed_reasons": e.detailed_reasons,
    }
