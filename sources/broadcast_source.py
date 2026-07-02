"""BroadcastSource — searchable source for broadcast (radio + podcasts)."""

from __future__ import annotations

from sources.base_source import MusicSource, TrackRef
from streaming.radio_manager import RadioManager
from streaming.podcast_manager import PodcastManager


class BroadcastSource(MusicSource):
    """Unified search source for radio stations and podcast episodes."""

    def __init__(self, radio_manager: RadioManager | None = None,
                 podcast_manager: PodcastManager | None = None):
        super().__init__()
        self._radio = radio_manager
        self._podcast = podcast_manager

    def list_tracks(self) -> list[TrackRef]:
        tracks: list[TrackRef] = []
        if self._radio:
            for st in self._radio.get_all():
                tracks.append(TrackRef(
                    uri=st.url, title=st.name, artist="Radio",
                    source_type="broadcast", source_label="Radio",
                ))
        return tracks

    def search(self, query: str) -> list[TrackRef]:
        q = query.lower()
        results: list[TrackRef] = []

        # Search radio stations
        if self._radio:
            for st in self._radio.get_all():
                if q in st.name.lower() or q in (st.url or "").lower() or q in (st.tags or "").lower():
                    results.append(TrackRef(
                        uri=st.url, title=st.name, artist="Radio",
                        source_type="broadcast", source_label="Radio",
                    ))

        # Search podcast episodes
        if self._podcast:
            shows = {s.id: s.title for s in self._podcast.get_shows()}
            for ep in self._podcast.get_recent_episodes(200):
                if q in ep.title.lower() or q in shows.get(ep.podcast_id, "").lower():
                    results.append(TrackRef(
                        uri=ep.local_path if ep.downloaded and ep.local_path else ep.audio_url,
                        title=ep.title,
                        artist=shows.get(ep.podcast_id, ""),
                        source_type="podcast",
                        source_label="Podcast",
                    ))

        return results
