"""Playlist import service — M3U, M3U8, PLS, JSON Michi."""
from __future__ import annotations

import json
import os
import re

from library.playlists.playlist_models import PlaylistImportPreview, PlaylistImportResult


def preview_import(path: str) -> PlaylistImportPreview:
    """Analyze an import file without importing.

    Returns a preview with counts of found/missing/remote/duplicate entries.
    """
    if not os.path.isfile(path):
        return PlaylistImportPreview()
    ext = os.path.splitext(path)[1].lower()
    if ext == ".json":
        return _preview_michi_json(path)
    entries = _parse_playlist_file(path)
    return _classify_entries(entries)


def import_as_playlist(path: str, store, options: dict | None = None) -> PlaylistImportResult:
    """Import a playlist file into the database via PlaylistStore.

    Options:
        name: str — playlist name (default: filename stem)
        skip_remote: bool — skip remote URLs (default: True)
        skip_missing: bool — skip missing files (default: False)
        resolve_links: bool — attempt to relink missing (default: False)
    """
    opts = {
        "name": os.path.splitext(os.path.basename(path))[0],
        "skip_remote": True,
        "skip_missing": False,
        "resolve_links": False,
        **(options or {}),
    }
    ext = os.path.splitext(path)[1].lower()
    if ext == ".json":
        return _import_michi_json(path, store, opts)
    entries = _parse_playlist_file(path)
    preview = _classify_entries(entries)
    base_dir = os.path.dirname(path)
    pid = store.create_playlist(opts["name"])
    imported = 0
    skipped = 0
    for entry in preview.entries:
        fp = entry.get("resolved_path") or entry.get("filepath", "")
        if (not fp or entry.get("status") == "remote") and opts["skip_remote"]:
            skipped += 1
            continue
        if entry.get("status") == "missing" and opts["skip_missing"]:
            skipped += 1
            continue
        if not os.path.isabs(fp):
            candidate = os.path.normpath(os.path.join(base_dir, fp))
            if os.path.isfile(candidate):
                fp = candidate
        if os.path.isfile(fp):
            store.add_track(pid, filepath=fp, source="import")
            imported += 1
        else:
            skipped += 1
    return PlaylistImportResult(
        ok=True, playlist_id=pid, playlist_name=opts["name"],
        imported=imported, skipped=skipped,
        message=f"Imported {imported} tracks ({skipped} skipped)",
    )


def _parse_playlist_file(path: str) -> list[dict]:
    ext = os.path.splitext(path)[1].lower()
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    if ext in (".m3u8", ".m3u"):
        return _parse_m3u(content)
    if ext == ".pls":
        return _parse_pls(content)
    return []


def _parse_m3u(content: str) -> list[dict]:
    entries = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        entries.append({"filepath": line, "raw": line})
    return entries


def _parse_pls(content: str) -> list[dict]:
    entries = []
    for line in content.splitlines():
        line = line.strip()
        m = re.match(r"^File\d+=(.+)$", line, re.IGNORECASE)
        if m:
            entries.append({"filepath": m.group(1).strip(), "raw": line})
    return entries


def _classify_entries(entries: list[dict]) -> PlaylistImportPreview:
    preview = PlaylistImportPreview(total_entries=len(entries))
    seen = set()
    for entry in entries:
        fp = entry.get("filepath", "")
        is_remote = bool(re.match(r"^https?://", fp))
        if is_remote:
            preview.remote += 1
            entry["status"] = "remote"
        elif os.path.isfile(fp) or os.path.isfile(os.path.abspath(fp)):
            preview.found += 1
            entry["status"] = "found"
            entry["resolved_path"] = os.path.abspath(fp)
        else:
            preview.missing += 1
            entry["status"] = "missing"
        if fp in seen:
            preview.duplicates += 1
        seen.add(fp)
        preview.entries.append(entry)
    return preview


def _preview_michi_json(path: str) -> PlaylistImportPreview:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return PlaylistImportPreview(message="Invalid JSON")
    tracks = data.get("tracks", []) if isinstance(data, dict) else []
    entries = []
    for t in tracks:
        fp = t.get("filepath", t.get("path", ""))
        entries.append({"filepath": fp, "metadata": t})
    return _classify_entries(entries)


def _import_michi_json(path: str, store, opts: dict) -> PlaylistImportResult:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return PlaylistImportResult(ok=False, message="Invalid JSON file")
    pl_data = data.get("playlist", {})
    name = opts.get("name") or pl_data.get("name", "Imported Playlist")
    tracks = data.get("tracks", [])
    pid = store.create_playlist(name, description=pl_data.get("description", ""))
    imported = 0
    for t in tracks:
        fp = t.get("filepath", t.get("path", ""))
        if fp and os.path.isfile(fp):
            store.add_track(pid, filepath=fp, source="import")
            imported += 1
    return PlaylistImportResult(
        ok=True, playlist_id=pid, playlist_name=name,
        imported=imported,
        message=f"Imported {imported}/{len(tracks)} tracks from JSON",
    )
