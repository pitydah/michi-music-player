"""File Manager Service — detect desktop environment and open files/folders.

Pure service, no Qt imports. Uses subprocess with shlex.quote for safety.
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import logging

logger = logging.getLogger("michi.file_manager")


class FileManagerService:
    """Detect available file managers and open/reveal files in them."""

    @staticmethod
    def available_file_managers() -> list[tuple[str, str]]:
        """Return list of (name, binary) for available file managers."""
        candidates = [
            ("Dolphin", "dolphin"),
            ("Nautilus", "nautilus"),
            ("Nemo", "nemo"),
            ("Thunar", "thunar"),
            ("PCManFM-Qt", "pcmanfm-qt"),
        ]
        available = []
        for name, binary in candidates:
            if shutil.which(binary):
                available.append((name, binary))
        return available

    @staticmethod
    def preferred_file_manager() -> tuple[str, str] | None:
        """Return (name, binary) of the best available file manager."""
        fm_list = FileManagerService.available_file_managers()
        if not fm_list:
            return None
        names = {n.lower() for n, _ in fm_list}
        desktop = FileManagerService.detect_desktop().lower()

        if "kde" in desktop or "plasma" in desktop:
            for n, b in fm_list:
                if n.lower() == "dolphin":
                    return (n, b)
        if "gnome" in desktop:
            for n, b in fm_list:
                if n.lower() == "nautilus":
                    return (n, b)
        if "cinnamon" in desktop or "x-cinnamon" in desktop:
            for n, b in fm_list:
                if n.lower() == "nemo":
                    return (n, b)
        if "xfce" in desktop:
            for n, b in fm_list:
                if n.lower() == "thunar":
                    return (n, b)
        if "lxqt" in desktop:
            for n, b in fm_list:
                if n.lower() == "pcmanfm-qt":
                    return (n, b)

        return fm_list[0]

    @staticmethod
    def detect_desktop() -> str:
        """Detect desktop environment from environment variables."""
        for var in ("XDG_CURRENT_DESKTOP", "DESKTOP_SESSION",
                    "KDE_FULL_SESSION", "GNOME_DESKTOP_SESSION_ID"):
            val = os.environ.get(var, "")
            if val:
                return val
        return ""

    @staticmethod
    def preferred_file_manager_name() -> str:
        """Return readable name of preferred file manager, or fallback."""
        pref = FileManagerService.preferred_file_manager()
        return pref[0] if pref else "Gestor de archivos"

    @staticmethod
    def open_folder(path: str) -> bool:
        """Open a folder in the preferred file manager."""
        if not path or not os.path.isdir(path):
            logger.warning("open_folder: invalid path %s", path)
            return False
        cmd = FileManagerService.build_open_command(path)
        if not cmd:
            return False
        try:
            subprocess.Popen(cmd, start_new_session=True)
            return True
        except Exception as e:
            logger.warning("open_folder failed: %s", e)
            return False

    @staticmethod
    def reveal_file(path: str) -> bool:
        """Reveal/highlight a file in the file manager."""
        if not path or not os.path.exists(path):
            logger.warning("reveal_file: invalid path %s", path)
            return False
        cmd = FileManagerService.build_reveal_command(path)
        if not cmd:
            return False
        try:
            subprocess.Popen(cmd, start_new_session=True)
            return True
        except Exception as e:
            logger.warning("reveal_file failed: %s", e)
            return False

    @staticmethod
    def open_terminal_here(path: str) -> bool:
        """Open a terminal emulator at the given directory."""
        if not path or not os.path.isdir(path):
            logger.warning("open_terminal: invalid path %s", path)
            return False
        cmd = FileManagerService._build_terminal_command(path)
        if not cmd:
            return False
        try:
            subprocess.Popen(cmd, start_new_session=True)
            return True
        except Exception as e:
            logger.warning("open_terminal failed: %s", e)
            return False

    @staticmethod
    def build_open_command(path: str) -> list[str] | None:
        """Build command list to open a folder."""
        target = path if os.path.isdir(path) else os.path.dirname(path)
        pref = FileManagerService.preferred_file_manager()
        if pref:
            return [pref[1], target]
        return ["xdg-open", target]

    @staticmethod
    def build_reveal_command(path: str) -> list[str] | None:
        """Build command list to reveal/select a file."""
        if not os.path.exists(path):
            return None
        pref = FileManagerService.preferred_file_manager()
        if pref:
            name, binary = pref
            if name.lower() == "dolphin":
                return [binary, "--select", path]
            if name.lower() == "nautilus":
                return [binary, "--select", path]
            if name.lower() == "nemo":
                return [binary, path]
            if name.lower() == "thunar":
                return [binary, path]
            if name.lower() == "pcmanfm-qt":
                return [binary, path]
        folder = os.path.dirname(path) if os.path.isfile(path) else path
        return ["xdg-open", folder]

    @staticmethod
    def _build_terminal_command(path: str) -> list[str] | None:
        """Build command list to open a terminal at path."""
        quoted = shlex.quote(path)
        candidates = [
            (shutil.which("konsole"), ["konsole", "--workdir", path]),
            (shutil.which("gnome-terminal"),
             ["gnome-terminal", f"--working-directory={path}"]),
            (shutil.which("xfce4-terminal"),
             ["xfce4-terminal", f"--working-directory={path}"]),
            (shutil.which("kitty"), ["kitty", "-d", path]),
            (shutil.which("alacritty"), ["alacritty", "--working-directory", path]),
        ]
        for exists, cmd in candidates:
            if exists:
                return cmd
        return None
