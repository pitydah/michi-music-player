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

            track_key = make_track_id(fp)
            size = os.path.getsize(fp)

            manifest.items.append({
                "track_id": track_key,
                "db_id": tid,
                "source_path": fp,
                "title": str(getattr(item, "title", "") or ""),
                "artist": str(getattr(item, "artist", "") or ""),
                "album": str(getattr(item, "album", "") or ""),
                "size": size,
                "format": str(getattr(item, "ext", "") or "").lstrip("."),
                "duration": float(getattr(item, "duration", 0) or 0),
                "year": int(getattr(item, "year", 0) or 0),
                "genre": str(getattr(item, "genre", "") or ""),
                "cover_id": str(getattr(item, "mb_album_id", "") or ""),
                "checksum": _checksum(fp),
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


def _checksum(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
