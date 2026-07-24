"""Centralized logging configuration."""
import logging
import logging.handlers
import os
import sys

LOG_LEVEL = os.environ.get("MICHI_LOG_LEVEL", "INFO").upper()
LOG_FILE = os.environ.get("MICHI_LOG_FILE", "")

def setup_logging():
    root = logging.getLogger()
    root.setLevel(LOG_LEVEL)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)
    root.addHandler(handler)

    if LOG_FILE:
        file_handler = logging.handlers.RotatingFileHandler(
            LOG_FILE, maxBytes=10*1024*1024, backupCount=3
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    return root
