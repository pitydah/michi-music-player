"""Filesystem library scanner — implements LibraryScannerPort."""

from pathlib import Path

from michi.application.library_port import LibraryScannerPort

AUDIO_EXTENSIONS = {".mp3", ".flac", ".ogg", ".wav", ".m4a", ".opus", ".aac", ".wma"}


class FilesystemLibraryScanner(LibraryScannerPort):
    """Infrastructure adapter: recursively discovers audio files."""

    def scan(self, root: Path) -> list[Path]:
        if not root.is_dir():
            return []
        files: list[Path] = []
        for entry in sorted(root.rglob("*")):
            if entry.is_file() and entry.suffix.lower() in AUDIO_EXTENSIONS:
                files.append(entry)
        return files
