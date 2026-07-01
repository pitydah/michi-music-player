"""GenreCleanupService — detect problems, generate suggestions, execute cleanup.

All operations are safe (DB-only by default). File tagging is opt-in.
"""
from __future__ import annotations

import logging
from collections import defaultdict

from metadata.genre_normalizer import (
    canonicalize_genre,
    get_junk_genres,
    is_junk_genre,
    split_genres,
    detect_duplicate_genres,
)

_log = logging.getLogger("michi.genre_cleanup")

_MULTI_DELIMS = (",", ";", "/", "|", "&")


class GenreCleanupService:
    def __init__(self, db, genre_repo):
        self._db = db
        self._repo = genre_repo

    # ── Detection methods ──

    def detect_duplicates(self) -> list[dict]:
        """Detect probable duplicate genres."""
        all_items = self._db.get_all() or []
        return detect_duplicate_genres(all_items)

    def detect_rare_genres(self, min_tracks: int = 3) -> list[dict]:
        """Detect genres with few tracks (potential cleanup candidates)."""
        stats = self._repo.get_cached_stats()
        rare = []
        for genre, s in stats.items():
            if s.get("track_count", 0) < min_tracks and genre not in ("", None):
                rare.append({
                    "genre": genre,
                    "track_count": s.get("track_count", 0),
                    "album_count": s.get("album_count", 0),
                    "artist_count": s.get("artist_count", 0),
                    "duration_total": s.get("duration_total", 0.0),
                })
        return sorted(rare, key=lambda r: r["track_count"])

    def detect_junk(self) -> list[dict]:
        """Find tracks with junk/unrecognized genre values."""
        junk_set = get_junk_genres()
        warnings = []
        all_items = self._db.get_all() or []
        counts: dict[str, int] = defaultdict(int)
        examples: dict[str, list] = defaultdict(list)
        for item in all_items:
            raw = (getattr(item, 'genre', '') or '').strip().lower()
            if not raw:
                continue
            if raw in junk_set or is_junk_genre(raw):
                counts[raw] += 1
                if len(examples[raw]) < 3:
                    title = getattr(item, 'title', '') or getattr(item, 'filename', '') or ''
                    artist = getattr(item, 'artist', '') or ''
                    label = f"{title} - {artist}".strip(" -") or f"track #{getattr(item, 'id', 0)}"
                    examples[raw].append(label)
        for val, cnt in sorted(counts.items(), key=lambda x: -x[1]):
            warnings.append({
                "value": val,
                "count": cnt,
                "examples": examples[val],
            })
        return warnings

    def detect_untagged(self) -> dict:
        tracks = self._get_untagged_items()
        return {
            "count": len(tracks),
            "tracks": tracks[:50],
            "total": len(tracks),
        }

    def detect_multi_genre_issues(self) -> list[dict]:
        """Detect tracks where genre has multiple values that should be split."""
        issues = []
        all_items = self._db.get_all() or []
        for item in all_items:
            raw = (getattr(item, 'genre', '') or '').strip()
            if not raw:
                continue
            if any(d in raw for d in _MULTI_DELIMS):
                genres = split_genres(raw)
                if len(genres) > 1:
                    issues.append({
                        "track_id": getattr(item, 'id', 0),
                        "title": getattr(item, 'title', '') or getattr(item, 'filename', ''),
                        "artist": getattr(item, 'artist', '') or '',
                        "raw_genre": raw,
                        "suggested_genres": genres,
                    })
        return issues

    def detect_inconsistent_albums(self) -> list[dict]:
        """Find albums where tracks have inconsistent genres."""
        all_items = self._db.get_all() or []
        album_genres: dict[str, set] = defaultdict(set)
        album_tracks: dict[str, list] = defaultdict(list)
        for item in all_items:
            album = (getattr(item, 'album', '') or '').strip()
            genre = (getattr(item, 'genre', '') or '').strip()
            if album and genre:
                album_genres[album].add(genre)
                album_tracks[album].append(item)
        issues = []
        for album, genres in album_genres.items():
            if len(genres) > 1:
                canonicals = set()
                for g in genres:
                    for sg in split_genres(g):
                        canonicals.add(canonicalize_genre(sg))
                if len(canonicals) > 1:
                    issues.append({
                        "album": album,
                        "genres": sorted(genres),
                        "canonicals": sorted(canonicals),
                        "track_count": len(album_tracks[album]),
                    })
        return sorted(issues, key=lambda x: -x["track_count"])

    def detect_inconsistent_artists(self) -> list[dict]:
        """Find artists with too many genre variants."""
        all_items = self._db.get_all() or []
        artist_genres: dict[str, set] = defaultdict(set)
        for item in all_items:
            artist = (getattr(item, 'artist', '') or '').strip()
            genre = (getattr(item, 'genre', '') or '').strip()
            if artist and genre:
                for sg in split_genres(genre):
                    artist_genres[artist].add(canonicalize_genre(sg))
        issues = []
        for artist, genres in artist_genres.items():
            if len(genres) > 4:
                issues.append({
                    "artist": artist,
                    "genre_count": len(genres),
                    "genres": sorted(genres),
                })
        return sorted(issues, key=lambda x: -x["genre_count"])

    # ── Suggestion generation ──

    def generate_all_suggestions(self) -> int:
        count = 0
        for dup in self.detect_duplicates():
            sug_id = self._repo.add_suggestion(
                "duplicate",
                ",".join(dup["raw_values"]),
                target_genre=dup["canonical"],
                affected_count=dup["count"],
                confidence=0.9,
                reason=f"Posibles duplicados: {', '.join(dup['raw_values'][:5])}",
            )
            if sug_id:
                count += 1
        for junk in self.detect_junk():
            sug_id = self._repo.add_suggestion(
                "junk",
                junk["value"],
                affected_count=junk["count"],
                confidence=0.8,
                reason=f"Valor no reconocido como género válido: {junk['value']}",
            )
            if sug_id:
                count += 1
        for rare in self.detect_rare_genres():
            sug_id = self._repo.add_suggestion(
                "rare",
                rare["genre"],
                affected_count=rare["track_count"],
                confidence=0.5,
                reason=f"Género con pocas canciones ({rare['track_count']})",
            )
            if sug_id:
                count += 1
        untagged = self.detect_untagged()
        if untagged["count"] > 0:
            self._repo.add_suggestion(
                "untagged",
                "sin_genero",
                affected_count=untagged["count"],
                confidence=0.7,
                reason=f"{untagged['count']} canciones sin género",
            )
            count += 1
        return count

    # ── Execution methods ──

    def execute_suggestion(self, sug_id: int) -> dict:
        suggestions = self._repo.get_pending_suggestions()
        sug = next((s for s in suggestions if s["id"] == sug_id), None)
        if not sug:
            return {"success": False, "error": "Suggestion not found"}
        sug_type = sug["suggestion_type"]
        result = {"success": False, "affected": 0}

        if sug_type == "duplicate":
            parts = sug["source_genre"].split(",")
            parts = [p.strip() for p in parts if p.strip()]
            target = sug["target_genre"] or parts[0]
            canonical = canonicalize_genre(target)
            res = self._repo.merge_genres(parts, canonical)
            result = {"success": True, "affected": res["affected"]}
        elif sug_type == "junk":
            result = {"success": True, "affected": 0, "note": "Manual review needed"}

        if result["success"]:
            self._repo.resolve_suggestion(sug_id, "accepted")
        return result

    def execute_merge(self, source_genres: list[str], target: str) -> dict:
        canonical = canonicalize_genre(target)
        result = self._repo.merge_genres(source_genres, canonical)
        # Persist aliases for future normalizations
        if result.get("affected", 0) > 0:
            for src in source_genres:
                src_norm = canonicalize_genre(src)
                if src_norm and src_norm != canonical:
                    self._repo.add_alias(src_norm, canonical, source="auto",
                                         is_user_defined=False)
        return result

    def execute_rename(self, old_name: str, new_name: str) -> int:
        canonical = canonicalize_genre(new_name)
        count = self._repo.rename_genre(old_name, canonical)
        if count:
            old_canonical = canonicalize_genre(old_name)
            if old_canonical and old_canonical != canonical:
                self._repo.add_alias(old_canonical, canonical, source="auto",
                                     is_user_defined=False)
        return count

    def execute_apply_genre(self, track_ids: list[int], genre: str,
                            write_tags: bool = False) -> int:
        return self._repo.apply_genre_to_tracks(track_ids, genre, write_tags=write_tags)

    def _get_untagged_items(self):
        all_items = self._db.get_all() or []
        return [item for item in all_items if not (getattr(item, 'genre', '') or '').strip()]
