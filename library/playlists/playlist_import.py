"""Playlist import service — M3U, M3U8, PLS, JSON Michi."""
from __future__ import annotations

import json
import os
import re

from library.playlists.playlist_models import PlaylistImportPreview, PlaylistImportResult


def preview_import(path: str) -> PlaylistImportPreview:
    if not os.path.isfile(path):
        return PlaylistImportPreview()
    ext = os.path.splitext(path)[1].lower()
    if ext == ".json":
        return _preview_michi_json(path)
    entries = _parse_playlist_file(path)
    return _classify_entries(entries)


def import_as_playlist(path, store, options=None):
    opts = {
        "name": os.path.splitext(os.path.basename(path))[0],
        "skip_remote": True, "skip_missing": False, ** (options or {}),
    }
    ext = os.path.splitext(path)[1].lower()
    if ext == ".json":
        return _import_michi_json(path, store, opts)
    preview = _classify_entries(_parse_playlist_file(path))
    base_dir = os.path.dirname(path)
    pid = store.create_playlist(opts["name"])
    imported = 0
    skipped = 0
    for entry in preview.entries:
        fp = entry.get("resolved_path") or entry.get("filepath", "")
        if entry.get("status") == "remote" and opts["skip_remote"]:
            skipped += 1
            continue
        if not os.path.isabs(fp):
            cand = os.path.normpath(os.path.join(base_dir, fp))
            if os.path.isfile(cand):
                fp = cand
        if os.path.isfile(fp):
            store.add_track(pid, filepath=fp, source="import")
            imported += 1
        else:
            skipped += 1
    return PlaylistImportResult(
        ok=True, playlist_id=pid, playlist_name=opts["name"],
        imported=imported, skipped=skipped,
    )


def _parse_playlist_file(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    ext = os.path.splitext(path)[1].lower()
    if ext in (".m3u8", ".m3u"):
        return _parse_m3u(content)
    if ext == ".pls":
        return _parse_pls(content)
    return []


def _parse_m3u(content):
    entries = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        entries.append({"filepath": line, "raw": line})
    return entries


def _parse_pls(content):
    entries = []
    for line in content.splitlines():
        m = re.match(r"^File\d+=(.+)$", line.strip(), re.IGNORECASE)
        if m:
            entries.append({"filepath": m.group(1).strip(), "raw": line.strip()})
    return entries


def _classify_entries(entries):
    preview = PlaylistImportPreview(total_entries=len(entries))
    seen = set()
    for e in entries:
        fp = e.get("filepath", "")
        is_remote = bool(re.match(r"^https?://", fp))
        if is_remote:
            preview.remote += 1
            e["status"] = "remote"
        elif os.path.isfile(fp) or os.path.isfile(os.path.abspath(fp)):
            preview.found += 1
            e["status"] = "found"
            e["resolved_path"] = os.path.abspath(fp)
        else:
            preview.missing += 1
            e["status"] = "missing"
        if fp in seen:
            preview.duplicates += 1
        seen.add(fp)
        preview.entries.append(e)
    return preview


def _preview_michi_json(path):
    try:
        with open(path) as f:
            data = json.load(f)
    except Exception:
        return PlaylistImportPreview()
    tracks = data.get("tracks", []) if isinstance(data, dict) else []
    return _classify_entries(
        [{"filepath": t.get("filepath", t.get("path", "")), "metadata": t} for t in tracks]
    )


def _import_michi_json(path, store, opts):
    try:
        with open(path) as f:
            data = json.load(f)
    except Exception:
        return PlaylistImportResult(ok=False, message="Invalid JSON")
    pd = data.get("playlist", {})
    name = opts.get("name") or pd.get("name", "Imported")
    pid = store.create_playlist(name, description=pd.get("description", ""))
    imported = 0
    for t in data.get("tracks", []):
        fp = t.get("filepath", t.get("path", ""))
        if fp and os.path.isfile(fp):
            store.add_track(pid, filepath=fp, source="import")
            imported += 1
    return PlaylistImportResult(ok=True, playlist_id=pid, playlist_name=name, imported=imported)
