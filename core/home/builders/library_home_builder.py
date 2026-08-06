"""LibraryHomeBuilder — builds LibraryHomeStatus."""

from __future__ import annotations

import logging
from typing import Any

from core.home.home_status import LibraryHomeStatus

logger = logging.getLogger("michi.home.builders.library")


def build_library_status_from_section(section: dict) -> LibraryHomeStatus:
    """Map the canonical ContextService library section (S11 authority).

    The section is produced by ``LibrarySectionProvider`` from the real
    database; this adapter never re-reads the DB directly.
    """
    if not isinstance(section, dict):
        return LibraryHomeStatus(is_empty=True, is_healthy=False)
    track_count = int(section.get("track_count", 0) or 0)
    return LibraryHomeStatus(
        track_count=track_count,
        album_count=int(section.get("album_count", 0) or 0),
        artist_count=int(section.get("artist_count", 0) or 0),
        genre_count=int(section.get("genre_count", 0) or 0),
        active_roots_count=int(section.get("active_roots_count", 0) or 0),
        last_scan=section.get("last_scan"),
        index_error_count=int(section.get("index_error_count", 0) or 0),
        missing_file_count=int(section.get("missing_file_count", 0) or 0),
        missing_metadata_count=int(section.get("missing_metadata_count", 0) or 0),
        missing_cover_count=int(section.get("missing_cover_count", 0) or 0),
        tracks_without_audio_features=int(section.get("tracks_without_audio_features", 0) or 0),
        new_tracks_count=int(section.get("new_tracks_count", 0) or 0),
        is_empty=track_count == 0,
        is_healthy=(
            int(section.get("index_error_count", 0) or 0) == 0
            and int(section.get("missing_file_count", 0) or 0) == 0
        ),
    )


def build_library_status(db: Any = None, context_svc: Any = None) -> LibraryHomeStatus:
    if context_svc is not None:
        try:
            snap = context_svc.get_home_snapshot()
            if snap and "library_health" in snap:
                lh = snap["library_health"]
                return LibraryHomeStatus(
                    track_count=lh.get("track_count", 0),
                    album_count=lh.get("album_count", 0),
                    artist_count=lh.get("artist_count", 0),
                    genre_count=lh.get("genre_count", 0),
                    active_roots_count=lh.get("active_roots_count", 0),
                    last_scan=lh.get("last_scan"),
                    index_error_count=lh.get("index_error_count", 0),
                    missing_file_count=lh.get("missing_file_count", 0),
                    missing_metadata_count=lh.get("missing_metadata_count", 0),
                    missing_cover_count=lh.get("missing_cover_count", 0),
                    tracks_without_audio_features=lh.get("tracks_without_audio_features", 0),
                    new_tracks_count=lh.get("new_tracks_count", 0),
                    is_empty=lh.get("track_count", 0) == 0,
                    is_healthy=lh.get("index_error_count", 0) == 0 and lh.get("missing_file_count", 0) == 0,
                )
        except Exception:
            logger.debug("ContextService snapshot unavailable, falling back to DB")

    if db is not None:
        try:
            if hasattr(db, "get_dashboard_stats"):
                ds = db.get_dashboard_stats()
            elif hasattr(db, "get_stats"):
                ds = db.get_stats()
            else:
                ds = {}
            tc = ds.get("total_songs", ds.get("total", 0))
            return LibraryHomeStatus(
                track_count=tc,
                album_count=ds.get("total_albums", 0),
                artist_count=ds.get("total_artists", 0),
                missing_metadata_count=ds.get("missing_metadata", 0),
                is_empty=tc == 0,
                is_healthy=True,
            )
        except Exception:
            logger.debug("DB stats unavailable")

    return LibraryHomeStatus(is_empty=True, is_healthy=True)
