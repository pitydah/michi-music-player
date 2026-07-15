"""Genre Repository — holds genre groups state and provides lookup methods."""
from metadata.genre_grouping import GenreGroup, build_genre_groups


class GenreRepository:
    def __init__(self):
        self._groups: list[GenreGroup] = []
        self._by_key: dict[str, GenreGroup] = {}
        self._current_key: str | None = None
        self._all_items: list = []

    def build(self, items: list):
        self._all_items = items
        self._groups = build_genre_groups(items)
        self._by_key = {g.key: g for g in self._groups}

    @property
    def groups(self) -> list[GenreGroup]:
        return self._groups

    @property
    def count(self) -> int:
        return len(self._groups)

    def get_group(self, key: str) -> GenreGroup | None:
        return self._by_key.get(key)

    def search(self, query: str) -> list[GenreGroup]:
        q = query.lower()
        return [g for g in self._groups
                if q in g.name.lower() or q in g.family.lower()]

    def filter_by_family(self, family: str) -> list[GenreGroup]:
        return [g for g in self._groups if g.family == family]

    def tracks_for_genre(self, key: str) -> list:
        g = self.get_group(key)
        return g.tracks if g else []

    def filepaths_for_genre(self, key: str) -> list[str]:
        import os
        g = self.get_group(key)
        if not g:
            return []
        return [t.filepath for t in g.tracks if os.path.isfile(t.filepath)]

    def artists_for_genre(self, key: str) -> list[str]:
        g = self.get_group(key)
        return sorted(g.artists) if g else []

    def albums_for_genre(self, key: str) -> list[str]:
        g = self.get_group(key)
        return sorted(g.albums) if g else []

    @property
    def families(self) -> list[str]:
        seen = set()
        for g in self._groups:
            if g.family and g.key != "untagged":
                seen.add(g.family)
        return sorted(seen)

    @property
    def untagged_tracks(self) -> list:
        g = self.get_group("untagged")
        return g.tracks if g else []

    @property
    def untagged_count(self) -> int:
        g = self.get_group("untagged")
        return g.track_count if g else 0

    @property
    def total_stats(self) -> dict:
        tagged = sum(g.track_count for g in self._groups if g.key != "untagged")
        lossless = sum(g.lossless_count for g in self._groups if g.key != "untagged")
        total = sum(g.track_count for g in self._groups)
        return {
            "genre_count": len([g for g in self._groups if g.key != "untagged"]),
            "tagged_tracks": tagged,
            "untagged_tracks": self.untagged_count,
            "total_tracks": total,
            "artist_count": len(set().union(*[g.artists for g in self._groups])),
            "lossless_pct": int(lossless / tagged * 100) if tagged else 0,
        }

    @property
    def current_key(self) -> str | None:
        return self._current_key

    @current_key.setter
    def current_key(self, key: str | None):
        self._current_key = key

    def clear_current(self):
        self._current_key = None
