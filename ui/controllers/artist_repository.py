"""Artist repository — holds artist groups state and provides lookup methods."""
from library.artist_grouping import ArtistGroup, build_artist_groups


class ArtistRepository:
    def __init__(self):
        self._groups: list[ArtistGroup] = []
        self._by_key: dict[str, ArtistGroup] = {}
        self._current_key: str | None = None

    def build(self, items: list):
        self._groups = build_artist_groups(items)
        self._by_key = {g.key: g for g in self._groups}

    @property
    def groups(self) -> list[ArtistGroup]:
        return self._groups

    @property
    def count(self) -> int:
        return len(self._groups)

    def get_group(self, key: str) -> ArtistGroup | None:
        return self._by_key.get(key)

    def filepaths(self, key: str) -> list[str]:
        """Return all filepaths for an artist, filtering to existing files."""
        import os
        group = self.get_group(key)
        if not group:
            return []
        return [t.filepath for t in group.all_tracks if os.path.isfile(t.filepath)]

    def apply_external_info(self, artist_key: str, info) -> bool:
        """Apply TheAudioDB info to an ArtistGroup. Returns True if applied."""
        group = self._by_key.get(artist_key)
        if not group or not info:
            return False

        group.external_id = getattr(info, "artist_id", "")
        group.mbid = getattr(info, "mbid", "")
        group.bio = getattr(info, "biography_preferred", "")
        group.genre = getattr(info, "genre", "")
        group.thumb_url = getattr(info, "thumb_url", "")
        group.banner_url = getattr(info, "banner_url", "")
        group.logo_url = getattr(info, "logo_url", "")
        group.fanart_urls = getattr(info, "fanart_urls", []) or []
        group.country = getattr(info, "country", "")
        group.formed_year = getattr(info, "formed_year", "")
        group.style = getattr(info, "style", "")
        group.mood = getattr(info, "mood", "")
        group.website = getattr(info, "website", "")
        group.last_enriched_at = (
            getattr(info, "last_updated", "")
            or getattr(info, "updated_at", ""))
        group.enrichment_status = "loaded"

        if hasattr(info, "thumb_path"):
            group.thumb_path = getattr(info, "thumb_path", "")
        if hasattr(info, "banner_path"):
            group.banner_path = getattr(info, "banner_path", "")
        if hasattr(info, "logo_path"):
            group.logo_path = getattr(info, "logo_path", "")
        if hasattr(info, "fanart_paths"):
            group.fanart_paths = getattr(info, "fanart_paths", []) or []

        return True

    def mark_enrichment_loading(self, artist_key: str):
        group = self._by_key.get(artist_key)
        if group:
            group.enrichment_status = "loading"

    def mark_enrichment_error(self, artist_key: str, error: str = ""):
        group = self._by_key.get(artist_key)
        if group:
            group.enrichment_status = "error"

    def mark_enrichment_not_found(self, artist_key: str):
        group = self._by_key.get(artist_key)
        if group:
            group.enrichment_status = "not_found"

    @property
    def current_key(self) -> str | None:
        return self._current_key

    @current_key.setter
    def current_key(self, key: str | None):
        self._current_key = key

    def clear_current(self):
        self._current_key = None
