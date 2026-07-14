from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

from core.metadata.models import (
    ArtworkMetadata, MetadataOperationResult,
)
from core.metadata.enums import MetadataErrorCode

_BASE = "https://coverartarchive.org"
_USER_AGENT = "MichiMusicPlayer/1.0 (metadata-core)"
_MAX_ARTWORK_BYTES = 10485760


class CoverArtProvider:
    def __init__(self):
        self._throttle_ts: float = 0.0

    def resolve(self, release_mbid: str) -> MetadataOperationResult:
        if not release_mbid:
            return MetadataOperationResult(
                ok=False, code=MetadataErrorCode.INVALID_PATH.value,
                message="No release MBID",
            )
        url = f"{_BASE}/release/{release_mbid}"
        req = urllib.request.Request(url)
        req.add_header("User-Agent", _USER_AGENT)

        elapsed = time.monotonic() - self._throttle_ts
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)
        self._throttle_ts = time.monotonic()

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return MetadataOperationResult(
                ok=False, code=MetadataErrorCode.NOT_FOUND.value if e.code == 404 else MetadataErrorCode.PROVIDER_UNAVAILABLE.value,
                message=f"HTTP {e.code}",
            )
        except Exception as e:
            return MetadataOperationResult(
                ok=False, code=MetadataErrorCode.NETWORK_ERROR.value,
                message=str(e),
            )

        images = data.get("images", [])
        artworks = []
        for img in images:
            if not img.get("image"):
                continue
            aw = ArtworkMetadata(
                artwork_id=img.get("id", ""),
                picture_type=img.get("types", ["front_cover"])[0] if img.get("types") else "front_cover",
                mime_type=self._detect_mime(img.get("image", "")),
                description=img.get("comment", ""),
            )
            artworks.append(aw)

        front = [a for a in artworks if a.picture_type == "front_cover"]
        return MetadataOperationResult(
            ok=True,
            data={
                "artworks": artworks,
                "front_cover": front[0] if front else None,
                "count": len(artworks),
            },
        )

    def download(self, url: str) -> MetadataOperationResult:
        if not url:
            return MetadataOperationResult(
                ok=False, code=MetadataErrorCode.INVALID_PATH.value,
            )
        req = urllib.request.Request(url)
        req.add_header("User-Agent", _USER_AGENT)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
            if len(data) > _MAX_ARTWORK_BYTES:
                return MetadataOperationResult(
                    ok=False, code=MetadataErrorCode.INVALID_VALUE.value,
                    message="Artwork exceeds size limit",
                )
            return MetadataOperationResult(ok=True, data={"bytes": data})
        except Exception as e:
            return MetadataOperationResult(
                ok=False, code=MetadataErrorCode.NETWORK_ERROR.value,
                message=str(e),
            )

    @staticmethod
    def _detect_mime(url: str) -> str:
        lower = url.lower()
        if lower.endswith(".png"):
            return "image/png"
        if lower.endswith(".gif"):
            return "image/gif"
        return "image/jpeg"
