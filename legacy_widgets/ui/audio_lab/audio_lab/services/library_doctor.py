"""Library Doctor — SQLite-powered metadata diagnostics and repair plans."""

from __future__ import annotations

import unicodedata
from collections import Counter
from typing import Any


class LibraryDoctor:
    def __init__(self, db: Any):
        self._db = db

    def scan_missing_metadata(self) -> list[dict]:
        items = self._db.get_all() if hasattr(self._db, "get_all") else []
        results = []
        for item in items:
            missing = []
            if not str(getattr(item, "title", "") or "").strip():
                missing.append("title")
            if not str(getattr(item, "artist", "") or "").strip():
                missing.append("artist")
            if not str(getattr(item, "album", "") or "").strip():
                missing.append("album")
            if not str(getattr(item, "genre", "") or "").strip():
                missing.append("genre")
            if not getattr(item, "year", 0):
                missing.append("year")
            if not str(getattr(item, "albumartist", "") or "").strip():
                missing.append("albumartist")
            if missing:
                results.append({
                    "track_id": getattr(item, "id", 0),
                    "title": str(getattr(item, "title", "") or ""),
                    "artist": str(getattr(item, "artist", "") or ""),
                    "album": str(getattr(item, "album", "") or ""),
                    "missing_fields": missing,
                })
        return results

    def detect_duplicate_artists(self) -> list[dict]:
        items = self._db.get_all() if hasattr(self._db, "get_all") else []
        norm_map: dict[str, list[str]] = {}
        raw_names: set[str] = set()

        for item in items:
            raw = str(getattr(item, "artist", "") or "").strip()
            if not raw:
                continue
            raw_names.add(raw)
            norm = _normalize_key(raw)
            if norm:
                norm_map.setdefault(norm, []).append(raw)

        duplicates = []
        for _, names in norm_map.items():
            unique = list(set(names))
            if len(unique) > 1:
                most_common = Counter(unique).most_common(1)[0][0]
                total_tracks = sum(1 for item in items if str(getattr(item, "artist", "") or "").strip() in unique)
                duplicates.append({
                    "canonical_name": most_common,
                    "variants": [n for n in unique if n != most_common],
                    "total_variants": len(unique) - 1,
                    "total_tracks": total_tracks,
                })

        duplicates.sort(key=lambda x: x["total_variants"], reverse=True)
        return duplicates[:50]

    def detect_split_albums(self) -> list[dict]:
        items = self._db.get_all() if hasattr(self._db, "get_all") else []
        grouped: dict[str, list[dict]] = {}

        for item in items:
            artist = str(getattr(item, "artist", "") or "").strip()
            album = str(getattr(item, "album", "") or "").strip()
            if not artist or not album:
                continue
            norm_artist = _normalize_key(artist)
            norm_album = _normalize_key(album)
            key = f"{norm_artist}|{norm_album}"
            grouped.setdefault(key, []).append({
                "artist": artist,
                "album": album,
                "norm_artist": norm_artist,
                "norm_album": norm_album,
                "track_id": getattr(item, "id", 0),
            })

        splits = []
        for _, entries in grouped.items():
            raw_albums = list(set(e["album"] for e in entries))
            if len(raw_albums) > 1:
                total_tracks = len(entries)
                main = Counter(e["album"] for e in entries).most_common(1)[0][0]
                splits.append({
                    "canonical_artist": entries[0]["artist"],
                    "canonical_album": main,
                    "album_variants": [a for a in raw_albums if _normalize_key(a) != _normalize_key(main)],
                    "total_variants": len(raw_albums) - 1,
                    "total_tracks": total_tracks,
                })

        splits.sort(key=lambda x: x["total_variants"], reverse=True)
        return splits[:50]

    def detect_missing_artwork(self) -> list[dict]:
        items = self._db.get_all() if hasattr(self._db, "get_all") else []
        albums: dict[str, dict] = {}
        for item in items:
            artist = str(getattr(item, "artist", "") or "").strip()
            album = str(getattr(item, "album", "") or "").strip()
            if not artist or not album:
                continue
            key = f"{artist.lower()}|{album.lower()}"
            if key not in albums:
                has_cover = self._check_album_has_cover(artist, album)
                albums[key] = {
                    "artist": artist, "album": album,
                    "has_cover": has_cover, "track_count": 0,
                }
            albums[key]["track_count"] += 1

        missing = []
        for _, info in albums.items():
            if not info["has_cover"]:
                missing.append({
                    "artist": info["artist"],
                    "album": info["album"],
                    "track_count": info["track_count"],
                })

        missing.sort(key=lambda x: x["track_count"], reverse=True)
        return missing[:100]

    def _check_album_has_cover(self, artist: str, album: str) -> bool:
        try:
            table_check = self._db.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='album_art_cache'"
            ).fetchone()
            if not table_check:
                return False
            row = self._db.conn.execute(
                "SELECT id FROM album_art_cache WHERE artist_name=? AND album_title=? LIMIT 1",
                (artist, album),
            ).fetchone()
            return row is not None
        except Exception:
            return False

    def detect_possible_duplicates(self) -> list[dict]:
        items = self._db.get_all() if hasattr(self._db, "get_all") else []
        seen: dict[str, list[dict]] = {}

        for item in items:
            title = str(getattr(item, "title", "") or "").strip()
            artist = str(getattr(item, "artist", "") or "").strip()
            dur = getattr(item, "duration", 0) or 0
            if not title or not artist:
                continue
            key = f"{_normalize_key(title)}|{_normalize_key(artist)}|{int(dur)}"
            seen.setdefault(key, []).append({
                "track_id": getattr(item, "id", 0),
                "title": title,
                "artist": artist,
                "duration": dur,
                "filepath": str(getattr(item, "filepath", "") or ""),
            })

        duplicates = []
        for _, entries in seen.items():
            if len(entries) > 1:
                duplicates.append({
                    "title": entries[0]["title"],
                    "artist": entries[0]["artist"],
                    "count": len(entries),
                    "track_ids": [e["track_id"] for e in entries],
                })

        duplicates.sort(key=lambda x: x["count"], reverse=True)
        return duplicates[:50]

    def scan_all(self) -> dict:
        return {
            "missing_metadata": len(self.scan_missing_metadata()),
            "duplicate_artists": len(self.detect_duplicate_artists()),
            "split_albums": len(self.detect_split_albums()),
            "missing_artwork": len(self.detect_missing_artwork()),
            "possible_duplicates": len(self.detect_possible_duplicates()),
        }

    def generate_repair_plan(self) -> dict:
        issues = self.scan_all()
        total = sum(issues.values())
        fixable = issues["missing_metadata"] + issues["duplicate_artists"]
        suggestions = []

        if issues["missing_metadata"]:
            suggestions.append({
                "category": "missing_metadata",
                "count": issues["missing_metadata"],
                "action": "Usa Smart Tagging con MusicBrainz para completar campos vacios.",
                "severity": "medium",
            })
        if issues["duplicate_artists"]:
            suggestions.append({
                "category": "duplicate_artists",
                "count": issues["duplicate_artists"],
                "action": "Normaliza nombres de artista. Usa Metadata Studio para unificar.",
                "severity": "medium",
            })
        if issues["split_albums"]:
            suggestions.append({
                "category": "split_albums",
                "count": issues["split_albums"],
                "action": "Álbumes partidos detectados. Corrige el campo 'album' en Metadata Studio.",
                "severity": "low",
            })
        if issues["missing_artwork"]:
            suggestions.append({
                "category": "missing_artwork",
                "count": issues["missing_artwork"],
                "action": "Álbumes sin carátula. Usa Smart Tagging para descargar covers.",
                "severity": "low",
            })
        if issues["possible_duplicates"]:
            suggestions.append({
                "category": "possible_duplicates",
                "count": issues["possible_duplicates"],
                "action": "Posibles duplicados detectados. Revisa manualmente.",
                "severity": "info",
            })

        return {
            "total_issues": total,
            "fixable": fixable,
            "suggestions": suggestions,
        }


def _normalize_key(text: str) -> str:
    text = text.lower().strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = "".join(c for c in text if c.isalnum() or c.isspace())
    return " ".join(text.split())
