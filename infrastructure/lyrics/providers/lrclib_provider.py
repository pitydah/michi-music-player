from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request

from core.lyrics.interfaces import LyricsProvider, LyricsCacheRepository
from core.lyrics.models import (
    ProviderContract, TrackIdentity, LyricsDocument, LyricsOperationResult,
    LyricsSource, LyricsErrorCode, MatchConfidence,
    LyricsMetadata, LyricsAttribution,
)
from core.lyrics.parser import parse_lrc

logger = logging.getLogger("michi.lyrics.providers.lrclib")

_BASE = "https://lrclib.net/api"


class LrcLibProvider(LyricsProvider):
    def __init__(self, cache: LyricsCacheRepository | None = None,
                 clock: callable | None = None):
        self._cache = cache
        self._clock = clock or (lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        self._throttle_ts: float = 0.0

    @property
    def contract(self) -> ProviderContract:
        return ProviderContract(
            provider_id="lrclib",
            display_name="LRCLIB",
            priority=10,
            supports_exact=True,
            supports_search=True,
            supports_synced=True,
            supports_plain=True,
            requires_network=True,
            rate_limit_rps=1.0,
            timeout_ms=10000,
            attribution=LyricsAttribution(
                source_label="lrclib.net",
                provider_url="https://lrclib.net",
                provider_id="lrclib",
                license_hint="Public API — see lrclib.net terms",
                terms_reference="https://lrclib.net/docs",
            ),
        )

    def resolve(self, identity: TrackIdentity,
                timeout_ms: int = 10000) -> LyricsOperationResult:
        cache_key = self._cache_key(identity)
        if self._cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return LyricsOperationResult(
                    ok=True, document=cached,
                    source=LyricsSource.CACHE,
                )

        result = self._fetch(identity, timeout_ms)
        if result.ok and result.document and self._cache:
            self._cache.put(cache_key, result.document)
        elif not result.ok and (result.code == LyricsErrorCode.NOT_FOUND or result.code == "not_found") and self._cache:
            self._cache.put_negative(cache_key)

        return result

    def search(self, identity: TrackIdentity,
               timeout_ms: int = 10000) -> LyricsOperationResult:
        query = f"{identity.artist} {identity.title}".strip()
        if not query:
            query = identity.title or ""
        if not query:
            return LyricsOperationResult(
                ok=False, code=LyricsErrorCode.INVALID_IDENTITY,
                message="No searchable metadata",
            )

        try:
            url = f"{_BASE}/search?q={urllib.parse.quote(query)}"
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "MichiMusicPlayer/1.0 (lyrics)")
            req.add_header("Accept", "application/json")

            with urllib.request.urlopen(req, timeout=timeout_ms / 1000) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            candidates: list[LyricsDocument] = []
            if isinstance(data, list):
                for entry in data[:10]:
                    doc = self._entry_to_doc(entry, identity)
                    if doc:
                        candidates.append(doc)

            return LyricsOperationResult(
                ok=True, candidates=candidates,
                source=LyricsSource.REMOTE_PROVIDER,
            )
        except urllib.error.HTTPError as e:
            return LyricsOperationResult(
                ok=False, code=LyricsErrorCode.PROVIDER_UNAVAILABLE
                if e.code >= 500 else LyricsErrorCode.NOT_FOUND,
                message=f"HTTP {e.code}",
            )
        except urllib.error.URLError as e:
            return LyricsOperationResult(
                ok=False, code=LyricsErrorCode.NETWORK_ERROR,
                message=str(e.reason),
            )
        except json.JSONDecodeError:
            return LyricsOperationResult(
                ok=False, code=LyricsErrorCode.PROVIDER_INVALID_RESPONSE,
                message="Invalid JSON",
            )
        except Exception as e:
            logger.exception("LRCLIB search failed")
            return LyricsOperationResult(
                ok=False, code=LyricsErrorCode.INTERNAL_ERROR,
                message=str(e),
            )

    def close(self):
        pass

    def _fetch(self, identity: TrackIdentity, timeout_ms: int) -> LyricsOperationResult:
        try:
            elapsed = time.monotonic() - self._throttle_ts
            if elapsed < 1.0:
                time.sleep(1.0 - elapsed)
            self._throttle_ts = time.monotonic()

            params = {}
            if identity.artist:
                params["artist_name"] = identity.artist
            if identity.title:
                params["track_name"] = identity.title
            if identity.album:
                params["album_name"] = identity.album
            if identity.duration_ms > 0:
                params["duration"] = str(int(identity.duration_ms / 1000))

            url = f"{_BASE}/get?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "MichiMusicPlayer/1.0 (lyrics)")
            req.add_header("Accept", "application/json")

            with urllib.request.urlopen(req, timeout=timeout_ms / 1000) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            doc = self._entry_to_doc(data, identity)
            if doc is None:
                return LyricsOperationResult(
                    ok=False, code=LyricsErrorCode.NOT_FOUND,
                    message="No lyrics in response",
                )
            return LyricsOperationResult(
                ok=True, document=doc,
                source=LyricsSource.REMOTE_PROVIDER,
            )
        except urllib.error.HTTPError as e:
            code = LyricsErrorCode.NOT_FOUND if e.code == 404 else LyricsErrorCode.PROVIDER_UNAVAILABLE
            return LyricsOperationResult(
                ok=False, code=code, message=f"HTTP {e.code}",
                retryable=e.code >= 500,
            )
        except urllib.error.URLError as e:
            return LyricsOperationResult(
                ok=False, code=LyricsErrorCode.NETWORK_ERROR,
                message=str(e.reason), retryable=True,
            )
        except json.JSONDecodeError:
            return LyricsOperationResult(
                ok=False, code=LyricsErrorCode.PROVIDER_INVALID_RESPONSE,
                message="Invalid JSON",
            )
        except Exception as e:
            logger.exception("LRCLIB fetch failed")
            return LyricsOperationResult(
                ok=False, code=LyricsErrorCode.INTERNAL_ERROR,
                message=str(e),
            )

    def _entry_to_doc(self, entry: dict, identity: TrackIdentity) -> LyricsDocument | None:
        synced = entry.get("syncedLyrics", "") or ""
        plain = entry.get("plainLyrics", "") or ""

        if not synced and not plain:
            return None

        now = self._clock()
        doc = LyricsDocument(
            identity=identity,
            plain_text=plain,
            synced_text=synced,
            source=LyricsSource.REMOTE_PROVIDER,
            provider_id="lrclib",
            provider_item_id=str(entry.get("id", "")),
            fetched_at=now,
            match_confidence=MatchConfidence.UNKNOWN,
            metadata=LyricsMetadata(
                artist=entry.get("artistName", ""),
                album=entry.get("albumName", ""),
                title=entry.get("trackName", ""),
            ),
            duration_ms=int(entry.get("duration", 0)) * 1000,
            attribution=self.contract.attribution,
        )

        if synced:
            parsed = parse_lrc(synced)
            doc.lines = parsed.lines
            doc.metadata = _merge_metadata(doc.metadata, parsed.metadata)
            doc.offset_ms = parsed.offset_ms

        return doc

    @staticmethod
    def _cache_key(identity: TrackIdentity) -> str:
        return f"lrclib:{identity.title.lower().strip()}|{identity.artist.lower().strip()}"


def _merge_metadata(base: LyricsMetadata, override: LyricsMetadata) -> LyricsMetadata:
    merged = LyricsMetadata(
        artist=override.artist or base.artist,
        album=override.album or base.album,
        title=override.title or base.title,
        author=override.author or base.author,
        editor=override.editor or base.editor,
        version=override.version or base.version,
        language=override.language or base.language,
        offset_ms=override.offset_ms or base.offset_ms,
    )
    return merged
