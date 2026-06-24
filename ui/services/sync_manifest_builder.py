"""Sync manifest builder — generates Android-compatible transfer manifests."""

from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SyncManifest:
    manifest_id: str = ""
    device_id: str = ""
    created_at: str = ""
    items: list[dict] = field(default_factory=list)
    total_size: int = 0
    total_tracks: int = 0
    destination_root: str = ""

    def to_public_dict(self) -> dict[str, Any]:
        """Android-safe payload — no local file paths exposed."""
        return {
            "manifest_id": self.manifest_id,
            "device_id": self.device_id,
            "created_at": self.created_at,
            "total_tracks": self.total_tracks,
            "total_size": self.total_size,
            "tracks": [
                {
                    "track_id": item["track_id"],
                    "title": item.get("title", ""),
                    "artist": item.get("artist", ""),
                    "album": item.get("album", ""),
                    "size": item.get("size", 0),
                    "format": item.get("format", ""),
                    "duration": item.get("duration", 0),
                    "year": item.get("year", 0),
                    "genre": item.get("genre", ""),
                    "cover_id": item.get("cover_id", ""),
                    "checksum": item.get("checksum", ""),
                    "download_path": item.get("download_path", ""),
                }
                for item in self.items
            ],
        }


class SyncManifestBuilder:
    def __init__(self, db):
        self._db = db

    def build_from_tracks(self, track_ids: list[int],
                          destination_root: str = "",
                          device_id: str = "") -> SyncManifest:
        import uuid
        from sync.sync_protocol import make_track_id

        manifest = SyncManifest(
            manifest_id=str(uuid.uuid4())[:12],
            device_id=device_id,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
            destination_root=destination_root,
        )

        items = self._db.get_all() if hasattr(self._db, "get_all") else []
        id_map = {getattr(item, "id", 0): item for item in items}

        for tid in track_ids:
            item = id_map.get(tid)
            if not item:
                continue
            fp = getattr(item, "filepath", "")
            if not fp or not os.path.isfile(fp):
                continue

            tuid = getattr(item, "track_uid", "") if hasattr(item, "track_uid") else ""
            track_key = make_track_id(fp, tuid)
            size = os.path.getsize(fp)
            title = str(getattr(item, "title", "") or "")
            artist = str(getattr(item, "artist", "") or "")
            album_name = str(getattr(item, "album", "") or "")
            cover_hash = ""
            if album_name:
                import hashlib as _hashlib
                cover_hash = _hashlib.md5(album_name.encode()).hexdigest()

            manifest.items.append({
                "track_id": track_key,
                "db_id": tid,
                "source_path": fp,
                "title": title,
                "artist": artist,
                "album": album_name,
                "size": size,
                "format": str(getattr(item, "ext", "") or "").lstrip("."),
                "duration": float(getattr(item, "duration", 0) or 0),
                "year": int(getattr(item, "year", 0) or 0),
                "genre": str(getattr(item, "genre", "") or ""),
                "cover_id": cover_hash,
                "checksum": self._db.ensure_file_hash(fp) if hasattr(self._db, "ensure_file_hash") else _checksum(fp),
                "download_path": f"/api/stream/{track_key}",
            })
            manifest.total_size += size
            manifest.total_tracks += 1

        return manifest

    def build_from_playlist(self, playlist_id: int,
                            destination_root: str = "",
                            device_id: str = "") -> SyncManifest:
        track_ids = []
        if hasattr(self._db, "get_playlist_items"):
            items = self._db.get_playlist_items(playlist_id)
            track_ids = [getattr(i, "id", 0) for i in items if getattr(i, "id", 0)]
        return self.build_from_tracks(track_ids, destination_root, device_id)

    def build_from_album(self, album_title: str, artist: str = "",
                         destination_root: str = "",
                         device_id: str = "") -> SyncManifest:
        items = self._db.get_all() if hasattr(self._db, "get_all") else []
        track_ids = []
        for item in items:
            a = str(getattr(item, "artist", "") or "").lower()
            al = str(getattr(item, "album", "") or "").lower()
            if album_title.lower() in al and (not artist or artist.lower() in a):
                track_ids.append(getattr(item, "id", 0))
        return self.build_from_tracks(track_ids, destination_root, device_id)

    def build_from_favorites(self, destination_root: str = "",
                             device_id: str = "") -> SyncManifest:
        favs = self._db.get_favorites() if hasattr(self._db, "get_favorites") else []
        items = self._db.get_all() if hasattr(self._db, "get_all") else []
        fp_map = {getattr(item, "filepath", ""): getattr(item, "id", 0) for item in items}
        track_ids = [fp_map.get(f, 0) for f in favs if fp_map.get(f, 0)]
        return self.build_from_tracks(track_ids, destination_root, device_id)

    def build_delta(self, device_id: str, since: float = 0.0,
                    destination_root: str = "") -> dict:
        """Build an incremental delta manifest since a given Unix timestamp.

        Returns a dict with 'added', 'modified', 'removed' track lists.
        Uses created_at, updated_at, and deleted_at from media_items.
        """
        import uuid
        items = self._db.get_all() if hasattr(self._db, "get_all") else []

        # Also fetch soft-deleted items (not returned by get_all)
        deleted_items = []
        try:
            rows = self._db._conn.execute(
                "SELECT id, filepath, title, artist, album, duration, ext, "
                "size, year, genre, deleted_at, track_uid "
                "FROM media_items WHERE deleted_at IS NOT NULL "
                "AND deleted_at >= ?", (since,)).fetchall()
            deleted_items = [
                {"id": r[0], "filepath": r[1], "title": r[2] or "",
                 "artist": r[3] or "", "album": r[4] or "",
                 "duration": r[5] or 0, "ext": r[6] or "",
                 "size": r[7] or 0, "year": r[8] or 0,
                 "genre": r[9] or "", "track_uid": r[11] or ""}
                for r in rows
            ]
        except Exception:
            pass

        from sync.sync_protocol import make_track_id

        def _build_public(item, fp: str, tuid: str = "") -> dict:
            track_key = make_track_id(fp, tuid)
            size = int(getattr(item, "size", 0) or 0)
            album_name = str(getattr(item, "album", "") or "")
            cover_hash = ""
            if album_name:
                import hashlib as _h
                cover_hash = _h.md5(album_name.encode()).hexdigest()
            cs = ""
            if hasattr(self._db, "ensure_file_hash") and os.path.isfile(fp):
                cs = self._db.ensure_file_hash(fp)
            elif os.path.isfile(fp):
                cs = _checksum(fp)
            return {
                "track_id": track_key,
                "title": str(getattr(item, "title", "") or ""),
                "artist": str(getattr(item, "artist", "") or ""),
                "album": album_name,
                "size": size,
                "format": str(getattr(item, "ext", "") or "").lstrip("."),
                "duration": float(getattr(item, "duration", 0) or 0),
                "year": int(getattr(item, "year", 0) or 0),
                "genre": str(getattr(item, "genre", "") or ""),
                "cover_id": cover_hash,
                "checksum": cs,
                "download_path": f"/api/stream/{track_key}",
            }

        added = []
        modified = []
        for item in items:
            created = float(getattr(item, "created_at", 0) or 0)
            updated = float(getattr(item, "updated_at", 0) or 0)
            fp = getattr(item, "filepath", "")
            tuid = getattr(item, "track_uid", "") if hasattr(item, "track_uid") else ""
            if not fp or not os.path.isfile(fp):
                continue
            if created >= since - 0.5:
                added.append(_build_public(item, fp, tuid))
            elif updated >= since - 0.5:
                modified.append(_build_public(item, fp, tuid))

        removed = []
        for d in deleted_items:
            fp = d.get("filepath", "")
            tuid = d.get("track_uid", "")
            removed.append({
                "track_id": make_track_id(fp, tuid),
                "title": d.get("title", ""),
                "artist": d.get("artist", ""),
                "album": d.get("album", ""),
            })

        return {
            "manifest_id": str(uuid.uuid4())[:12],
            "device_id": device_id,
            "since": since,
            "until": time.time(),
            "added": added,
            "modified": modified,
            "removed": removed,
            "total_added": len(added),
            "total_modified": len(modified),
            "total_removed": len(removed),
        }


def _checksum(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
