"""Playlist export service — M3U, M3U8, TXT, CSV, JSON Michi, portable pack."""
from __future__ import annotations

import csv
import json
import os
import shutil
import time

from library.playlists.playlist_models import PlaylistExportOptions


def export_m3u(store, pid: int, path: str, options: PlaylistExportOptions | None = None) -> dict:
    opts = options or PlaylistExportOptions()
    tracks = store.get_playlist_items(pid)
    pl = store.get_playlist(pid)
    lines = ["#EXTM3U", f"#PLAYLIST:{pl['name'] if pl else ''}"]
    for t in tracks:
        fp = _resolve_path(t.filepath, opts.relative_paths, os.path.dirname(path))
        dur = int(t.duration) if t.duration else -1
        lines.append(f"#EXTINF:{dur},{t.artist} - {t.title}")
        lines.append(fp)
    _atomic_write(path, "\n".join(lines), encoding="utf-8")
    return {"ok": True, "path": path, "count": len(tracks)}


def export_m3u8(store, pid: int, path: str, options: PlaylistExportOptions | None = None) -> dict:
    return export_m3u(store, pid, path, options)


def export_txt(store, pid: int, path: str) -> dict:
    tracks = store.get_playlist_items(pid)
    lines = []
    for i, t in enumerate(tracks, 1):
        dur = f"{int(t.duration//60)}:{int(t.duration%60):02d}" if t.duration else "--:--"
        lines.append(f"{i:4d}. {t.artist} — {t.title}  [{dur}]")
        if t.album:
            lines[-1] += f"  ({t.album})"
    _atomic_write(path, "\n".join(lines), encoding="utf-8")
    return {"ok": True, "path": path, "count": len(tracks)}


def export_csv(store, pid: int, path: str) -> dict:
    tracks = store.get_playlist_items(pid)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["position", "title", "artist", "album", "year", "genre",
                     "duration", "filepath", "format", "quality"])
        for t in tracks:
            w.writerow([
                t.position, t.title, t.artist, t.album, t.year, t.genre,
                t.duration, t.filepath, t.ext.upper(), t.quality_kind,
            ])
    return {"ok": True, "path": path, "count": len(tracks)}


def export_michi_json(store, pid: int, path: str,
                       include_filepaths: bool = True,
                       safe_mobile: bool = False) -> dict:
    tracks = store.get_playlist_items(pid)
    pl = store.get_playlist(pid)
    track_list = []
    for t in tracks:
        entry = {
            "position": t.position,
            "track_id": t.track_id,
            "track_uid": t.track_uid,
            "title": t.title,
            "artist": t.artist,
            "album": t.album,
            "year": t.year,
            "genre": t.genre,
            "duration": t.duration,
            "ext": t.ext,
            "bitrate": t.bitrate,
            "sample_rate": t.sample_rate,
            "bit_depth": t.bit_depth,
            "quality": t.quality_kind,
            "content_hash": t.content_hash,
        }
        if include_filepaths and not safe_mobile:
            entry["filepath"] = t.filepath
        track_list.append(entry)
    data = {
        "format": "michi.playlist.v1",
        "exported_at": time.time(),
        "playlist": {
            "id": pid,
            "name": pl["name"] if pl else "",
            "description": pl.get("description", "") if pl else "",
            "cover_type": pl.get("cover_type", "none") if pl else "none",
            "cover_path": pl.get("cover_path", "") if pl else "",
            "is_smart": bool(pl.get("is_smart", 0)) if pl else False,
        },
        "tracks": track_list,
    }
    _atomic_write(path, json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"ok": True, "path": path, "count": len(tracks)}


def export_portable_pack(store, pid: int, target_dir: str,
                          options: PlaylistExportOptions | None = None) -> dict:
    tracks = store.get_playlist_items(pid)
    pl = store.get_playlist(pid)
    os.makedirs(target_dir, exist_ok=True)
    tracks_dir = os.path.join(target_dir, "tracks")
    os.makedirs(tracks_dir, exist_ok=True)

    copied = 0
    errors = []
    track_entries = []
    for i, t in enumerate(tracks, 1):
        if not t.filepath or not os.path.isfile(t.filepath):
            errors.append(f"Missing: {t.filepath}")
            continue
        ext = os.path.splitext(t.filepath)[1]
        safe_name = _sanitize_filename(f"{i:03d}_{t.artist}_{t.title}{ext}")
        dest = os.path.join(tracks_dir, safe_name)
        try:
            shutil.copy2(t.filepath, dest)
            copied += 1
            track_entries.append(dest)
        except OSError as e:
            errors.append(f"Copy error: {t.filepath} → {e}")

    # Write M3U8
    m3u_path = os.path.join(target_dir, "playlist.m3u8")
    lines = ["#EXTM3U", f"#PLAYLIST:{pl['name'] if pl else 'Playlist'}"]
    for fp in track_entries:
        lines.append(fp)
    _atomic_write(m3u_path, "\n".join(lines), encoding="utf-8")

    # Write JSON
    json_path = os.path.join(target_dir, "playlist.michi.json")
    export_michi_json(store, pid, json_path, include_filepaths=True)

    # Write report
    report_path = os.path.join(target_dir, "report.html")
    _write_portable_report(report_path, pl, copied, len(tracks), errors)

    return {
        "ok": True,
        "path": target_dir,
        "copied": copied,
        "total": len(tracks),
        "errors": errors,
    }


# ── Internal helpers ──


def _resolve_path(filepath: str, relative: bool, base_dir: str) -> str:
    if relative and base_dir:
        try:
            return os.path.relpath(filepath, base_dir)
        except ValueError:
            return filepath
    return filepath


def _atomic_write(path: str, content: str, encoding: str = "utf-8"):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding=encoding) as f:
        f.write(content)
    os.replace(tmp, path)


def _sanitize_filename(name: str) -> str:
    safe = []
    for ch in name:
        if ch.isalnum() or ch in "._- ":
            safe.append(ch)
        else:
            safe.append("_")
    result = "".join(safe)
    while "  " in result:
        result = result.replace("  ", " ")
    return result.strip() or "untitled"


def _write_portable_report(path: str, pl: dict | None, copied: int,
                            total: int, errors: list[str]):
    name = pl["name"] if pl else "Playlist"
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Portable Pack: {name}</title>
<style>body{{font-family:sans-serif;max-width:800px;margin:2em auto;color:#333}}
h2{{color:#8FB7FF}}.ok{{color:#4CAF50}}.err{{color:#f44336}}</style></head>
<body>
<h1>Portable Pack: {name}</h1>
<p>Copied: <span class="ok">{copied}</span> / {total}</p>
"""
    if errors:
        html += "<h3>Errors:</h3><ul>"
        for e in errors:
            html += f"<li class='err'>{e}</li>"
        html += "</ul>"
    html += "</body></html>"
    _atomic_write(path, html, encoding="utf-8")
