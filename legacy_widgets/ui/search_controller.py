"""SearchController — unifies search across all MusicSources."""

from PySide6.QtCore import QObject, Signal
from sources.base_source import TrackRef, MusicSource


class SearchController(QObject):
    results_ready = Signal(list)  # list[TrackRef]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sources: dict[str, MusicSource] = {}
        self._active_source_key: str = ""

    def register(self, key: str, source: MusicSource):
        self._sources[key] = source

    def set_active(self, key: str):
        self._active_source_key = key

    def active_source(self) -> MusicSource | None:
        return self._sources.get(self._active_source_key)

    def search(self, query: str):
        """Search all registered sources and merge results."""
        if not query.strip():
            source = self.active_source()
            if source:
                self.results_ready.emit(source.list_tracks())
            return

        all_results: list[TrackRef] = []
        # Active source first, then others
        active = self.active_source()
        if active:
            all_results.extend(active.search(query))

        for key, source in self._sources.items():
            if key == self._active_source_key:
                continue
            all_results.extend(source.search(query))

        self.results_ready.emit(all_results)

    def list_all(self) -> list[TrackRef]:
        source = self.active_source()
        return source.list_tracks() if source else []
