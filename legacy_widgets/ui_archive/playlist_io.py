"""Playlist I/O — M3U/PLS import/export with rich diagnostics and atomic writes."""

from __future__ import annotations

import contextlib
import logging
import os
from dataclasses import dataclass

logger = logging.getLogger("michi.playlist_io")


@dataclass
class PlaylistEntry:
    path: str
    exists: bool
    is_remote: bool
    original_line: str
    resolved_path: str


def parse_playlist_entries(path: str) -> list[PlaylistEntry]:
    """Parse M3U/PLS and return structured entries preserving missing/remote info."""
    ext = os.path.splitext(path)[1].lower()
    if ext in (".m3u", ".m3u8"):
        return _parse_m3u_entries(path)
    elif ext == ".pls":
        return _parse_pls_entries(path)
    return []


def import_playlist(path: str) -> list[str]:
    """Legacy: auto-detect format, return only existing file paths."""
    ext = os.path.splitext(path)[1].lower()
    if ext in (".m3u", ".m3u8"):
        return parse_m3u(path)
    elif ext == ".pls":
        return parse_pls(path)
    return []


def parse_m3u(path: str) -> list[str]:
    """Parse M3U, returns list of existing absolute file paths (legacy)."""
    entries = _parse_m3u_entries(path)
    return [e.resolved_path for e in entries if e.exists and not e.is_remote]


def parse_pls(path: str) -> list[str]:
    """Parse PLS, returns list of existing absolute file paths (legacy)."""
    entries = _parse_pls_entries(path)
    return [e.resolved_path for e in entries if e.exists and not e.is_remote]


def _parse_m3u_entries(path: str) -> list[PlaylistEntry]:
    entries: list[PlaylistEntry] = []
    base = os.path.dirname(os.path.abspath(path))
    if not os.path.exists(path):
        return entries
    with open(path, "r", errors="ignore") as f:
        for line in f:
            original = line.strip()
            if not original or original.startswith("#"):
                continue
            is_remote = original.startswith("http://") or original.startswith("https://")
            if is_remote:
                entries.append(PlaylistEntry(
                    path=original, exists=False, is_remote=True,
                    original_line=original, resolved_path=original))
                continue
            resolved = original if os.path.isabs(original) else os.path.join(base, original)
            exists = os.path.exists(resolved)
            entries.append(PlaylistEntry(
                path=original, exists=exists, is_remote=False,
                original_line=original, resolved_path=resolved))
    return entries


def _parse_pls_entries(path: str) -> list[PlaylistEntry]:
    entries: list[PlaylistEntry] = []
    base = os.path.dirname(os.path.abspath(path))
    if not os.path.exists(path):
        return entries
    with open(path, "r", errors="ignore") as f:
        for line in f:
            original = line.strip()
            if not original.lower().startswith("file"):
                continue
            eq = original.find("=")
            if eq <= 0:
                continue
            filepath = original[eq + 1:].strip()
            is_remote = filepath.startswith("http://") or filepath.startswith("https://")
            if is_remote:
                entries.append(PlaylistEntry(
                    path=filepath, exists=False, is_remote=True,
                    original_line=original, resolved_path=filepath))
                continue
            resolved = filepath if os.path.isabs(filepath) else os.path.join(base, filepath)
            exists = os.path.exists(resolved)
            entries.append(PlaylistEntry(
                path=filepath, exists=exists, is_remote=is_remote,
                original_line=original, resolved_path=resolved))
    return entries


def export_m3u(path: str, filepaths: list[str], title: str = "Playlist"):
    """Export file paths to M3U with UTF-8 encoding and atomic write."""
    tmp = path + ".tmp"
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(f"#EXTM3U\n#EXTINF:{title}\n")
            for fp in filepaths:
                f.write(fp + "\n")
            f.flush()
            with contextlib.suppress(OSError):
                os.fsync(f.fileno())
        os.replace(tmp, path)
        return path
    except OSError as e:
        logger.warning("export_m3u failed for %s: %s", path, e)
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise
