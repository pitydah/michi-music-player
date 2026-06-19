"""Playlist I/O — M3U/PLS import/export."""

import os


def parse_m3u(path: str) -> list[str]:
    """Parse M3U playlist, returns list of absolute file paths."""
    files = []
    base = os.path.dirname(path)
    if not os.path.exists(path):
        return files
    with open(path, "r", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                if os.path.isabs(line):
                    files.append(line)
                else:
                    files.append(os.path.join(base, line))
    return [f for f in files if os.path.exists(f)]


def parse_pls(path: str) -> list[str]:
    """Parse PLS playlist, returns list of absolute file paths."""
    files = []
    base = os.path.dirname(path)
    if not os.path.exists(path):
        return files
    with open(path, "r", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line.lower().startswith("file"):
                eq = line.find("=")
                if eq > 0:
                    filepath = line[eq + 1:].strip()
                    if os.path.isabs(filepath):
                        files.append(filepath)
                    else:
                        full = os.path.join(base, filepath)
                        if os.path.exists(full):
                            files.append(full)
    return files


def export_m3u(path: str, filepaths: list[str], title: str = "Playlist"):
    """Export file paths to M3U format."""
    with open(path, "w") as f:
        f.write(f"#EXTM3U\n#EXTINF:{title}\n")
        for fp in filepaths:
            f.write(fp + "\n")
    return path


def import_playlist(path: str) -> list[str]:
    """Auto-detect format and import."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".m3u" or ext == ".m3u8":
        return parse_m3u(path)
    elif ext == ".pls":
        return parse_pls(path)
    return []
