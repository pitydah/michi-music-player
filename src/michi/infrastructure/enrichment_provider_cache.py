"""Provider-response cache (M6.9B) — filesystem authority, SEPARATE from
enrichment.db (schema 3 stays frozen).

Layout: <root>/<key[:2]>/<key>.json
Key: sha256 of "provider|canonical-url".
Atomic writes (temp + os.replace); corrupt entries are discarded safely.
Fresh entries serve offline; expired entries are only readable via
get_stale() (knowledge-only stale policy — identity never remaps from
stale candidate caches).

Default TTLs (M6.9 contract):
- musicbrainz search/identity: 7 days
- musicbrainz lookup: 30 days
- wikidata: 30 days
- wikipedia: 7 days
- commons metadata: 30 days
- cover art archive JSON: 30 days
"""

import base64
import hashlib
import json
import os
import time
from pathlib import Path

from michi.application.enrichment_ports import (
    HttpResponse,
    ProviderCacheEntry,
    ProviderCachePort,
)

DEFAULT_TTLS_SECONDS = {
    "musicbrainz_search": 7 * 86400,
    "musicbrainz_lookup": 30 * 86400,
    "wikidata": 30 * 86400,
    "wikipedia": 7 * 86400,
    "commons": 30 * 86400,
    "coverart": 30 * 86400,
}
DEFAULT_TTL_SECONDS = 7 * 86400


class FilesystemProviderCache(ProviderCachePort):
    """Atomic, bounded, corruption-tolerant provider cache."""

    def __init__(self, root_dir: Path, clock=time.time) -> None:
        self._root = root_dir
        self._clock = clock

    @staticmethod
    def cache_key(provider: str, url: str) -> str:
        return hashlib.sha256(
            f"{provider}|{url}".encode("utf-8")
        ).hexdigest()

    def _entry_path(self, key: str) -> Path:
        return self._root / key[:2] / f"{key}.json"

    def get(self, provider: str, url: str) -> ProviderCacheEntry | None:
        entry = self._load(provider, url)
        if entry is None:
            return None
        if entry.expires_at <= self._clock():
            return None  # expired: not fresh
        return entry

    def get_stale(self, provider: str, url: str) -> ProviderCacheEntry | None:
        """Expired-but-readable entry — for KNOWLEDGE offline display
        only. Never for identity authority decisions."""
        return self._load(provider, url)

    def _load(self, provider: str, url: str) -> ProviderCacheEntry | None:
        path = self._entry_path(self.cache_key(provider, url))
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if not isinstance(payload, dict):
            return None
        try:
            entry = ProviderCacheEntry(
                provider=str(payload["provider"]),
                url=str(payload["url"]),
                status_code=int(payload["status"]),
                body=base64.b64decode(payload["body_b64"]),
                retrieved_at=float(payload["retrieved_at"]),
                expires_at=float(payload["expires_at"]),
                etag=str(payload.get("etag", "")),
                last_modified=str(payload.get("last_modified", "")),
            )
        except (KeyError, TypeError, ValueError):
            # Corrupt cache entry: discard safely, never crash.
            self._discard(path)
            return None
        if entry.provider != provider or entry.url != url:
            self._discard(path)
            return None
        return entry

    def put(
        self,
        provider: str,
        url: str,
        response: HttpResponse,
        ttl_seconds: float,
        etag: str = "",
        last_modified: str = "",
    ) -> None:
        now = self._clock()
        payload = {
            "provider": provider,
            "url": url,
            "status": response.status_code,
            "body_b64": base64.b64encode(response.body).decode("ascii"),
            "retrieved_at": now,
            "expires_at": now + ttl_seconds,
            "etag": etag,
            "last_modified": last_modified,
        }
        path = self._entry_path(self.cache_key(provider, url))
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        temp.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        os.replace(temp, path)

    def remove_expired(self, older_than_days: int = 90) -> int:
        """Bounded explicit maintenance: delete entries whose expires_at
        is older than the retention window. Returns removed count."""
        horizon = self._clock() - older_than_days * 86400
        removed = 0
        if not self._root.exists():
            return 0
        for path in self._root.rglob("*.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                expires_at = float(payload.get("expires_at", 0))
            except (OSError, ValueError, TypeError):
                path.unlink(missing_ok=True)
                removed += 1
                continue
            if expires_at < horizon:
                path.unlink(missing_ok=True)
                removed += 1
        return removed

    @staticmethod
    def _discard(path: Path) -> None:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
