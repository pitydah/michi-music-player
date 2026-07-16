"""File actions — pure logic, no QtWidgets dependency."""
from __future__ import annotations

import os
import subprocess
import logging


logger = logging.getLogger("michi.file_actions")


def open_containing_folder(filepath: str) -> bool:
    if not filepath:
        return False
    folder = os.path.dirname(filepath)
    if not folder or not os.path.isdir(folder):
        logger.warning("Cannot open containing folder for missing path: %s", filepath)
        return False
    try:
        subprocess.Popen(["xdg-open", folder])
        return True
    except Exception:
        logger.exception("Failed to open containing folder: %s", folder)
        return False
