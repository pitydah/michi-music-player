"""Centralized logger for Michi Music Player.

Logs to ~/.local/share/michi-music-player/logs/michi.log (rotating, 5MB x 3 backups).
Console output only when MICHI_DEBUG=1 or --debug flag.

setup_logging() must be called explicitly from main.py — no auto-setup on import.
"""

import logging
import logging.handlers
import os
import sys

LOG_FILE = None  # set after setup_logging() is called


def _is_debug() -> bool:
    return os.environ.get("MICHI_DEBUG") == "1" or "--debug" in sys.argv


def setup_logging():
    global LOG_FILE
    from core.paths import logs_dir, log_file
    log_dir = logs_dir()
    try:
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "michi.log")
    except OSError:
        log_path = log_file()
        os.makedirs(os.path.dirname(log_path), exist_ok=True)

    LOG_FILE = log_path

    logger = logging.getLogger("michi")
    logger.setLevel(logging.DEBUG if _is_debug() else logging.INFO)

    if logger.handlers:
        return

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    try:
        fh = logging.handlers.RotatingFileHandler(
            log_path, maxBytes=5 * 1024 * 1024, backupCount=3)
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except OSError:
        ch = logging.StreamHandler(sys.stderr)
        ch.setLevel(logging.WARNING)
        ch.setFormatter(fmt)
        logger.addHandler(ch)
        logger.warning("Cannot write to log file %s — logging to stderr", log_path)
        return

    if _is_debug():
        ch = logging.StreamHandler(sys.stderr)
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(fmt)
        logger.addHandler(ch)

    logging.getLogger("PIL").setLevel(logging.WARNING)

    _log = logging.getLogger("michi.runtime")
    _log.info("Python %s · PySide6 %s", sys.version.split()[0], _pyside_version())
    _log.info("Log file: %s", log_path)


def _pyside_version() -> str:
    try:
        from PySide6 import __version_info__
        return ".".join(map(str, __version_info__[:3]))
    except Exception:
        return "unknown"


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"michi.{name}")


# Explicit call required — no auto-setup on import
