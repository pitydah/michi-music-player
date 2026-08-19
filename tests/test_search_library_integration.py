"""M7.5 + M7.6 — Unified library search integration — Phase-1 RED tests.

When a query is active, the unified SearchProjection filters Songs, Albums,
Artists, Genres, Composers, Favorites, History and Recently Added through
the SAME matched track/album/entity sets; clearing restores the canonical
collections EXACTLY. Selection stays canonical-safe (filtering is never
deletion; only real structural removal clears it). Active search REBUILDS
after rescan/metadata changes (no stale results). The bridge exposes raw
query, counts, clear and the no-results state — no business logic in
bridge/QML.
"""

from michi.application.library_service import LibraryService
from michi.application.playback_service import PlaybackService
from michi.application.queue_service import QueueService
from michi.domain.library import TrackMetadata
from michi.presentation.library_bridge import LibraryBridge
from tests.conftest import FakeAudioPort
from tests.test_library_metadata import FakeExtractor, FakeScanner

GOLDEN = {
    "a.mp3": dict(
        title="Blue",
        artist="Joni Mitchell",
        album="Blue",
        album_artist="Joni Mitchell",
        genre="Folk",
        composer="Joni Mitchell",
    ),
    "b.mp3": dict(
        title="So What",
        artist="Miles Davis",
        album="Kind of Blue",
        album_artist="Miles Davis",
        genre="Jazz",
        composer="Miles Davis",
    ),
    "c.mp3": dict(
        title="Time",
        artist="Hans Zimmer",
        album="Inception",
        album_artist="Hans Zimmer",
        genre="Soundtrack",
        composer="Hans Zimmer",
    ),
    "d.mp3": dict(
        title="Cornfield Chase",
        artist="Hans Zimmer",
        album="Interstellar",
        album_artist="Hans Zimmer",
        genre="Soundtrack",
        composer="Hans Zimmer",
    ),
}


def _factory(path):
    meta = GOLDEN.get(path.name, {})
    return TrackMetadata(
        title=meta.get("title", ""),
        artist=meta.get("artist", ""),
        album=meta.get("album", ""),
        album_artist=meta.get("album_artist", ""),
        genre=meta.get("genre", ""),
        composer=meta.get("composer", ""),
        duration_ms=1000,
    )


def _make(tmp_path, names):
    music = tmp_path / "music"
    music.mkdir(exist_ok=True)
    paths = []
    for name in names:
        p = music / name
        p.write_bytes(b"x")
        paths.append(p)
    audio = FakeAudioPort()
    playback = PlaybackService(audio)
    queue = QueueService(playback)
    library = LibraryService(FakeScanner(paths), queue, FakeExtractor(factory=_factory))
    library.scan(str(music))
    return library, queue, audio, music, paths


def _bridge(library):
    return LibraryBridge(library)


class TestUnifiedFiltering:
    def test_active_search_filters_song_projection(self, tmp_path):
        library, *_ = _make(tmp_path, list(GOLDEN))
        library.search("miles")
        assert [t.display_name for t in library.state.visible_tracks] == ["So What"]

    def test_active_search_filters_album_projection(self, tmp_path):
        library, *_ = _make(tmp_path, list(GOLDEN))
        bridge = _bridge(library)
        assert len(bridge.property("albums")) == 4
        library.search("zimmer")
        rows = bridge.property("albums")
        assert {r["title"] for r in rows} == {"Inception", "Interstellar"}
        bridge.dispose()

    def test_active_search_filters_artist_projection(self, tmp_path):
        library, *_ = _make(tmp_path, list(GOLDEN))
        bridge = _bridge(library)
        library.search("joni")
        assert [r["name"] for r in bridge.property("artists")] == ["Joni Mitchell"]
        bridge.dispose()

    def test_active_search_filters_genre_projection(self, tmp_path):
        library, *_ = _make(tmp_path, list(GOLDEN))
        bridge = _bridge(library)
        library.search("jazz")
        assert [r["name"] for r in bridge.property("genres")] == ["Jazz"]
        bridge.dispose()

    def test_clear_search_restores_canonical_collections(self, tmp_path):
        library, *_ = _make(tmp_path, list(GOLDEN))
        bridge = _bridge(library)
        canonical_tracks = list(library.state.tracks)
        canonical_albums = library.state.albums
        canonical_artists = library.state.artists
        canonical_genres = library.state.genres
        library.search("miles")
        assert library.state.search_projection is not None
        library.clear_search()
        assert library.state.query == ""
        assert library.state.search_projection is None
        assert library.state.tracks == canonical_tracks
        assert library.state.albums == canonical_albums
        assert library.state.artists == canonical_artists
        assert library.state.genres == canonical_genres
        assert len(bridge.property("albums")) == 4  # canonical passthrough
        bridge.dispose()

    def test_search_preserves_raw_query(self, tmp_path):
        library, *_ = _make(tmp_path, list(GOLDEN))
        library.search("  Miles Davis  ")
        assert library.state.query == "  Miles Davis  "  # presentation form kept
        assert len(library.state.visible_tracks) == 1
        library.clear_search()


class TestReferenceFiltering:
    def test_search_filters_favorite_rows_by_matched_track_ids(self, tmp_path):
        library, queue, audio, music, paths = _make(tmp_path, list(GOLDEN))
        bridge = _bridge(library)
        library.toggle_favorite(paths[1])  # Miles track
        library.toggle_favorite(paths[2])  # Zimmer track
        assert len(bridge.property("favoriteRows")) == 2
        library.search("miles")
        rows = bridge.property("favoriteRows")
        assert [r["path"] for r in rows] == [str(paths[1])]
        bridge.dispose()

    def test_search_filters_history_rows_by_matched_track_ids(self, tmp_path):
        library, queue, audio, music, paths = _make(tmp_path, list(GOLDEN))
        bridge = _bridge(library)
        library.activate(0)  # Joni track
        audio.trigger_media_accepted(paths[0])  # commit -> history entry
        assert library.state.history_paths == (str(paths[0]),)
        library.search("zimmer")
        rows = bridge.property("historyRows")
        assert rows == []  # no Zimmer track in history
        library.clear_search()
        assert len(bridge.property("historyRows")) == 1
        bridge.dispose()

    def test_search_filters_recent_rows_by_matched_track_ids(self, tmp_path):
        library, queue, audio, music, paths = _make(tmp_path, list(GOLDEN))
        bridge = _bridge(library)
        assert len(bridge.property("recentlyAddedRows")) == 4
        library.search("joni")
        rows = bridge.property("recentlyAddedRows")
        assert [r["path"] for r in rows] == [str(paths[0])]
        bridge.dispose()


class TestSelectionSafety:
    def test_filtered_out_album_is_not_deleted(self, tmp_path):
        library, *_ = _make(tmp_path, list(GOLDEN))
        bridge = _bridge(library)
        kind_of_blue = next(
            a for a in library.state.albums if a.title == "Kind of Blue"
        )
        bridge.select_album(kind_of_blue.key)
        library.search("zimmer")  # hides Kind of Blue
        assert kind_of_blue in library.state.albums  # canonical, not deleted
        assert bridge.property("selectedAlbumKey") == kind_of_blue.key
        bridge.dispose()

    def test_clear_search_restores_selected_album_visibility(self, tmp_path):
        library, *_ = _make(tmp_path, list(GOLDEN))
        bridge = _bridge(library)
        kind_of_blue = next(
            a for a in library.state.albums if a.title == "Kind of Blue"
        )
        bridge.select_album(kind_of_blue.key)
        library.search("zimmer")
        assert kind_of_blue.key not in {r["key"] for r in bridge.property("albums")}
        library.clear_search()
        assert kind_of_blue.key in {r["key"] for r in bridge.property("albums")}
        assert bridge.property("selectedAlbumKey") == kind_of_blue.key
        bridge.dispose()

    def test_real_album_removal_clears_selection(self, tmp_path):
        library, *_ = _make(tmp_path, list(GOLDEN))
        bridge = _bridge(library)
        kind_of_blue = next(
            a for a in library.state.albums if a.title == "Kind of Blue"
        )
        bridge.select_album(kind_of_blue.key)
        # Structural removal: the Miles track disappears -> album gone.
        library._state.tracks = [
            t for t in library.state.tracks if t.artist != "Miles Davis"
        ]
        library._rebuild_derived_library_state()
        library._notify()  # the bridge observes through the notify stream
        assert bridge.property("selectedAlbumKey") == ""  # cleared by real removal
        bridge.dispose()


class TestActiveSearchLifecycle:
    def test_active_search_rebuilds_after_rescan(self, tmp_path):
        library, queue, audio, music, paths = _make(tmp_path, list(GOLDEN))
        library.search("zimmer")
        # Canonical tie-break: equal scores -> title order.
        assert [t.display_name for t in library.state.visible_tracks] == [
            "Cornfield Chase",
            "Time",
        ]
        # Rescan removes the Zimmer tracks and adds a new Miles track.
        new_path = music / "e.mp3"
        new_path.write_bytes(b"x")
        library._scanner.paths = [paths[1], new_path]
        library.scan(str(music))
        # Active search followed the NEW canonical library: no stale Zimmer.
        assert library.state.query == "zimmer"
        assert [t.display_name for t in library.state.visible_tracks] == []

    def test_active_search_metadata_modification_reflected(self, tmp_path):
        library, queue, audio, music, paths = _make(tmp_path, list(GOLDEN))
        library.search("miles")
        assert [t.display_name for t in library.state.visible_tracks] == ["So What"]
        # The Joni track's metadata is corrected to Miles and rescanned.
        library._scanner.paths = [paths[0], paths[1]]
        library._metadata_extractor.factory = lambda p: (
            TrackMetadata(
                title="Blue",
                artist="Miles Davis",
                album="Blue",
                album_artist="Miles Davis",
                genre="Jazz",
                composer="Miles Davis",
                duration_ms=1000,
            )
            if p == paths[0]
            else _factory(p)
        )
        library.scan(str(music))
        assert {t.display_name for t in library.state.visible_tracks} == {
            "Blue",
            "So What",
        }


class TestBridgeSearchSurface:
    def test_bridge_preserves_raw_search_query(self, tmp_path):
        library, *_ = _make(tmp_path, list(GOLDEN))
        bridge = _bridge(library)
        bridge.search("  Miles Davis  ")
        assert bridge.property("searchQuery") == "  Miles Davis  "
        bridge.dispose()

    def test_bridge_exposes_search_counts(self, tmp_path):
        library, *_ = _make(tmp_path, list(GOLDEN))
        bridge = _bridge(library)
        library.search("zimmer")
        assert bridge.property("searchActive") is True
        assert bridge.property("searchTrackCount") == 2
        assert bridge.property("searchAlbumCount") == 2
        assert bridge.property("searchArtistCount") == 1
        assert bridge.property("searchGenreCount") == 0  # no genre named Zimmer
        assert bridge.property("searchComposerCount") == 1
        assert bridge.property("searchTotalCount") == 6
        bridge.dispose()

    def test_bridge_clear_search(self, tmp_path):
        library, *_ = _make(tmp_path, list(GOLDEN))
        bridge = _bridge(library)
        library.search("miles")
        assert bridge.property("searchActive") is True
        bridge.clear_search()
        assert bridge.property("searchActive") is False
        assert bridge.property("searchQuery") == ""
        assert len(bridge.property("albums")) == 4
        bridge.dispose()

    def test_search_no_results_state(self, tmp_path):
        library, *_ = _make(tmp_path, list(GOLDEN))
        bridge = _bridge(library)
        library.search("zzz")
        assert bridge.property("searchActive") is True
        assert bridge.property("searchTotalCount") == 0
        assert bridge.property("searchTrackCount") == 0
        bridge.dispose()
