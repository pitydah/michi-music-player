"""Artist repository — holds artist groups state and provides lookup methods."""
from library.artist_grouping import ArtistGroup, build_artist_groups


class ArtistRepository:
    def __init__(self):
        self._groups: list[ArtistGroup] = []
        self._current_key: str | None = None

    def build(self, items: list):
        self._groups = build_artist_groups(items)

    @property
    def groups(self) -> list[ArtistGroup]:
        return self._groups

    @property
    def count(self) -> int:
        return len(self._groups)

    def get_group(self, key: str) -> ArtistGroup | None:
        return next((g for g in self._groups if g.key == key), None)

    def filepaths(self, key: str) -> list[str]:
        """Return all filepaths for an artist, filtering to existing files."""
        import os
        group = self.get_group(key)
        if not group:
            return []
        return [t.filepath for t in group.all_tracks if os.path.isfile(t.filepath)]

    @property
    def current_key(self) -> str | None:
        return self._current_key

    @current_key.setter
    def current_key(self, key: str | None):
        self._current_key = key

    def clear_current(self):
        self._current_key = None
