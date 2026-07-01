"""Playlist sync manifest — for Michi Link, Mobile, and Micro Server."""
from __future__ import annotations

import hashlib
import time

from library.playlists.playlist_models import PlaylistSyncManifest, PlaylistSyncManifestEntry


def build_manifest(store, db_conn, device_id: str = "desktop") -> PlaylistSyncManifest:
    """Build a complete sync manifest of all playlists."""
    summaries = store.get_all_playlists(include_stats=True)
    entries = []
    for s in summaries:
        tracks = store.get_playlist_items(s.id)
        tracks_hash = _hash_tracks(tracks)
        rules_hash = ""
        if s.is_smart:
            pl = store.get_playlist(s.id)
            rules_raw = pl.get("rules_json", "") if pl else ""
            rules_hash = hashlib.sha256((rules_raw).encode()).hexdigest()[:16]
        entries.append(PlaylistSyncManifestEntry(
            id=str(s.id),
            name=s.name,
            description=s.description,
            updated_at=s.updated_at,
            sync_version=s.sync_version,
            is_smart=s.is_smart,
            rules_hash=rules_hash,
            cover_id=f"pl_{s.id}",
            track_count=s.track_count,
            duration=s.total_duration,
            tracks_hash=tracks_hash,
        ))
    return PlaylistSyncManifest(
        generated_at=time.time(),
        device_id=device_id,
        playlists=entries,
    )


def build_delta(store, db_conn, since: float, device_id: str = "desktop") -> dict:
    """Build a delta manifest for incremental sync."""
    manifest = build_manifest(store, db_conn, device_id)
    changed = [p for p in manifest.playlists if p.updated_at > since]
    deleted = _find_deleted_since(store, db_conn, since)
    return {
        "format": "michi.playlists.delta.v1",
        "since": since,
        "generated_at": time.time(),
        "changed": [p.__dict__ for p in changed],
        "deleted_ids": deleted,
    }


def serialize_manifest_safe(manifest: PlaylistSyncManifest) -> dict:
    """Serialize without exposing local filepaths (for mobile sync)."""
    return {
        "format": manifest.format,
        "generated_at": manifest.generated_at,
        "device_id": manifest.device_id,
        "playlists": [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "updated_at": p.updated_at,
                "sync_version": p.sync_version,
                "is_smart": p.is_smart,
                "rules_hash": p.rules_hash,
                "cover_id": p.cover_id,
                "track_count": p.track_count,
                "duration": p.duration,
                "tracks_hash": p.tracks_hash,
            }
            for p in manifest.playlists
        ],
        "deleted_ids": manifest.deleted_ids,
    }


def _hash_tracks(tracks: list) -> str:
    h = hashlib.sha256()
    for t in tracks:
        h.update(f"{t.track_id}:{t.filepath}:{t.position},".encode())
    return h.hexdigest()[:16]


def _find_deleted_since(store, db_conn, since: float) -> list[int]:
    """Find playlists that were deleted by checking IDs that existed before."""
    current = {s.id for s in store.get_all_playlists(include_stats=False)}
    all_possible = db_conn.execute(
        "SELECT id FROM playlists WHERE created_at < ?", (since,)
    ).fetchall()
    deleted = []
    for r in all_possible:
        if r["id"] not in current:
            deleted.append(r["id"])
    return deleted
