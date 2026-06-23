"""Sync manifest builder — generates transfer manifests from local library."""

from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass, field


@dataclass
class SyncManifest:
    manifest_id: str = ""
    device_id: str = ""
    created_at: str = ""
    items: list[dict] = field(default_factory=list)
    total_size: int = 0
    total_tracks: int = 0
    destination_root: str = ""


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
            size = os.path.getsize(fp)
            name = os.path.basename(fp)
            title = str(getattr(item, "title", "") or "")
            artist = str(getattr(item, "artist", "") or "")
            album = str(getattr(item, "album", "") or "")
            dest = os.path.join(destination_root, artist, album, name)

            manifest.items.append({
                "track_id": tid,
                "source_path": fp,
                "dest_path": dest,
                "title": title,
                "artist": artist,
                "album": album,
                "size": size,
                "format": str(getattr(item, "ext", "") or "").lstrip("."),
                "checksum": _checksum(fp),
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
