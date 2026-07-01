"""MPD Path Mapper — resolves differences between Michi file paths and MPD paths.

Michi paths are absolute filesystem paths (/home/user/Music/Album/track.flac).
MPD paths are relative to its music_directory (Album/track.flac).

This mapper uses settings to translate between the two.
"""

import os

from core.settings_manager import get


class MpdPathMapper:
    """Bidirectional path mapping between Michi and MPD."""

    def __init__(self, music_dir: str = "", local_root: str = ""):
        self._music_dir = music_dir or get("audio/mpd/music_directory") or os.path.expanduser("~/Música")
        self._local_root = local_root or get("audio/mpd/local_music_root") or self._music_dir
        self._mapping_enabled = True

    @property
    def music_directory(self) -> str:
        return self._music_dir

    def to_mpd_path(self, local_path: str) -> str:
        """Convert an absolute local path to a relative MPD path.

        /home/user/Music/Album/track.flac → Album/track.flac
        """
        if not self._mapping_enabled:
            return local_path
        local_path = os.path.normpath(local_path)
        root = os.path.normpath(self._local_root)
        if local_path.startswith(root + "/") or local_path.startswith(root + os.sep):
            rel = local_path[len(root) + 1:]
            return rel
        if local_path.startswith(root):
            rel = local_path[len(root):]
            return rel.lstrip("/")
        return local_path

    def from_mpd_path(self, mpd_path: str) -> str:
        """Convert a relative MPD path to an absolute local path.

        Album/track.flac → /home/user/Music/Album/track.flac
        """
        if not self._mapping_enabled:
            return mpd_path
        if os.path.isabs(mpd_path):
            return mpd_path
        return os.path.normpath(os.path.join(self._local_root, mpd_path))

    def set_music_directory(self, path: str):
        self._music_dir = path

    def set_local_root(self, path: str):
        self._local_root = path
