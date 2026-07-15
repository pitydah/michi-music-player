"""Artist repository — holds artist groups state and provides lookup methods."""
from library.artist_grouping import ArtistGroup, build_artist_groups
from library.artist_insights import (
    ArtistInsight, ArtistQualitySummary, ArtistMetadataHealth,
    build_artist_insight,
)
from library.artist_aliases import find_artist_alias_candidates


class ArtistRepository:
    def __init__(self):
        self._groups: list[ArtistGroup] = []
        self._by_key: dict[str, ArtistGroup] = {}
        self._current_key: str | None = None
        self._all_items: list = []
        self._insights_by_key: dict[str, ArtistInsight] = {}
        self._insight_dirty = True

    def build(self, items: list):
        self._groups = build_artist_groups(items)
        self._by_key = {g.key: g for g in self._groups}
        self._all_items = items
        self._insight_dirty = True

    def invalidate_insights(self):
        self._insight_dirty = True

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
        """Apply external artist info to an ArtistGroup. Returns True if applied."""
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

    # ── Helper methods ──

    def current_group(self) -> ArtistGroup | None:
        """Return the currently selected artist group, or None."""
        if self._current_key:
            return self._by_key.get(self._current_key)
        return None

    def albums_for_artist(self, key: str) -> list:
        group = self.get_group(key)
        return group.albums if group else []

    def tracks_for_artist(self, key: str) -> list:
        group = self.get_group(key)
        return group.all_tracks if group else []

    def top_tracks_for_artist(self, key: str, limit: int = 10) -> list:
        from library.artist_insights import rank_top_tracks
        group = self.get_group(key)
        if not group:
            return []
        return rank_top_tracks(group, limit)

    def genres_for_artist(self, key: str) -> list[str]:
        group = self.get_group(key)
        return group.genres if group else []

    def years_for_artist(self, key: str) -> list[int]:
        group = self.get_group(key)
        return group.years if group else []

    # ── Insight methods ──

    def _ensure_insights(self):
        if not self._insight_dirty:
            return
        self._insights_by_key = {}
        for group in self._groups:
            self._insights_by_key[group.key] = build_artist_insight(
                group, self._all_items)
        self._insight_dirty = False

    def insight_for_artist(self, key: str) -> ArtistInsight | None:
        self._ensure_insights()
        return self._insights_by_key.get(key)

    def quality_summary_for_artist(self, key: str) -> ArtistQualitySummary | None:
        insight = self.insight_for_artist(key)
        return insight.quality if insight else None

    def metadata_health_for_artist(self, key: str) -> ArtistMetadataHealth | None:
        insight = self.insight_for_artist(key)
        return insight.health if insight else None

    def collaborations_for_artist(self, key: str) -> list:
        insight = self.insight_for_artist(key)
        return insight.collaborations if insight else []

    def alias_candidates_for_artist(self, key: str) -> list[tuple[str, str, float]]:
        candidates = find_artist_alias_candidates(self._groups)
        return [(k1, k2, s) for k1, k2, s in candidates if k1 == key or k2 == key]

    def artists_with_warnings(self) -> list[ArtistGroup]:
        self._ensure_insights()
        result = []
        for group in self._groups:
            insight = self._insights_by_key.get(group.key)
            if insight and insight.health.total_issues > 0:
                result.append(group)
        return result

    def artists_with_missing_info(self) -> list[ArtistGroup]:
        return [g for g in self._groups if not g.enrichment_status]

    def artists_with_external_info(self) -> list[ArtistGroup]:
        return [g for g in self._groups if g.enrichment_status == "loaded"]

    def artists_by_quality(self) -> list[ArtistGroup]:
        self._ensure_insights()
        sorted_groups = sorted(
            self._groups,
            key=lambda g: (
                -(self._insights_by_key.get(g.key).quality.lossless_ratio
                  if self._insights_by_key.get(g.key) else 0),
            ),
        )
        return sorted_groups
