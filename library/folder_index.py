"""Folder Index — directory-based navigation for audio files.

All public functions cache results per directory with a configurable TTL
(default 5 seconds) to avoid redundant filesystem reads during rapid
navigation (e.g. arrow keys in FolderBrowser).
"""
import os
import time

_AUDIO_EXTS = frozenset({
    ".mp3", ".flac", ".ogg", ".wav", ".m4a", ".aac", ".opus",
    ".dsf", ".dff", ".aiff", ".ape", ".wv", ".wma", ".spx",
})

_cache: dict[str, tuple[float, list[str] | list[str]]] = {}
_CACHE_TTL = 5.0


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
                if os.path.isdir(full):
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
        except Exception:
            pass
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
