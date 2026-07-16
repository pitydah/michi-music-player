"""Sync manifest builder — generates Android-compatible transfer manifests."""

from __future__ import annotations

import contextlib
import hashlib
import os
import time
from dataclasses import dataclass, field
from typing import Any

from sync.sync_protocol import make_cover_id, make_track_id


@dataclass
class SyncManifest:
    manifest_id: str = ""
    device_id: str = ""
    created_at: str = ""
    items: list[dict] = field(default_factory=list)
    playlists: list[dict] = field(default_factory=list)
    removed: list[dict] = field(default_factory=list)
    total_size: int = 0
    total_tracks: int = 0
    destination_root: str = ""

    def to_public_dict(self) -> dict[str, Any]:
        """Android-safe payload — no local file paths exposed. Michi Sync Manifest v1."""
        return {
            "schema": "michi.sync.manifest",
            "version": 1,
            "manifest_id": self.manifest_id,
            "device_id": self.device_id,
            "created_at": self.created_at,
            "total_tracks": self.total_tracks,
            "total_size": self.total_size,
            "profile": {
                "audio": "original",
                "artwork": "embedded",
                "lyrics": False,
                "replaygain": True,
            },
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
            "playlists": self.playlists,
            "removed": self.removed,
        }


class SyncManifestBuilder:
    def __init__(self, db):
        self._db = db

    def build_from_tracks(self, track_ids: list[int],
                          destination_root: str = "",
                          device_id: str = "") -> SyncManifest:
        import uuid

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
            cover_hash = make_cover_id(album_name, artist)

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
        playlist_name = ""
        if hasattr(self._db, "get_playlist_items"):
            items = self._db.get_playlist_items(playlist_id)
            track_ids = [getattr(i, "id", 0) for i in items if getattr(i, "id", 0)]
        if hasattr(self._db, "get_playlists"):
            for p in self._db.get_playlists():
                if p["id"] == playlist_id:
                    playlist_name = p.get("name", "")
                    break
        manifest = self.build_from_tracks(track_ids, destination_root, device_id)

        manifest.playlists = [{
            "playlist_id": f"desktop:{playlist_id}",
            "name": playlist_name,
            "track_ids": [t["track_id"] for t in manifest.items],
            "updated_at": int(time.time()),
        }]
        return manifest

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

        # Also fetch soft-deleted items via public API
        deleted_items = []
        with contextlib.suppress(Exception):
            deleted_items = self._db.get_deleted_since(since)


        def _build_public(item, fp: str, tuid: str = "") -> dict:
            track_key = make_track_id(fp, tuid)
            size = int(getattr(item, "size", 0) or 0)
            album_name = str(getattr(item, "album", "") or "")
            cover_hash = make_cover_id(album_name, str(getattr(item, "artist", "") or ""))
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
