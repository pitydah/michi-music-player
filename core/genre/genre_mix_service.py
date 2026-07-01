"""GenreMixService — create mixes, radio, and smart playlists by genre.

Integrates with existing smart_mixes.py and playlist systems.
Does NOT depend on Qt.
"""
from __future__ import annotations

import logging
import random
from collections import defaultdict

_log = logging.getLogger("michi.genre_mix")

MAX_MIX_SIZE = 100


class GenreMixService:
    def __init__(self, db, genre_repo, playlist_store=None):
        self._db = db
        self._repo = genre_repo
        self._playlist_store = playlist_store

    def get_tracks_for_genre(self, canonical: str) -> list:
        """Get all MediaItems for a given canonical genre."""
        return self._get_tracks_by_genre(canonical)

    def create_mix(self, canonical: str, mode: str = "all",
                   limit: int = 30, max_duration: float = 0.0) -> list:
        """Create a mix of tracks for a genre.

        Modes: all, favorites, unplayed, high_quality, discovery, recent,
               decade, artist_variety
        """
        tracks = self._get_tracks_by_genre(canonical)
        if not tracks:
            return []

        if mode == "all":
            result = list(tracks)
        elif mode == "favorites":
            result = [t for t in tracks if getattr(t, 'rating', 0) and (getattr(t, 'rating', 0) or 0) >= 4]
        elif mode == "unplayed":
            result = [t for t in tracks if not (getattr(t, 'play_count', 0) or 0)]
        elif mode == "high_quality":
            result = [t for t in tracks if self._is_high_quality(t)]
        elif mode == "discovery":
            played = [t for t in tracks if not (getattr(t, 'play_count', 0) or 0)]
            rest = [t for t in tracks if (getattr(t, 'play_count', 0) or 0) > 0]
            random.shuffle(played)
            random.shuffle(rest)
            result = played[:limit // 2] + rest[:limit // 2]
        elif mode == "recent":
            result = sorted(tracks, key=lambda t: -(getattr(t, 'last_played', 0) or 0))
        elif mode == "decade":
            result = tracks
        elif mode == "artist_variety":
            result = self._create_artist_varied_mix(tracks, limit)
        else:
            result = list(tracks)

        if mode != "artist_variety":
            random.shuffle(result)

        if limit and len(result) > limit:
            result = result[:limit]

        if max_duration > 0:
            result = self._trim_by_duration(result, max_duration)

        return result

    def create_radio_queue(self, canonical: str, initial_size: int = 20) -> list:
        """Create a dynamic radio queue for a genre (continues playing)."""
        tracks = self._get_tracks_by_genre(canonical)
        if not tracks:
            return []

        random.shuffle(tracks)
        # Prefer unplayed and favorites for radio
        unplayed = [t for t in tracks if not (getattr(t, 'play_count', 0) or 0)]
        favs = [t for t in tracks if getattr(t, 'rating', 0) and (getattr(t, 'rating', 0) or 0) >= 4]
        rest = [t for t in tracks if t not in unplayed and t not in favs]

        queue = []
        queue.extend(random.sample(favs, min(len(favs), initial_size // 3)))
        queue.extend(random.sample(unplayed, min(len(unplayed), initial_size // 3)))
        queue.extend(random.sample(rest, min(len(rest), initial_size - len(queue))))

        random.shuffle(queue)
        return queue[:initial_size]

    def create_smart_playlist(self, name: str, canonical: str,
                              rules: dict | None = None) -> int | None:
        """Create a persistent smart playlist.

        Rules:
            min_quality: str ('lossless', 'hires', 'any')
            min_year: int
            max_year: int
            decade: int
            only_favorites: bool
            only_unplayed: bool
            exclude_format: list[str]
            max_tracks: int
            max_duration: float
            include_artist: str
            exclude_artist: str
        """
        if not self._playlist_store:
            _log.warning("create_smart_playlist: no playlist_store available")
            return None
        rules = rules or {}
        tracks = self._get_tracks_by_genre(canonical)
        if not tracks:
            return None

        filtered = self._apply_rules(tracks, rules)
        filepaths = [getattr(t, 'filepath', '') for t in filtered
                     if getattr(t, 'filepath', '')]

        if not filepaths:
            return None

        pid = self._playlist_store(name)
        for fp in filepaths:
            try:
                self._db.add_to_playlist(pid, fp)
            except Exception as e:
                _log.warning("add_to_playlist failed for %s: %s", fp, e)
        return pid

    def get_related_genres(self, canonical: str, max_results: int = 5) -> list[dict]:
        """Find genres that often co-occur with the given genre."""
        track_ids = self._repo.get_tracks_for_genre(canonical)
        if not track_ids:
            return []

        cooccurrences: dict[str, int] = defaultdict(int)
        for tid in track_ids:
            genres = self._repo.get_track_genres(tid)
            for g in genres:
                gc = g.get("canonical_genre", "")
                if gc and gc != canonical:
                    cooccurrences[gc] += 1

        related = []
        for gc, count in sorted(cooccurrences.items(), key=lambda x: -x[1])[:max_results]:
            related.append({
                "genre": gc,
                "cooccurrence_count": count,
            })
        return related

    def _get_tracks_by_genre(self, canonical: str) -> list:
        track_ids = self._repo.get_tracks_for_genre(canonical)
        items = []
        for tid in track_ids:
            item = self._db.get_media_item_by_id(tid)
            if item:
                items.append(item)
        return items

    def _create_artist_varied_mix(self, tracks: list, limit: int) -> list:
        by_artist: dict[str, list] = defaultdict(list)
        for t in tracks:
            artist = getattr(t, 'artist', '') or 'Unknown'
            by_artist[artist].append(t)
        result = []
        artists = list(by_artist.keys())
        random.shuffle(artists)
        per_artist = max(1, limit // len(artists))
        for artist in artists:
            pool = by_artist[artist]
            random.shuffle(pool)
            result.extend(pool[:per_artist])
            if len(result) >= limit:
                break
        random.shuffle(result)
        return result[:limit]

    def _is_high_quality(self, t) -> bool:
        sr = getattr(t, 'sample_rate', 0) or 0
        bd = getattr(t, 'bit_depth', 0) or 0
        br = getattr(t, 'bitrate', 0) or 0
        ext = (getattr(t, 'ext', '') or '').lower()
        if ext in ('.mp3',) and br >= 320:
            return True
        return bool(sr >= 44100 and bd >= 16)

    def _trim_by_duration(self, tracks: list, max_secs: float) -> list:
        total = 0.0
        result = []
        for t in tracks:
            dur = getattr(t, 'duration', 0) or 0
            if total + dur > max_secs:
                break
            result.append(t)
            total += dur
        return result

    def _apply_rules(self, tracks: list, rules: dict) -> list:
        result = tracks
        min_q = rules.get("min_quality", "any")
        if min_q != "any":
            result = [t for t in result if self._meets_quality(t, min_q)]
        min_year = rules.get("min_year", 0)
        if min_year:
            result = [t for t in result if (getattr(t, 'year', 0) or 0) >= min_year]
        max_year = rules.get("max_year", 0)
        if max_year:
            result = [t for t in result if (getattr(t, 'year', 0) or 0) <= max_year]
        if rules.get("only_favorites"):
            result = [t for t in result if getattr(t, 'rating', 0) and (getattr(t, 'rating', 0) or 0) >= 4]
        if rules.get("only_unplayed"):
            result = [t for t in result if not (getattr(t, 'play_count', 0) or 0)]
        exclude_fmt = rules.get("exclude_format", [])
        if exclude_fmt:
            result = [t for t in result if (getattr(t, 'ext', '') or '').lower() not in exclude_fmt]
        include_artist = rules.get("include_artist", "")
        if include_artist:
            result = [t for t in result if include_artist.lower() in (getattr(t, 'artist', '') or '').lower()]
        exclude_artist = rules.get("exclude_artist", "")
        if exclude_artist:
            result = [t for t in result if exclude_artist.lower() not in (getattr(t, 'artist', '') or '').lower()]
        max_tracks = rules.get("max_tracks", 0)
        if max_tracks and len(result) > max_tracks:
            result = result[:max_tracks]
        return result

    @staticmethod
    def _meets_quality(t, min_q: str) -> bool:
        sr = getattr(t, 'sample_rate', 0) or 0
        bd = getattr(t, 'bit_depth', 0) or 0
        if min_q == "hires":
            return sr >= 88200 or bd >= 24
        if min_q == "lossless":
            ext = (getattr(t, 'ext', '') or '').lower()
            return ext not in ('.mp3', '.aac', '.wma', '.ogg', '.opus')
        return True
