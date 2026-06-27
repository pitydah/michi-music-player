"""AlbumInfoRepository — LRU cache for AlbumSummary objects."""
from collections import OrderedDict
from metadata.album_summary import AlbumSummary


class AlbumInfoRepository:
    def __init__(self, max_size: int = 200):
        self._lru: OrderedDict[str, AlbumSummary] = OrderedDict()
        self._max_size = max_size

    def has(self, album_key: str) -> bool:
        return album_key in self._lru

    def get_summary(self, album_key: str,
                    fallback_data: list | None = None) -> AlbumSummary | None:
        # 1. LRU cache hit
        if album_key in self._lru:
            self._lru.move_to_end(album_key)
            return self._lru[album_key]

        # 2. Artist metadata local cache
        from integrations.artist_metadata.album_cache import AlbumCache
        cached = AlbumCache().get_metadata(album_key)
        if cached:
            summary = _dict_to_summary(cached)
            if summary:
                self._put(album_key, summary)
                return summary

        # 3. Build from fallback data (CoverFlowItem tracks)
        if fallback_data:
            summary = self._build_from_tracks(album_key, fallback_data)
            self._put(album_key, summary)
            return summary

        return None

    def preload(self, album_keys: list[str], fallback_map: dict = None):
        for key in album_keys:
            if key not in self._lru:
                fb = (fallback_map or {}).get(key)
                self.get_summary(key, fb)

    def invalidate(self, album_key: str):
        self._lru.pop(album_key, None)

    def update_summary(self, album_key: str, summary: AlbumSummary):
        self._put(album_key, summary)

    def _put(self, key: str, summary: AlbumSummary):
        self._lru[key] = summary
        self._lru.move_to_end(key)
        while len(self._lru) > self._max_size:
            self._lru.popitem(last=False)

    def _build_from_tracks(self, album_key: str,
                           tracks: list) -> AlbumSummary:
        if not tracks:
            return AlbumSummary(album_key=album_key, source="local")

        first = tracks[0]
        count = len(tracks)
        dur = sum(getattr(t, 'duration', 0) or 0 for t in tracks)
        years = {getattr(t, 'year', 0) or 0 for t in tracks if getattr(t, 'year', 0)}
        genres = {getattr(t, 'genre', '') or '' for t in tracks if getattr(t, 'genre', '')}

        return AlbumSummary(
            album_key=album_key,
            title=first.album or "",
            artist=getattr(first, 'albumartist', '') or first.artist or "",
            year=str(max(years)) if years else "",
            track_count=count,
            duration=dur,
            genre=", ".join(sorted(genres)[:3]) if genres else "",
            cover_path=getattr(first, 'filepath', ''),
            source="local",
            track_list=list(tracks),
        )


def _dict_to_summary(data: dict) -> AlbumSummary | None:
    try:
        # Parse raw_json for extra fields if present
        raw = data.get("raw_json", "")
        extra = {}
        if raw:
            import json as _json
            try:
                extra = _json.loads(raw)
                if not isinstance(extra, dict):
                    extra = {}
            except _json.JSONDecodeError:
                pass

        # Merge: explicit columns take priority, raw_json fills gaps
        def _get(key, default=""):
            return data.get(key) or extra.get(key) or default

        return AlbumSummary(
            album_key=data.get("album_key", ""),
            title=data.get("title", data.get("album", "")),
            artist=data.get("artist", ""),
            year=str(data.get("year", "")),
            genre=_get("genre"),
            style=_get("style"),
            mood=_get("mood"),
            description=_get("description"),
            track_count=int(data.get("track_count", 0)),
            duration=float(data.get("duration", 0)),
            cover_path=_get("cover_path"),
            cover_url=_get("cover_url"),
            thumb_path=_get("thumb_path"),
            thumb_url=_get("thumb_url"),
            fanart_path=_get("fanart_path"),
            source=_get("source", "cache"),
            match_confidence=float(data.get("match_confidence", 0)),
            updated_at=str(data.get("updated_at", "")),
            dominant_color=_get("dominant_color"),
            track_list=data.get("track_list") or extra.get("track_list") or [],
            external_ids=data.get("external_ids") or extra.get("external_ids") or {},
        )
    except Exception:
        return None
