"""Folder Index — directory-based navigation for audio files.

All public functions cache results per directory with a configurable TTL
(default 5 seconds) to avoid redundant filesystem reads during rapid
navigation (e.g. arrow keys in FolderBrowser).
"""
import os
import time

from library.folder_models import FolderEntry
from library.metadata_extractor import AUDIO_EXTS as _AUDIO_EXTS

_cache: dict[str, tuple[float, list[str] | list[str]]] = {}
_CACHE_TTL = 5.0

_COVER_NAMES = frozenset({
    "cover.jpg", "cover.png", "folder.jpg", "folder.png",
    "front.jpg", "front.png", "album.jpg", "album.png",
    "art.jpg", "art.png", "portada.jpg", "portada.png",
    "Cover.jpg", "Cover.png", "Folder.jpg", "Folder.png",
})
_PLAYLIST_EXTS = frozenset({".m3u", ".m3u8", ".pls", ".xspf"})
_CUE_LOG_EXTS = frozenset({".cue", ".log"})
_TEXT_EXTS = frozenset({".txt", ".nfo"})
_UNSUPPORTED_AUDIO_EXTS = frozenset({
    ".ape", ".wv", ".tta", ".mka", ".tak", ".aiff", ".aif",
}) - _AUDIO_EXTS


def _cached(key: str, ttl: float = _CACHE_TTL):
    entry = _cache.get(key)
    if entry and (time.time() - entry[0]) < ttl:
        return entry[1]
    return None


def _store(key: str, value):
    _cache[key] = (time.time(), value)


def clear_cache():
    _cache.clear()


def list_audio_files(directory: str) -> list[str]:
    """List all audio files in a directory (non-recursive). Returns cached result."""
    cached = _cached(f"files:{directory}")
    if cached is not None:
        return list(cached)
    files = []
    try:
        for f in sorted(os.listdir(directory)):
            if not f.startswith("."):
                full = os.path.join(directory, f)
                if os.path.isfile(full) and os.path.splitext(f)[1].lower() in _AUDIO_EXTS:
                    files.append(full)
    except (PermissionError, FileNotFoundError):
        pass
    _store(f"files:{directory}", files)
    return files


def list_subfolders(directory: str) -> list[str]:
    """List subdirectories (non-recursive). Returns cached result."""
    cached = _cached(f"dirs:{directory}")
    if cached is not None:
        return list(cached)
    dirs = []
    try:
        for f in sorted(os.listdir(directory)):
            if not f.startswith("."):
                full = os.path.join(directory, f)
                if os.path.isdir(full) and not os.path.islink(full):
                    dirs.append(full)
    except (PermissionError, FileNotFoundError):
        pass
    _store(f"dirs:{directory}", dirs)
    return dirs


def get_folder_duration(directory: str) -> float:
    """Return total duration (seconds) of all audio files in a directory."""
    total = 0.0
    for fp in list_audio_files(directory):
        try:
            from library.metadata_extractor import extract_metadata_combined
            meta = extract_metadata_combined(fp)
            total += meta.get("duration", 0.0) or 0.0
        except Exception as e:
            import logging
            logging.getLogger("michi.folder_index").debug(
                "get_folder_duration failed for %s: %s", fp, e)
    return total


def get_audio_tree(root: str, max_depth: int = 3) -> dict:
    """Return a nested dict of {name: {files: [...], folders: {...}}}."""
    result = {"files": list_audio_files(root), "folders": {}}
    if max_depth <= 0:
        return result
    for folder in list_subfolders(root):
        name = os.path.basename(folder)
        result["folders"][name] = get_audio_tree(folder, max_depth - 1)
    return result


def classify_file(path: str) -> FolderEntry:
    """Classify a single file or directory into a FolderEntry."""
    entry = FolderEntry.from_path(path)

    if os.path.isdir(path) and not os.path.islink(path):
        entry.kind = "folder"
        return entry

    if not os.path.isfile(path):
        entry.kind = "error"
        entry.problems.append("not_a_file")
        return entry

    ext = os.path.splitext(path)[1].lower()
    entry.ext = ext

    if ext in _AUDIO_EXTS:
        entry.kind = "audio"
        entry.is_supported_audio = True
        entry.format_label = ext.lstrip(".").upper()
    elif ext in _UNSUPPORTED_AUDIO_EXTS:
        entry.kind = "unsupported_audio"
        entry.format_label = ext.lstrip(".").upper()
        entry.problems.append("unsupported_format")
    elif is_cover_file(path):
        entry.kind = "cover"
        entry.format_label = ext.lstrip(".").upper()
    elif is_playlist_file(path):
        entry.kind = "playlist"
        entry.format_label = ext.lstrip(".").upper()
    elif is_cue_or_log(path):
        entry.kind = "cue" if ext == ".cue" else "log"
    elif ext in _TEXT_EXTS:
        entry.kind = "text"
    else:
        entry.kind = "unknown"

    return entry


def is_cover_file(path: str) -> bool:
    """Check if a path is a known cover/sidecar image."""
    name = os.path.basename(path).lower()
    return name in _COVER_NAMES


def is_playlist_file(path: str) -> bool:
    """Check if a path is a playlist file."""
    ext = os.path.splitext(path)[1].lower()
    return ext in _PLAYLIST_EXTS


def is_cue_or_log(path: str) -> bool:
    """Check if a path is a .cue or .log file."""
    ext = os.path.splitext(path)[1].lower()
    return ext in _CUE_LOG_EXTS


def list_folder_entries(directory: str, include_hidden: bool = False) -> list[FolderEntry]:
    """List all entries in a directory as FolderEntry objects."""
    entries = []
    try:
        for name in sorted(os.listdir(directory)):
            if not include_hidden and name.startswith("."):
                continue
            full = os.path.join(directory, name)
            try:
                entry = classify_file(full)
                entries.append(entry)
            except Exception:
                pass
    except (PermissionError, FileNotFoundError):
        pass
    return entries


def walk_audio_files(root: str, max_depth: int | None = None,
                     include_hidden: bool = False) -> list[str]:
    """Recursively walk a directory tree for audio files."""
    result = []
    _walk_audio(root, result, max_depth or 999, 0, include_hidden)
    return result


def _walk_audio(root: str, result: list[str], max_depth: int,
                depth: int, include_hidden: bool):
    if depth > max_depth:
        return
    try:
        for name in sorted(os.listdir(root)):
            if not include_hidden and name.startswith("."):
                continue
            full = os.path.join(root, name)
            if os.path.isdir(full) and not os.path.islink(full):
                _walk_audio(full, result, max_depth, depth + 1, include_hidden)
            elif os.path.isfile(full):
                ext = os.path.splitext(name)[1].lower()
                if ext in _AUDIO_EXTS:
                    result.append(full)
    except (PermissionError, FileNotFoundError):
        pass


def walk_folder_entries(root: str, max_depth: int | None = None,
                        include_hidden: bool = False) -> list[FolderEntry]:
    """Recursively walk a directory tree returning FolderEntry objects."""
    result = []
    _walk_entries(root, result, max_depth or 999, 0, include_hidden)
    return result


def _walk_entries(root: str, result: list[FolderEntry], max_depth: int,
                  depth: int, include_hidden: bool):
    if depth > max_depth:
        return
    try:
        for name in sorted(os.listdir(root)):
            full = os.path.join(root, name)
            if os.path.isdir(full) and not os.path.islink(full):
                if not include_hidden and name.startswith("."):
                    continue
                result.append(FolderEntry(
                    path=full, name=name, kind="folder",
                    is_hidden=name.startswith(".")))
                _walk_entries(full, result, max_depth, depth + 1, include_hidden)
            elif os.path.isfile(full):
                try:
                    entry = classify_file(full)
                    result.append(entry)
                except Exception:
                    pass
    except (PermissionError, FileNotFoundError):
        pass
