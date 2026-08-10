"""Library scanner — discovers audio files. No Qt dependency."""

from pathlib import Path

AUDIO_EXTENSIONS = {".mp3", ".flac", ".ogg", ".wav", ".m4a", ".opus", ".aac", ".wma"}


def scan_directory(root: Path) -> list[Path]:
    """Recursively scan a directory for audio files. Returns sorted paths."""
    if not root.is_dir():
        return []
    files: list[Path] = []
    for entry in sorted(root.rglob("*")):
        if entry.is_file() and entry.suffix.lower() in AUDIO_EXTENSIONS:
            files.append(entry)
    return files
