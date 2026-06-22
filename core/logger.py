"""Centralized logger for Michi Music Player.

Logs to ~/.local/share/michi-music-player/michi.log
Console output only when ASTRA_DEBUG=1 or --debug flag.
"""

import logging
import os
import sys

LOG_DIR = os.path.expanduser("~/.local/share/michi-music-player")
LOG_FILE = os.path.join(LOG_DIR, "michi.log")


def _is_debug() -> bool:
    return os.environ.get("ASTRA_DEBUG") == "1" or "--debug" in sys.argv


def setup_logging():
    os.makedirs(LOG_DIR, exist_ok=True)

    logger = logging.getLogger("michi")
    logger.setLevel(logging.DEBUG if _is_debug() else logging.INFO)

    if logger.handlers:
        return

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    fh = logging.FileHandler(LOG_FILE)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    if _is_debug():
        ch = logging.StreamHandler(sys.stderr)
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(fmt)
        logger.addHandler(ch)

    # Suppress noisy third-party loggers
    logging.getLogger("PIL").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"michi.{name}")


# Auto-setup on import
setup_logging()
