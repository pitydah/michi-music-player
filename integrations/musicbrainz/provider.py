from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable

from core.metadata.models import (
    TrackMetadata, MetadataDocument, MetadataOperationResult,
)
from core.metadata.enums import MetadataErrorCode

logger = logging.getLogger("michi.metadata.musicbrainz")

_BASE = "https://musicbrainz.org/ws/2"
_DEFAULT_USER_AGENT = "MichiMusicPlayer/1.0 (metadata-core)"
_RATE_LIMIT_S = 1.0


class MusicBrainzProvider:
    def __init__(self, user_agent: str = _DEFAULT_USER_AGENT,
                 cache: Callable | None = None,
                 clock: Callable[[], str] | None = None):
        self._user_agent = user_agent
        self._cache = cache
        self._clock = clock or (lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        self._throttle_ts: float = 0.0

    def search_artist(self, query: str) -> MetadataOperationResult:
        return self._search("artist", query)

    def search_release(self, query: str) -> MetadataOperationResult:
        return self._search("release", query)

    def search_recording(self, query: str) -> MetadataOperationResult:
        return self._search("recording", query)

    def lookup_artist(self, mbid: str) -> MetadataOperationResult:
        return self._lookup(f"artist/{mbid}", {"inc": "aliases+tags+genres"})

    def lookup_release(self, mbid: str) -> MetadataOperationResult:
        return self._lookup(f"release/{mbid}", {"inc": "artists+recordings+tags+genres"})

    def lookup_release_group(self, mbid: str) -> MetadataOperationResult:
        return self._lookup(f"release-group/{mbid}", {"inc": "artists+tags+genres"})

    def lookup_recording(self, mbid: str) -> MetadataOperationResult:
        return self._lookup(f"recording/{mbid}", {"inc": "artists+releases+tags+genres"})

    def lookup_by_isrc(self, isrc: str) -> MetadataOperationResult:
        return self._search("recording", f"isrc:{isrc}")

    def _search(self, entity: str, query: str) -> MetadataOperationResult:
        if not query:
            return MetadataOperationResult(
                ok=False, code=MetadataErrorCode.INVALID_PATH.value,
                message="Empty query",
            )
        url = f"{_BASE}/{entity}?query={urllib.parse.quote(query)}&fmt=json"
        return self._request(url)

    def _lookup(self, path: str, params: dict | None = None) -> MetadataOperationResult:
        url = f"{_BASE}/{path}?fmt=json"
        if params:
            url += "&" + urllib.parse.urlencode(params)
        return self._request(url)

    def _request(self, url: str) -> MetadataOperationResult:
        elapsed = time.monotonic() - self._throttle_ts
        if elapsed < _RATE_LIMIT_S:
            time.sleep(_RATE_LIMIT_S - elapsed)
        self._throttle_ts = time.monotonic()

        req = urllib.request.Request(url)
        req.add_header("User-Agent", self._user_agent)
        req.add_header("Accept", "application/json")

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return MetadataOperationResult(ok=True, data={"response": data})
        except urllib.error.HTTPError as e:
            code = MetadataErrorCode.NOT_FOUND if e.code == 404 else MetadataErrorCode.PROVIDER_UNAVAILABLE
            return MetadataOperationResult(
                ok=False, code=code.value, message=f"HTTP {e.code}",
                retryable=e.code >= 500,
            )
        except urllib.error.URLError as e:
            return MetadataOperationResult(
                ok=False, code=MetadataErrorCode.NETWORK_ERROR.value,
                message=str(e.reason), retryable=True,
            )
        except json.JSONDecodeError:
            return MetadataOperationResult(
                ok=False, code=MetadataErrorCode.PROVIDER_INVALID_RESPONSE.value,
                message="Invalid JSON",
            )
        except Exception as e:
            return MetadataOperationResult(
                ok=False, code=MetadataErrorCode.INTERNAL_ERROR.value,
                message=str(e),
            )

    def to_document(self, data: dict, source: str = "musicbrainz") -> MetadataDocument:
        doc = MetadataDocument(format=source)
        track = TrackMetadata()

        if "id" in data:
            track.musicbrainz_recording_id = data.get("id", "")

        if "title" in data:
            track.title = data.get("title", "")
        if "artist-credit" in data:
            track.artists = [ac.get("name", "") for ac in data["artist-credit"] if isinstance(ac, dict)]
        if "length" in data:
            track.replaygain_track_peak = float(data["length"]) / 1000

        doc.track = track
        return doc

    def close(self):
        pass
