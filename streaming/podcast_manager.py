"""PodcastManager — operations for podcasts, feed management and episode tracking."""

from __future__ import annotations

import datetime
import logging
from typing import Any

from streaming.podcast_feed_parser import parse_feed
from streaming.podcast_models import (
    BroadcastHistoryItem,
    PodcastEpisode,
    PodcastShow,
)
from streaming.podcast_repository import PodcastRepository

logger = logging.getLogger("michi.podcast.manager")


class PodcastManager:
    def __init__(self, repo: PodcastRepository | None = None):
        self._repo = repo or PodcastRepository()

    @property
    def repository(self) -> PodcastRepository:
        return self._repo

    def add_feed(self, feed_url: str, import_limit: int = 50) -> dict[str, Any]:
        existing = self._repo.find_show_by_feed_url(feed_url)
        if existing is not None:
            return {"ok": False, "error": "Feed ya suscrito", "show": existing}

        parsed = parse_feed(feed_url)
        if not parsed.ok:
            return {"ok": False, "error": parsed.errors[0] if parsed.errors else "Error desconocido",
                    "warnings": parsed.warnings, "errors": parsed.errors}

        show = parsed.show
        if show is None:
            return {"ok": False, "error": "No se pudo extraer informacion del feed"}

        now = datetime.datetime.now().isoformat()
        show.created_at = now
        show.updated_at = now
        show.episode_count = len(parsed.episodes)
        show.unread_count = len(parsed.episodes)
        show_id = self._repo.add_show(show)

        imported = 0
        for ep in parsed.episodes[:import_limit]:
            ep.podcast_id = show_id
            ep.created_at = now
            ep.updated_at = now
            self._repo.upsert_episode(ep)
            imported += 1

        if show_id:
            self._repo.update_show_counts(show_id)

        show.id = show_id
        return {"ok": True, "show": show, "imported": imported, "total": len(parsed.episodes)}

    def refresh_feed(self, show_id: int, import_limit: int = 50) -> dict[str, Any]:
        show = self._repo.get_show(show_id)
        if show is None:
            return {"ok": False, "error": "Podcast no encontrado"}

        parsed = parse_feed(show.feed_url)
        if not parsed.ok:
            return {"ok": False, "error": parsed.errors[0] if parsed.errors else "Error",
                    "warnings": parsed.warnings}

        now = datetime.datetime.now().isoformat()
        new_count = 0
        existing_guids = {ep.guid for ep in self._repo.get_episodes_for_show(show_id)}

        for ep in parsed.episodes[:import_limit]:
            if ep.guid not in existing_guids:
                ep.podcast_id = show_id
                ep.created_at = now
                ep.updated_at = now
                self._repo.upsert_episode(ep)
                new_count += 1

        self._repo.update_show_counts(show_id)
        show_obj = self._repo.get_show(show_id)
        total = show_obj.episode_count if show_obj else 0

        return {"ok": True, "new_episodes": new_count, "total": total}

    def refresh_all(self) -> dict[str, Any]:
        shows = self._repo.get_shows()
        results = {"refreshed": 0, "new_episodes": 0, "errors": []}
        for show in shows:
            try:
                r = self.refresh_feed(show.id)
                if r.get("ok"):
                    results["refreshed"] += 1
                    results["new_episodes"] += r.get("new_episodes", 0)
                else:
                    results["errors"].append(f"{show.title}: {r.get('error')}")
            except Exception as e:
                results["errors"].append(f"{show.title}: {e}")
        return results

    def remove_show(self, show_id: int):
        self._repo.remove_show(show_id)

    def get_shows(self) -> list[PodcastShow]:
        return self._repo.get_shows()

    def get_show(self, show_id: int) -> PodcastShow | None:
        return self._repo.get_show(show_id)

    def get_episodes_for_show(self, show_id: int) -> list[PodcastEpisode]:
        return self._repo.get_episodes_for_show(show_id)

    def get_recent_episodes(self, limit: int = 50) -> list[PodcastEpisode]:
        return self._repo.get_recent_episodes(limit)

    def get_unplayed_episodes(self, limit: int = 50) -> list[PodcastEpisode]:
        return self._repo.get_unplayed_episodes(limit)

    def get_in_progress_episodes(self, limit: int = 50) -> list[PodcastEpisode]:
        return self._repo.get_in_progress_episodes(limit)

    def get_downloaded_episodes(self) -> list[PodcastEpisode]:
        return self._repo.get_downloaded_episodes()

    def get_favorite_episodes(self, limit: int = 100) -> list[PodcastEpisode]:
        return self._repo.get_favorite_episodes(limit)

    def get_listened_episodes(self, limit: int = 100) -> list[PodcastEpisode]:
        return self._repo.get_listened_episodes(limit)

    def get_episodes_by_status(self, played=None, downloaded=None,
                                favorite=None, limit=100) -> list[PodcastEpisode]:
        return self._repo.get_episodes_by_status(played, downloaded, favorite, limit)

    def set_episode_position(self, episode_id: int, position_sec: int):
        self._repo.set_episode_position(episode_id, position_sec)

    def mark_episode_played(self, episode_id: int, completed: bool = False):
        self._repo.mark_episode_played(episode_id, completed)
        ep = self._repo.get_episode_by_id(episode_id)
        if ep:
            self._repo.update_show_counts(ep.podcast_id)

    def mark_episode_unplayed(self, episode_id: int):
        self._repo.mark_episode_unplayed(episode_id)
        ep = self._repo.get_episode_by_id(episode_id)
        if ep:
            self._repo.update_show_counts(ep.podcast_id)

    def toggle_episode_favorite(self, episode_id: int) -> bool:
        return self._repo.toggle_episode_favorite(episode_id)

    def mark_episode_downloaded(self, episode_id: int, local_path: str, file_size: int):
        self._repo.set_episode_downloaded(episode_id, local_path, file_size)

    def mark_episode_download_removed(self, episode_id: int):
        self._repo.mark_episode_download_removed(episode_id)
        self._repo.remove_download_record(episode_id)

    def get_downloaded_count(self) -> int:
        return self._repo.get_downloaded_count()

    def get_total_download_size(self) -> int:
        return self._repo.get_total_download_size()

    def get_latest_unplayed_for_show(self, show_id: int) -> PodcastEpisode | None:
        eps = sorted(
            [e for e in self._repo.get_episodes_for_show(show_id) if not e.played],
            key=lambda e: e.published_at or "", reverse=True,
        )
        return eps[0] if eps else None

    def get_counts(self) -> dict[str, int]:
        return self._repo.get_counts()

    def add_history(self, item: BroadcastHistoryItem):
        self._repo.add_history(item)

    def get_history(self, limit: int = 100) -> list[BroadcastHistoryItem]:
        return self._repo.get_history(limit)

    def get_history_by_type(self, entry_type: str, limit: int = 50) -> list[BroadcastHistoryItem]:
        return self._repo.get_history_by_type(entry_type, limit)

    def clear_history(self):
        self._repo.clear_history()

    def delete_history_item(self, history_id: int):
        self._repo.delete_history_item(history_id)

    def record_radio_history(self, title: str, subtitle: str = "", url: str = "",
                              duration_sec: int = 0):
        item = BroadcastHistoryItem(
            entry_type="radio", ref_id=url, title=title, subtitle=subtitle,
            duration_seconds=duration_sec,
            started_at=datetime.datetime.now().isoformat(),
        )
        self._repo.add_history(item)

    def record_podcast_history(self, episode_id: int, title: str, show_title: str = "",
                                url: str = "", duration_sec: int = 0,
                                position_sec: int = 0):
        item = BroadcastHistoryItem(
            entry_type="podcast", ref_id=str(episode_id), title=title,
            subtitle=show_title, url=url,
            duration_seconds=duration_sec, position_seconds=position_sec,
            started_at=datetime.datetime.now().isoformat(),
        )
        self._repo.add_history(item)
