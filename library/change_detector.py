"""Change detector — determines if a file needs re-indexing.

Uses a hierarchical strategy:
  Level 1: size + mtime (fast, no I/O beyond stat)
  Level 2: quick hash (first + last 64KB) when mtime changed but size didn't
  Level 3: full SHA-256 (opt-in, for sync manifest)

Results are cached in memory per session to avoid redundant re-hashing.
"""
import hashlib
import os
import logging

logger = logging.getLogger("michi.change_detector")

_HASH_CACHE: dict[str, str] = {}
_MAX_CACHE_SIZE = 5000


def _cache_get(filepath: str) -> str | None:
    return _HASH_CACHE.get(filepath)


def _cache_set(filepath: str, h: str):
    if len(_HASH_CACHE) >= _MAX_CACHE_SIZE:
        _HASH_CACHE.clear()
    _HASH_CACHE[filepath] = h


def clear_cache():
    _HASH_CACHE.clear()


def is_file_unchanged(db, filepath: str, stat: os.stat_result) -> bool:
    """Return True if the file hasn't changed since its last DB entry.

    Hierarchy:
      1. Not in DB → must scan (returns False)
      2. Size differs → must scan
      3. Size same, mtime same, hash matches in DB and cache → skip
      4. Size same, mtime same, hash matches on disk → skip
      5. Size same, mtime same, no hash yet → skip (trust size+mtime)
      6. Size same, mtime changed → verify with quick hash
    """
    sig = db.get_file_signature(filepath)
    if sig is None:
        return False

    db_size, db_mtime, db_hash = sig

    # Size changed — definitely modified
    if stat.st_size != db_size:
        return False

    # Size same, mtime same — check cached or stored hash
    if stat.st_mtime == db_mtime:
        cached = _cache_get(filepath)
        if cached:
            return cached == db_hash
        if db_hash:
            current_hash = compute_quick_hash(filepath)
            _cache_set(filepath, current_hash)
            return current_hash == db_hash
        return True

    # Size same but mtime changed — might be a touch or metadata update
    cached = _cache_get(filepath)
    if cached:
        return cached == db_hash

    current_hash = compute_quick_hash(filepath)
    _cache_set(filepath, current_hash)
    if not db_hash:
        return True
    return current_hash == db_hash


def compute_quick_hash(filepath: str) -> str:
    """SHA-256 of first 64KB + last 64KB for fast content verification."""
    h = hashlib.sha256()
    try:
        size = os.path.getsize(filepath)
        with open(filepath, "rb") as f:
            h.update(f.read(min(65536, size)))
            if size > 65536:
                f.seek(max(0, size - 65536))
                h.update(f.read(65536))
        return h.hexdigest()
    except OSError as e:
        logger.debug("compute_quick_hash failed for %s: %s", filepath, e)
        return ""


def compute_full_hash(filepath: str) -> str:
    """Full SHA-256 of entire file. Intended for sync/verification."""
    h = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError as e:
        logger.debug("compute_full_hash failed for %s: %s", filepath, e)
        return ""
