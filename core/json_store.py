"""JSON persistence helpers — atomic writes, safe reads, corrupt-file recovery."""

import contextlib
import json
import logging
import os
import time

logger = logging.getLogger("michi.json_store")


def atomic_write_json(path: str, data) -> bool:
    """Write JSON atomically via temp file + os.replace. Returns True on success."""
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            with contextlib.suppress(OSError):
                os.fsync(f.fileno())
        os.replace(tmp, path)
        return True
    except (OSError, TypeError) as e:
        logger.warning("atomic_write_json failed for %s: %s", path, e)
        with contextlib.suppress(OSError):
            os.unlink(path + ".tmp")
        return False


def read_json_safe(path: str, default=None, backup_corrupt: bool = True):
    """Read JSON from path. On corrupt/invalid data, rename to .broken and return default."""
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("read_json_safe failed for %s: %s", path, e)
        if backup_corrupt:
            _backup_corrupt_file(path)
        return default


def _backup_corrupt_file(path: str):
    try:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup = f"{path}.broken.{timestamp}"
        os.rename(path, backup)
        logger.warning("Corrupt JSON backed up: %s", backup)
    except OSError:
        logger.debug("Failed to backup corrupt file: %s", path)
