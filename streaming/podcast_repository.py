"""PodcastRepository — SQLite storage for podcasts, episodes, downloads and history."""

from __future__ import annotations

import json
import os
import sqlite3

from streaming.podcast_models import (
    BroadcastHistoryItem,
    PodcastDownload,
    PodcastEpisode,
    PodcastShow,
)

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS podcast_shows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feed_url TEXT UNIQUE NOT NULL,
    title TEXT DEFAULT '',
    website TEXT DEFAULT '',
    author TEXT DEFAULT '',
    description TEXT DEFAULT '',
    image_url TEXT DEFAULT '',
    image_path TEXT DEFAULT '',
    language TEXT DEFAULT '',
    categories TEXT DEFAULT '[]',
    last_updated TEXT DEFAULT '',
    episode_count INTEGER DEFAULT 0,
    unread_count INTEGER DEFAULT 0,
    favorite INTEGER DEFAULT 0,
    created_at TEXT DEFAULT '',
    updated_at TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS podcast_episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    podcast_id INTEGER NOT NULL,
    guid TEXT UNIQUE NOT NULL,
    title TEXT DEFAULT '',
    description TEXT DEFAULT '',
    audio_url TEXT DEFAULT '',
    episode_url TEXT DEFAULT '',
    image_url TEXT DEFAULT '',
    image_path TEXT DEFAULT '',
    published_at TEXT DEFAULT '',
    duration_seconds INTEGER DEFAULT 0,
    position_seconds INTEGER DEFAULT 0,
    played INTEGER DEFAULT 0,
    completed INTEGER DEFAULT 0,
    favorite INTEGER DEFAULT 0,
    downloaded INTEGER DEFAULT 0,
    local_path TEXT DEFAULT '',
    file_size INTEGER DEFAULT 0,
    mime_type TEXT DEFAULT '',
    created_at TEXT DEFAULT '',
    updated_at TEXT DEFAULT '',
    FOREIGN KEY (podcast_id) REFERENCES podcast_shows(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS podcast_downloads (
    episode_id INTEGER PRIMARY KEY,
    status TEXT DEFAULT '',
    progress REAL DEFAULT 0.0,
    local_path TEXT DEFAULT '',
    file_size INTEGER DEFAULT 0,
    error TEXT DEFAULT '',
    started_at TEXT DEFAULT '',
    completed_at TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS broadcast_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_type TEXT NOT NULL,
    ref_id TEXT DEFAULT '',
    title TEXT DEFAULT '',
    subtitle TEXT DEFAULT '',
    started_at TEXT DEFAULT '',
    ended_at TEXT DEFAULT '',
    duration_seconds INTEGER DEFAULT 0,
    position_seconds INTEGER DEFAULT 0,
    completed INTEGER DEFAULT 0,
    extra TEXT DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_episodes_podcast_id ON podcast_episodes(podcast_id);
CREATE INDEX IF NOT EXISTS idx_episodes_guid ON podcast_episodes(guid);
CREATE INDEX IF NOT EXISTS idx_episodes_published ON podcast_episodes(published_at);
CREATE INDEX IF NOT EXISTS idx_episodes_played ON podcast_episodes(played);
CREATE INDEX IF NOT EXISTS idx_episodes_downloaded ON podcast_episodes(downloaded);
CREATE INDEX IF NOT EXISTS idx_history_type ON broadcast_history(entry_type);
CREATE INDEX IF NOT EXISTS idx_history_started ON broadcast_history(started_at);
"""


class PodcastRepository:
    def __init__(self, db_path: str | None = None):
        if db_path is None:
            from core.paths import app_data_dir
            db_path = os.path.join(app_data_dir(), "podcasts.db")
        self._path = db_path
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(_SCHEMA_SQL)
        self._conn.commit()

    def close(self):
        self._conn.close()

    # ── Shows ──

    def add_show(self, show: PodcastShow) -> int:
        cur = self._conn.execute(
            "INSERT OR IGNORE INTO podcast_shows "
            "(feed_url, title, website, author, description, image_url, image_path, "
            "language, categories, last_updated, episode_count, unread_count, favorite, "
            "created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (show.feed_url, show.title, show.website, show.author, show.description,
             show.image_url, show.image_path, show.language,
             json.dumps(show.categories), show.last_updated,
             show.episode_count, show.unread_count, int(show.favorite),
             show.created_at, show.updated_at),
        )
        self._conn.commit()
        if cur.lastrowid and cur.lastrowid > 0:
            return cur.lastrowid
        # Already existed — get existing id
        row = self._conn.execute(
            "SELECT id FROM podcast_shows WHERE feed_url=?", (show.feed_url,)
        ).fetchone()
        return row["id"] if row else 0

    def update_show(self, show: PodcastShow):
        self._conn.execute(
            "UPDATE podcast_shows SET title=?, website=?, author=?, description=?, "
            "image_url=?, image_path=?, language=?, categories=?, last_updated=?, "
            "episode_count=?, unread_count=?, favorite=?, updated_at=? WHERE id=?",
            (show.title, show.website, show.author, show.description,
             show.image_url, show.image_path, show.language,
             json.dumps(show.categories), show.last_updated,
             show.episode_count, show.unread_count, int(show.favorite),
             show.updated_at, show.id),
        )
        self._conn.commit()

    def remove_show(self, show_id: int):
        self._conn.execute("DELETE FROM podcast_episodes WHERE podcast_id=?", (show_id,))
        self._conn.execute("DELETE FROM podcast_shows WHERE id=?", (show_id,))
        self._conn.commit()

    def get_shows(self) -> list[PodcastShow]:
        rows = self._conn.execute(
            "SELECT * FROM podcast_shows ORDER BY title"
        ).fetchall()
        return [_row_to_show(r) for r in rows]

    def get_show(self, show_id: int) -> PodcastShow | None:
        row = self._conn.execute(
            "SELECT * FROM podcast_shows WHERE id=?", (show_id,)
        ).fetchone()
        return _row_to_show(row) if row else None

    def find_show_by_feed_url(self, feed_url: str) -> PodcastShow | None:
        row = self._conn.execute(
            "SELECT * FROM podcast_shows WHERE feed_url=?", (feed_url,)
        ).fetchone()
        return _row_to_show(row) if row else None

    # ── Episodes ──

    def upsert_episode(self, ep: PodcastEpisode) -> int:
        self._conn.execute(
            "INSERT INTO podcast_episodes "
            "(podcast_id, guid, title, description, audio_url, episode_url, image_url, "
            "image_path, published_at, duration_seconds, position_seconds, played, "
            "completed, favorite, downloaded, local_path, file_size, mime_type, "
            "created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(guid) DO UPDATE SET "
            "title=excluded.title, description=excluded.description, "
            "audio_url=excluded.audio_url, episode_url=excluded.episode_url, "
            "image_url=excluded.image_url, published_at=excluded.published_at, "
            "duration_seconds=excluded.duration_seconds, "
            "file_size=excluded.file_size, mime_type=excluded.mime_type, "
            "updated_at=excluded.updated_at",
            (ep.podcast_id, ep.guid, ep.title, ep.description, ep.audio_url,
             ep.episode_url, ep.image_url, ep.image_path, ep.published_at,
             ep.duration_seconds, ep.position_seconds, int(ep.played),
             int(ep.completed), int(ep.favorite), int(ep.downloaded),
             ep.local_path, ep.file_size, ep.mime_type,
             ep.created_at, ep.updated_at),
        )
        self._conn.commit()
        row = self._conn.execute(
            "SELECT id FROM podcast_episodes WHERE guid=?", (ep.guid,)
        ).fetchone()
        return row[0] if row else 0

    def get_episodes_for_show(self, podcast_id: int) -> list[PodcastEpisode]:
        rows = self._conn.execute(
            "SELECT * FROM podcast_episodes WHERE podcast_id=? "
            "ORDER BY published_at DESC", (podcast_id,)
        ).fetchall()
        return [_row_to_episode(r) for r in rows]

    def get_recent_episodes(self, limit: int = 50) -> list[PodcastEpisode]:
        rows = self._conn.execute(
            "SELECT * FROM podcast_episodes ORDER BY published_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [_row_to_episode(r) for r in rows]

    def get_unplayed_episodes(self, limit: int = 50) -> list[PodcastEpisode]:
        rows = self._conn.execute(
            "SELECT * FROM podcast_episodes WHERE played=0 "
            "ORDER BY published_at DESC LIMIT ?", (limit,),
        ).fetchall()
        return [_row_to_episode(r) for r in rows]

    def get_in_progress_episodes(self, limit: int = 50) -> list[PodcastEpisode]:
        rows = self._conn.execute(
            "SELECT * FROM podcast_episodes WHERE played=0 AND position_seconds>0 "
            "ORDER BY updated_at DESC LIMIT ?", (limit,),
        ).fetchall()
        return [_row_to_episode(r) for r in rows]

    def get_downloaded_episodes(self) -> list[PodcastEpisode]:
        rows = self._conn.execute(
            "SELECT * FROM podcast_episodes WHERE downloaded=1 "
            "ORDER BY published_at DESC"
        ).fetchall()
        return [_row_to_episode(r) for r in rows]

    def set_episode_position(self, episode_id: int, position_sec: int):
        self._conn.execute(
            "UPDATE podcast_episodes SET position_seconds=?, updated_at=? WHERE id=?",
            (position_sec, _now(), episode_id),
        )
        self._conn.commit()

    def mark_episode_played(self, episode_id: int, completed: bool = False):
        self._conn.execute(
            "UPDATE podcast_episodes SET played=1, completed=?, updated_at=? WHERE id=?",
            (int(completed), _now(), episode_id),
        )
        self._conn.commit()

    def mark_episode_unplayed(self, episode_id: int):
        self._conn.execute(
            "UPDATE podcast_episodes SET played=0, completed=0, position_seconds=0, "
            "updated_at=? WHERE id=?",
            (_now(), episode_id),
        )
        self._conn.commit()

    def toggle_episode_favorite(self, episode_id: int) -> bool:
        row = self._conn.execute(
            "SELECT favorite FROM podcast_episodes WHERE id=?", (episode_id,)
        ).fetchone()
        if row is None:
            return False
        new_val = 0 if row[0] else 1
        self._conn.execute(
            "UPDATE podcast_episodes SET favorite=?, updated_at=? WHERE id=?",
            (new_val, _now(), episode_id),
        )
        self._conn.commit()
        return bool(new_val)

    def set_episode_downloaded(self, episode_id: int, local_path: str, file_size: int):
        self._conn.execute(
            "UPDATE podcast_episodes SET downloaded=1, local_path=?, file_size=?, "
            "updated_at=? WHERE id=?",
            (local_path, file_size, _now(), episode_id),
        )
        self._conn.commit()

    # ── Downloads ──

    def add_download(self, dl: PodcastDownload):
        self._conn.execute(
            "INSERT OR REPLACE INTO podcast_downloads "
            "(episode_id, status, progress, local_path, file_size, error, "
            "started_at, completed_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (dl.episode_id, dl.status, dl.progress, dl.local_path, dl.file_size,
             dl.error, dl.started_at, dl.completed_at),
        )
        self._conn.commit()

    def get_download(self, episode_id: int) -> PodcastDownload | None:
        row = self._conn.execute(
            "SELECT * FROM podcast_downloads WHERE episode_id=?", (episode_id,)
        ).fetchone()
        return _row_to_download(row) if row else None

    # ── History ──

    def add_history(self, item: BroadcastHistoryItem):
        self._conn.execute(
            "INSERT INTO broadcast_history "
            "(entry_type, ref_id, title, subtitle, started_at, ended_at, "
            "duration_seconds, position_seconds, completed, extra) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (item.entry_type, item.ref_id, item.title, item.subtitle,
             item.started_at, item.ended_at, item.duration_seconds,
             item.position_seconds, int(item.completed),
             json.dumps(item.extra)),
        )
        self._conn.commit()

    def get_history(self, limit: int = 100) -> list[BroadcastHistoryItem]:
        rows = self._conn.execute(
            "SELECT * FROM broadcast_history ORDER BY started_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [_row_to_history(r) for r in rows]

    def get_history_by_type(self, entry_type: str, limit: int = 50) -> list[BroadcastHistoryItem]:
        rows = self._conn.execute(
            "SELECT * FROM broadcast_history WHERE entry_type=? "
            "ORDER BY started_at DESC LIMIT ?", (entry_type, limit),
        ).fetchall()
        return [_row_to_history(r) for r in rows]

    def clear_history(self):
        self._conn.execute("DELETE FROM broadcast_history")
        self._conn.commit()

    def delete_history_item(self, history_id: int):
        self._conn.execute("DELETE FROM broadcast_history WHERE id=?", (history_id,))
        self._conn.commit()

    def clear_history_by_type(self, entry_type: str):
        self._conn.execute("DELETE FROM broadcast_history WHERE entry_type=?", (entry_type,))
        self._conn.commit()

    def get_episode_by_id(self, episode_id: int) -> PodcastEpisode | None:
        row = self._conn.execute(
            "SELECT * FROM podcast_episodes WHERE id=?", (episode_id,)
        ).fetchone()
        return _row_to_episode(row) if row else None

    def get_episode_by_guid(self, guid: str) -> PodcastEpisode | None:
        row = self._conn.execute(
            "SELECT * FROM podcast_episodes WHERE guid=?", (guid,)
        ).fetchone()
        return _row_to_episode(row) if row else None

    def get_favorite_episodes(self, limit: int = 100) -> list[PodcastEpisode]:
        rows = self._conn.execute(
            "SELECT * FROM podcast_episodes WHERE favorite=1 "
            "ORDER BY published_at DESC LIMIT ?", (limit,),
        ).fetchall()
        return [_row_to_episode(r) for r in rows]

    def get_episodes_by_status(self, played: int | None = None,
                                downloaded: int | None = None,
                                favorite: int | None = None,
                                limit: int = 100) -> list[PodcastEpisode]:
        clauses = []
        params: list = []
        if played is not None:
            clauses.append("played=?")
            params.append(played)
        if downloaded is not None:
            clauses.append("downloaded=?")
            params.append(downloaded)
        if favorite is not None:
            clauses.append("favorite=?")
            params.append(favorite)
        where = " AND ".join(clauses) if clauses else "1=1"
        rows = self._conn.execute(
            f"SELECT * FROM podcast_episodes WHERE {where} "
            "ORDER BY published_at DESC LIMIT ?",
            (*params, limit),
        ).fetchall()
        return [_row_to_episode(r) for r in rows]

    def get_listened_episodes(self, limit: int = 100) -> list[PodcastEpisode]:
        rows = self._conn.execute(
            "SELECT * FROM podcast_episodes WHERE played=1 "
            "ORDER BY updated_at DESC LIMIT ?", (limit,),
        ).fetchall()
        return [_row_to_episode(r) for r in rows]

    def update_show_counts(self, show_id: int):
        total = self._conn.execute(
            "SELECT COUNT(*) FROM podcast_episodes WHERE podcast_id=?", (show_id,)
        ).fetchone()[0]
        unread = self._conn.execute(
            "SELECT COUNT(*) FROM podcast_episodes WHERE podcast_id=? AND played=0",
            (show_id,),
        ).fetchone()[0]
        self._conn.execute(
            "UPDATE podcast_shows SET episode_count=?, unread_count=?, updated_at=? WHERE id=?",
            (total, unread, _now(), show_id),
        )
        self._conn.commit()

    def mark_episode_download_removed(self, episode_id: int):
        self._conn.execute(
            "UPDATE podcast_episodes SET downloaded=0, local_path='', "
            "updated_at=? WHERE id=?",
            (_now(), episode_id),
        )
        self._conn.commit()

    def remove_download_record(self, episode_id: int):
        self._conn.execute(
            "DELETE FROM podcast_downloads WHERE episode_id=?", (episode_id,)
        )
        self._conn.commit()

    def get_total_download_size(self) -> int:
        row = self._conn.execute(
            "SELECT COALESCE(SUM(file_size), 0) FROM podcast_episodes WHERE downloaded=1"
        ).fetchone()
        return row[0] if row else 0

    def get_downloaded_count(self) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) FROM podcast_episodes WHERE downloaded=1"
        ).fetchone()
        return row[0] if row else 0

    def get_counts(self) -> dict[str, int]:
        shows = self._conn.execute("SELECT COUNT(*) FROM podcast_shows").fetchone()[0]
        episodes = self._conn.execute("SELECT COUNT(*) FROM podcast_episodes").fetchone()[0]
        unplayed = self._conn.execute(
            "SELECT COUNT(*) FROM podcast_episodes WHERE played=0"
        ).fetchone()[0]
        downloaded = self._conn.execute(
            "SELECT COUNT(*) FROM podcast_episodes WHERE downloaded=1"
        ).fetchone()[0]
        return {
            "shows": shows,
            "episodes": episodes,
            "unplayed": unplayed,
            "downloaded": downloaded,
        }


def _now() -> str:
    import datetime
    return datetime.datetime.now().isoformat()


def _row_to_show(r: sqlite3.Row) -> PodcastShow:
    return PodcastShow(
        id=r["id"], feed_url=r["feed_url"], title=r["title"],
        website=r["website"], author=r["author"], description=r["description"],
        image_url=r["image_url"], image_path=r["image_path"],
        language=r["language"],
        categories=json.loads(r["categories"] or "[]"),
        last_updated=r["last_updated"], episode_count=r["episode_count"],
        unread_count=r["unread_count"], favorite=bool(r["favorite"]),
        created_at=r["created_at"], updated_at=r["updated_at"],
    )


def _row_to_episode(r: sqlite3.Row) -> PodcastEpisode:
    return PodcastEpisode(
        id=r["id"], podcast_id=r["podcast_id"], guid=r["guid"],
        title=r["title"], description=r["description"],
        audio_url=r["audio_url"], episode_url=r["episode_url"],
        image_url=r["image_url"], image_path=r["image_path"],
        published_at=r["published_at"],
        duration_seconds=r["duration_seconds"],
        position_seconds=r["position_seconds"],
        played=bool(r["played"]), completed=bool(r["completed"]),
        favorite=bool(r["favorite"]), downloaded=bool(r["downloaded"]),
        local_path=r["local_path"], file_size=r["file_size"],
        mime_type=r["mime_type"],
        created_at=r["created_at"], updated_at=r["updated_at"],
    )


def _row_to_download(r: sqlite3.Row) -> PodcastDownload:
    return PodcastDownload(
        episode_id=r["episode_id"], status=r["status"],
        progress=r["progress"], local_path=r["local_path"],
        file_size=r["file_size"], error=r["error"],
        started_at=r["started_at"], completed_at=r["completed_at"],
    )


def _row_to_history(r: sqlite3.Row) -> BroadcastHistoryItem:
    return BroadcastHistoryItem(
        id=r["id"], entry_type=r["entry_type"], ref_id=r["ref_id"],
        title=r["title"], subtitle=r["subtitle"],
        started_at=r["started_at"], ended_at=r["ended_at"],
        duration_seconds=r["duration_seconds"],
        position_seconds=r["position_seconds"],
        completed=bool(r["completed"]),
        extra=json.loads(r["extra"] or "{}"),
    )
