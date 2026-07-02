"""Broadcast diagnostics — validate radio stream URLs and podcast RSS feeds."""

from __future__ import annotations

from typing import Any
from urllib.request import urlopen, Request


def diagnose_stream(url: str, timeout: int = 10) -> dict[str, Any]:
    """Validate a radio stream URL.

    Returns dict with:
        ok, content_type, redirected, final_url, error, is_playlist
    """
    result: dict[str, Any] = {
        "ok": False,
        "content_type": "",
        "redirected": False,
        "final_url": url,
        "error": "",
        "is_playlist": False,
    }

    if not url.startswith(("http://", "https://")):
        result["error"] = "La URL debe comenzar con http:// o https://"
        return result

    playlist_exts = (".m3u", ".m3u8", ".pls", ".asx", ".xspf")
    if any(url.lower().endswith(ext) for ext in playlist_exts):
        result["is_playlist"] = True

    try:
        req = Request(url, method="HEAD", headers={"User-Agent": "MichiMusicPlayer/1.0"})
        resp = urlopen(req, timeout=timeout)
        result["ok"] = True
        result["content_type"] = resp.headers.get("Content-Type", "")
        result["final_url"] = resp.url
        result["redirected"] = resp.url != url
    except Exception:
        # Try GET if HEAD fails
        try:
            req = Request(url, headers={"User-Agent": "MichiMusicPlayer/1.0"})
            resp = urlopen(req, timeout=timeout)
            result["ok"] = True
            result["content_type"] = resp.headers.get("Content-Type", "")
            result["final_url"] = resp.url
            result["redirected"] = resp.url != url
        except Exception as e2:
            result["error"] = str(e2)

    return result


def diagnose_feed(feed_url: str, timeout: int = 15) -> dict[str, Any]:
    """Validate a podcast RSS feed URL.

    Returns dict with:
        ok, title, episodes, errors, warnings
    """
    result: dict[str, Any] = {
        "ok": False,
        "title": "",
        "episodes": 0,
        "errors": [],
        "warnings": [],
    }

    if not feed_url.startswith(("http://", "https://")):
        result["errors"].append("La URL debe comenzar con http:// o https://")
        return result

    from streaming.podcast_feed_parser import parse_feed
    parsed = parse_feed(feed_url, timeout=timeout)
    result["ok"] = parsed.ok
    result["errors"] = parsed.errors
    result["warnings"] = parsed.warnings
    if parsed.show:
        result["title"] = parsed.show.title
    result["episodes"] = len(parsed.episodes)
    return result
