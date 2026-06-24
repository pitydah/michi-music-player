"""Change detector — determines if a file needs re-indexing.

Compares filesystem stats (size, mtime) against the database,
then verifies with a SHA-256 quick hash (first + last 64KB).
"""
import hashlib
import os


def is_file_unchanged(db, filepath: str, stat: os.stat_result) -> bool:
    """Return True if the file hasn't changed since its last DB entry."""
    sig = db.get_file_signature(filepath)
    if sig is None:
        return False  # not in DB yet

    db_size, db_mtime, db_hash = sig
    if (stat.st_size, stat.st_mtime) != (db_size, db_mtime):
        return False  # size or mtime changed — re-scan

    if db_hash:
        current_hash = compute_quick_hash(filepath)
        return current_hash == db_hash

    return True  # no hash stored yet, trust size+mtime


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
    except OSError:
        return ""
