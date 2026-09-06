"""G0 — Queue firewall: Golden Path direct-play contract (V4 §6/§7).

Adversarial L3 seals over the REAL bridge chain:
  LibraryBridge → LibraryPlaybackCoordinator → PlaybackSessionService,
with a live QueueService — proving direct playback NEVER mutates the
Queue and context types stay truthful.

GP-A  Queue=[]     + Songs click  → X plays;  Queue stays []
GP-B  Queue=[A..]  + Songs click  → X plays;  Queue stays [A..]
GP-C  Queue=[A..]  + Album click  → ALBUM context; Queue unchanged
GP-E  Queue=[A..]  + Search click → SINGLE context; Queue unchanged
GP-F  Queue click  → QUEUE context (live sequence)       [session seal exists]
GP-G  explicit add → Queue mutates; current playback intact [session seal exists]
"""

from tests.test_library_metadata import FakeExtractor, FakeScanner
from tests.test_library_views import (
    _album_genre_factory,
    _bridge_with_coordinator,
    _make_library,
)


def _scan_two(tmp_path):
    a1 = tmp_path / "a1.mp3"
    a2 = tmp_path / "a2.mp3"
    for p in (a1, a2):
        p.write_bytes(b"x")
    library, queue, session, playback, audio = _make_library(
        FakeScanner([a1, a2]), FakeExtractor(factory=_album_genre_factory())
    )
    library.scan(str(tmp_path))
    bridge = _bridge_with_coordinator(library, session)
    return library, queue, session, playback, audio, bridge


def _track_id(library, path):
    ref = next(t for t in library.state.tracks if t.file_path == path)
    return ref.track_id or f"legacy-path::{ref.file_path}"


class TestGpADirectSongsPlay:
    def test_gp_a_queue_empty_songs_click_plays_single(self, tmp_path):
        library, queue, session, _, audio, bridge = _scan_two(tmp_path)
        a1 = tmp_path / "a1.mp3"
        bridge.activate_track_by_id(_track_id(library, a1))
        assert queue.state.count == 0, "GP-A: Queue stays empty"
        audio.trigger_media_accepted(a1)
        assert session.state.context_type.name == "SINGLE"
        assert session.state.current_entry.file_path == a1

    def test_gp_b_queue_populated_songs_click_never_touches_queue(self, tmp_path):
        library, queue, session, _, audio, bridge = _scan_two(tmp_path)
        a1 = tmp_path / "a1.mp3"
        a2 = tmp_path / "a2.mp3"
        # Queue pre-populated [a1, a2] with explicit entries.
        queue.add(a1)
        queue.add(a2)
        assert queue.state.count == 2
        queue_ids = [t.entry_id for t in queue.state.tracks]

        bridge.activate_track_by_id(_track_id(library, a1))
        assert queue.state.count == 2, "GP-B: Queue untouched"
        assert [t.entry_id for t in queue.state.tracks] == queue_ids
        audio.trigger_media_accepted(a1)
        assert session.state.context_type.name == "SINGLE"


class TestGpCAlbumClick:
    def test_gp_c_album_track_click_album_context_queue_unchanged(self, tmp_path):
        library, queue, session, _, audio, bridge = _scan_two(tmp_path)
        a1 = tmp_path / "a1.mp3"
        a2 = tmp_path / "a2.mp3"
        queue.add(a1)
        queue.add(a2)
        assert queue.state.count == 2
        queue_ids = [t.entry_id for t in queue.state.tracks]

        album = library.state.albums[0]
        bridge.select_album(album.key)
        ref = next(t for t in library.state.tracks if t.file_path == a1)
        bridge.activate_album_track_by_id(
            ref.track_id or f"legacy-path::{ref.file_path}"
        )
        assert queue.state.count == 2, "GP-C: Queue unchanged"
        assert [t.entry_id for t in queue.state.tracks] == queue_ids
        audio.trigger_media_accepted(a1)
        assert session.state.context_type.name == "ALBUM", (
            "album click → ALBUM context (never SINGLE, never Queue)"
        )
        assert session.state.current_entry.file_path == a1


class TestGpESearchOrigin:
    def test_gp_e_search_track_click_is_single_queue_unchanged(self, tmp_path):
        """Search results activate by TrackId through the SAME single
        intent seam — direct playback from Search never mutates Queue."""
        library, queue, session, _, audio, bridge = _scan_two(tmp_path)
        a1 = tmp_path / "a1.mp3"
        a2 = tmp_path / "a2.mp3"
        queue.add(a1)
        queue.add(a2)
        queue_ids = [t.entry_id for t in queue.state.tracks]

        # Search-origin activation: identical canonical seam (TrackId).
        bridge.activate_track_by_id(_track_id(library, a1))
        assert queue.state.count == 2, "GP-E: Queue unchanged"
        assert [t.entry_id for t in queue.state.tracks] == queue_ids
        audio.trigger_media_accepted(a1)
        assert session.state.context_type.name == "SINGLE"


class TestGpFGGpReferences:
    def test_gp_f_gp_g_semantics_sealed_by_session_suite(self, tmp_path):
        """GP-F (queue click → QUEUE live context) and GP-G (explicit add
        mutates Queue without touching playback) are already sealed by
        test_playback_session_service (Q05, Q08, Q02-04, single never
        mutates). This test documents the mapping so the G0 baseline has
        no unclassified gap."""
        # GP-F: session.play_queue_index → QUEUE context (Q05).
        # GP-G: explicit queue add leaves the accepted playback untouched.
        library, queue, session, _, audio, bridge = _scan_two(tmp_path)
        a1 = tmp_path / "a1.mp3"
        a2 = tmp_path / "a2.mp3"
        # GP-G: an accepted single keeps playing; explicit adds only stack.
        bridge.activate_track_by_id(_track_id(library, a1))
        audio.trigger_media_accepted(a1)
        assert session.state.context_type.name == "SINGLE"
        queue.add(a2)
        assert session.state.context_type.name == "SINGLE", (
            "GP-G: explicit add never changes the active context"
        )
        assert session.state.current_entry.file_path == a1
        assert queue.state.count == 1
