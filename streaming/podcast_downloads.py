"""PodcastDownloads — download manager for podcast episodes."""

from __future__ import annotations

import logging
import os
import re
from typing import Any
from urllib.request import urlopen, Request

from streaming.podcast_models import PodcastEpisode

logger = logging.getLogger("michi.podcast.downloads")

_DOWNLOAD_DIR = ""


def set_download_dir(path: str):
    global _DOWNLOAD_DIR
    _DOWNLOAD_DIR = path


def get_download_dir() -> str:
    global _DOWNLOAD_DIR
    if not _DOWNLOAD_DIR:
        from core.paths import app_data_dir
        _DOWNLOAD_DIR = os.path.join(app_data_dir(), "podcast_downloads")
    return _DOWNLOAD_DIR


def safe_filename(title: str, max_len: int = 100) -> str:
    safe = re.sub(r'[\\/*?:"<>|]', "_", title)
    safe = re.sub(r"\s+", " ", safe).strip()
    if len(safe) > max_len:
        safe = safe[:max_len]
    return safe or "episode"


def download_episode(
    episode: PodcastEpisode,
    show_title: str = "",
    progress_cb=None,
    cancel_check=None,
) -> dict[str, Any]:
    """Download a podcast episode to the download directory.

    Args:
        episode: Episode to download.
        show_title: Show title for directory naming.
        progress_cb: Optional callback(bytes_downloaded, total_bytes).
        cancel_check: Optional callable returning True if cancelled.

    Returns dict with keys: ok, local_path, file_size, error.
    """
    if not episode.audio_url:
        return {"ok": False, "error": "No audio URL", "local_path": ""}

    dest_dir = os.path.join(get_download_dir(), safe_filename(show_title or "podcast"))
    os.makedirs(dest_dir, exist_ok=True)

    ext = _ext_for_mime(episode.mime_type)
    filename = f"{safe_filename(episode.title)}{ext}"
    dest_path = os.path.join(dest_dir, filename)

    if os.path.exists(dest_path):
        size = os.path.getsize(dest_path)
        return {"ok": True, "local_path": dest_path, "file_size": size}

    try:
        req = Request(
            episode.audio_url,
            headers={"User-Agent": "MichiMusicPlayer/1.0"},
        )
        with urlopen(req, timeout=120) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 65536
            with open(dest_path, "wb") as f:
                while True:
                    if cancel_check and cancel_check():
                        f.close()
                        os.unlink(dest_path)
                        return {"ok": False, "error": "Cancelado", "local_path": ""}
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_cb:
                        progress_cb(downloaded, total)

        file_size = os.path.getsize(dest_path)
        return {"ok": True, "local_path": dest_path, "file_size": file_size}

    except Exception as e:
        if os.path.exists(dest_path):
            import contextlib
            with contextlib.suppress(Exception):
                os.unlink(dest_path)
        return {"ok": False, "error": str(e), "local_path": ""}


def remove_download(local_path: str) -> bool:
    try:
        if os.path.isfile(local_path):
            os.unlink(local_path)
            return True
    except Exception:
        pass
    return False


def _ext_for_mime(mime: str) -> str:
    return {
        "audio/mpeg": ".mp3",
        "audio/mp3": ".mp3",
        "audio/ogg": ".ogg",
        "audio/opus": ".opus",
        "audio/aac": ".aac",
        "audio/x-m4a": ".m4a",
        "audio/mp4": ".m4a",
        "audio/flac": ".flac",
        "audio/x-flac": ".flac",
        "audio/wav": ".wav",
        "audio/webm": ".webm",
    }.get(mime, ".mp3")
