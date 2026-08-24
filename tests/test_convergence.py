"""Tests for convergence patch 3 (M4-R1 adapted).

EndOfMedia/repeat navigation authority moved from QueueService to
PlaybackSessionService; PlaybackCoordinator is position/duration
projection only; LibraryService no longer owns Queue.
"""

from pathlib import Path

import pytest

from michi.application.coordinator import PlaybackCoordinator
from michi.application.library_service import LibraryService
from michi.application.playback_service import PlaybackService
from michi.application.playback_session_service import PlaybackSessionService
from michi.application.queue_service import QueueService
from michi.domain.playback import PlaybackStatus
from michi.domain.playback_session import RepeatMode
from michi.presentation.playback_bridge import PlaybackBridge


def _graph(fake_audio, seed: int = 42):
    import random

    svc = PlaybackService(fake_audio)
    q = QueueService()
    session = PlaybackSessionService(svc, q, rng=random.Random(seed))
    session.start()  # M4-R1 final seal: explicit lifecycle arms subscriptions
    return svc, q, session


class TestSeekBridge:
    """Real seek test: 60 seconds through the bridge → 60000 ms at AudioPort."""

    def test_seek_seconds_converts_to_ms(self, fake_audio):
        svc = PlaybackService(fake_audio)
        bridge = PlaybackBridge(svc)
        bridge.seek_seconds(60)
        assert fake_audio.position() == 60000

    def test_seek_zero(self, fake_audio):
        svc = PlaybackService(fake_audio)
        bridge = PlaybackBridge(svc)
        bridge.seek_seconds(0)
        assert fake_audio.position() == 0


class TestEndOfMedia:
    """EOM navigation is owned by PlaybackSessionService (M4-R1)."""

    def test_with_next(self, fake_audio):
        svc, q, session = _graph(fake_audio)
        q.add(Path("/tmp/a.mp3"))
        q.add(Path("/tmp/b.mp3"))
        session.play_queue_index(0)
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))
        fake_audio.trigger_end_of_media()
        assert session.state.current_index == 0  # B pending, not committed
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))
        assert session.state.current_index == 1

    def test_auto_advance_failure_preserves_index(self, fake_audio, monkeypatch):
        svc, q, session = _graph(fake_audio)
        q.add(Path("/tmp/a.mp3"))
        q.add(Path("/tmp/b.mp3"))
        session.play_queue_index(0)
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))

        def failing_load(p):
            raise RuntimeError("load failed")

        monkeypatch.setattr(fake_audio, "load", failing_load)

        with pytest.raises(RuntimeError):
            fake_audio.trigger_end_of_media()

        assert session.state.current_index == 0

    def test_auto_advance_rejection_preserves_queue(self, fake_audio):
        svc, q, session = _graph(fake_audio)
        q.add(Path("/tmp/a.mp3"))
        q.add(Path("/tmp/b.mp3"))
        session.play_queue_index(0)
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))
        fake_audio.trigger_end_of_media()
        fake_audio.trigger_media_rejected(Path("/tmp/b.mp3"), "cannot decode")
        assert session.state.current_index == 0
        assert svc.state.file_path == Path("/tmp/a.mp3")
        assert svc.state.status == PlaybackStatus.STOPPED
        assert svc.state.error_message == "cannot decode"

    def test_auto_advance_acceptance_advances_exactly_once(self, fake_audio):
        svc, q, session = _graph(fake_audio)
        q.add(Path("/tmp/a.mp3"))
        q.add(Path("/tmp/b.mp3"))
        q.add(Path("/tmp/c.mp3"))
        session.play_queue_index(0)
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))
        fake_audio.trigger_end_of_media()
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))
        assert session.state.current_index == 1
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))  # duplicate
        assert session.state.current_index == 1  # no double advance

    def test_at_end(self, fake_audio):
        svc, q, session = _graph(fake_audio)
        q.add(Path("/tmp/a.mp3"))
        session.play_queue_index(0)
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))
        fake_audio.trigger_end_of_media()
        assert svc.state.status == PlaybackStatus.STOPPED
        assert svc.state.position_ms == 0


class TestRepeatWithCoordinator:
    """M4 integration: EOM drives exactly ONE repeat-aware auto-advance via
    PlaybackSessionService — the coordinator must not double-load, replay-
    stop, or cancel wraps."""

    def test_coordinator_repeat_none_single_advance(self, fake_audio, monkeypatch):
        svc, q, session = _graph(fake_audio)
        q.add(Path("/tmp/a.mp3"))
        q.add(Path("/tmp/b.mp3"))
        q.add(Path("/tmp/c.mp3"))
        loads = []
        real_load = fake_audio.load

        def spy_load(p):
            loads.append(p)
            real_load(p)

        monkeypatch.setattr(fake_audio, "load", spy_load)
        session.play_queue_index(0)
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))
        assert session.state.current_index == 0
        loads.clear()

        fake_audio.trigger_end_of_media()  # NONE → exactly one advance to B
        assert loads == [Path("/tmp/b.mp3")]  # no double-load
        assert fake_audio.loaded == Path("/tmp/b.mp3")
        assert session.state.current_index == 0  # pending, not committed
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))
        assert session.state.current_index == 1

    def test_coordinator_repeat_one_replays_once(self, fake_audio, monkeypatch):
        svc, q, session = _graph(fake_audio)
        q.add(Path("/tmp/a.mp3"))
        q.add(Path("/tmp/b.mp3"))
        q.add(Path("/tmp/c.mp3"))
        loads = []
        real_load = fake_audio.load

        def spy_load(p):
            loads.append(p)
            real_load(p)

        monkeypatch.setattr(fake_audio, "load", spy_load)
        session.set_repeat_mode(RepeatMode.ONE)
        session.play_queue_index(1)
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))
        assert session.state.current_index == 1
        loads.clear()

        fake_audio.trigger_end_of_media()  # ONE → replay B exactly once
        assert loads == [Path("/tmp/b.mp3")]
        assert fake_audio.loaded == Path("/tmp/b.mp3")
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))
        assert session.state.current_index == 1

    def test_coordinator_repeat_all_wraps_at_last(self, fake_audio, monkeypatch):
        svc, q, session = _graph(fake_audio)
        q.add(Path("/tmp/a.mp3"))
        q.add(Path("/tmp/b.mp3"))
        q.add(Path("/tmp/c.mp3"))
        loads = []
        real_load = fake_audio.load

        def spy_load(p):
            loads.append(p)
            real_load(p)

        monkeypatch.setattr(fake_audio, "load", spy_load)
        session.set_repeat_mode(RepeatMode.ALL)
        session.play_queue_index(2)
        fake_audio.trigger_media_accepted(Path("/tmp/c.mp3"))
        assert session.state.current_index == 2
        loads.clear()

        fake_audio.trigger_end_of_media()  # ALL at last → wrap to index 0
        assert loads == [Path("/tmp/a.mp3")]  # wrap, not stop() cancelling it
        assert fake_audio.loaded == Path("/tmp/a.mp3")
        assert fake_audio.state == "playing"  # must not stop()
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))
        assert session.state.current_index == 0

    def test_coordinator_keeps_position_and_duration(self, fake_audio):
        svc, q, session = _graph(fake_audio)
        coord = PlaybackCoordinator(fake_audio, svc)
        coord.start()
        fake_audio.trigger_position(5000)
        fake_audio.trigger_duration(200000)
        assert svc.state.position_ms == 5000
        assert svc.state.duration_ms == 200000


class TestSubscriptions:
    def test_subscribe_unsubscribe_eom(self, fake_audio):
        calls = []

        def cb():
            calls.append(1)

        fake_audio.subscribe_end_of_media(cb)
        fake_audio.trigger_end_of_media()
        assert len(calls) == 1
        fake_audio.unsubscribe_end_of_media(cb)
        fake_audio.trigger_end_of_media()
        assert len(calls) == 1

    def test_duplicate_subscribe_safe(self, fake_audio):
        calls = []

        def cb():
            calls.append(1)

        fake_audio.subscribe_end_of_media(cb)
        fake_audio.subscribe_end_of_media(cb)  # duplicate
        fake_audio.trigger_end_of_media()
        assert len(calls) == 1  # not doubled

    def test_double_unsubscribe_safe(self, fake_audio):
        def cb():
            pass

        fake_audio.subscribe_end_of_media(cb)
        fake_audio.unsubscribe_end_of_media(cb)
        fake_audio.unsubscribe_end_of_media(cb)  # safe

    def test_multiple_subscribers_independent(self, fake_audio):
        a, b = [], []

        def ca():
            a.append(1)

        def cb():
            b.append(1)

        fake_audio.subscribe_end_of_media(ca)
        fake_audio.subscribe_end_of_media(cb)
        fake_audio.trigger_end_of_media()
        assert len(a) == 1 and len(b) == 1
        fake_audio.unsubscribe_end_of_media(ca)
        fake_audio.trigger_end_of_media()
        assert len(a) == 1  # unsubscribed
        assert len(b) == 2  # still active

    def test_position_events(self, fake_audio):
        calls = []

        def cb(p):
            calls.append(p)

        fake_audio.subscribe_position_changed(cb)
        fake_audio.trigger_position(5000)
        assert calls == [5000]

    def test_duration_events(self, fake_audio):
        calls = []

        def cb(d):
            calls.append(d)

        fake_audio.subscribe_duration_changed(cb)
        fake_audio.trigger_duration(240000)
        assert calls == [240000]

    def test_media_accepted_events(self, fake_audio):
        calls = []

        def cb(p):
            calls.append(p)

        fake_audio.subscribe_media_accepted(cb)
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))
        assert calls == [Path("/tmp/a.mp3")]

    def test_media_rejected_events(self, fake_audio):
        calls = []

        def cb(p, m):
            calls.append((p, m))

        fake_audio.subscribe_media_rejected(cb)
        fake_audio.trigger_media_rejected(Path("/tmp/a.mp3"), "decode failed")
        assert calls == [(Path("/tmp/a.mp3"), "decode failed")]


class TestCoordinatorIdempotent:
    def test_double_start_safe(self, fake_audio):
        svc = PlaybackService(fake_audio)
        c = PlaybackCoordinator(fake_audio, svc)
        c.start()
        c.start()  # idempotent
        assert c._started

    def test_double_stop_safe(self, fake_audio):
        svc = PlaybackService(fake_audio)
        c = PlaybackCoordinator(fake_audio, svc)
        c.start()
        c.stop()
        c.stop()  # idempotent


class TestServiceNotifications:
    def test_queue_notify_on_add(self, queue_service):
        calls = []

        def cb():
            calls.append(1)

        queue_service.subscribe_changed(cb)
        queue_service.add(Path("/tmp/a.mp3"))
        assert len(calls) == 1

    def test_queue_notify_not_from_library_playback(self, fake_audio):
        """M4-R1: library playback intents must NOT mutate the Queue."""
        svc, q, session = _graph(fake_audio)

        class FakeScanner:
            def scan(self, root):
                return [root / "a.mp3"]

            def validate_file(self, path):
                return None

        lib = LibraryService(FakeScanner())
        lib.scan("/tmp")

        calls = []

        def cb():
            calls.append(1)

        q.subscribe_changed(cb)
        lib.record_history(Path("/tmp/a.mp3"))
        assert calls == []  # library does not touch Queue
        assert q.state.count == 0

    def test_playback_notify_on_play(self, fake_audio):
        svc = PlaybackService(fake_audio)
        calls = []

        def cb():
            calls.append(1)

        svc.subscribe_changed(cb)
        svc.load_and_play(Path("/tmp/a.mp3"))
        assert len(calls) == 1

    def test_playback_notify_on_error(self, fake_audio):
        svc = PlaybackService(fake_audio)
        calls = []

        def cb():
            calls.append(1)

        svc.subscribe_changed(cb)
        svc.report_error("oops")
        assert len(calls) == 1
        assert svc.state.error_message == "oops"

    def test_library_notify_on_scan(self, fake_audio):
        class FakeScanner:
            def scan(self, root):
                return [root / "a.mp3"]

            def validate_file(self, path):
                return None

        lib = LibraryService(FakeScanner())
        calls = []

        def cb():
            calls.append(1)

        lib.subscribe_changed(cb)
        lib.scan("/tmp")
        assert len(calls) == 1


class TestLibraryService:
    def test_scan_and_search(self, fake_audio):
        from michi.infrastructure.filesystem_scanner import FilesystemLibraryScanner

        (tmp := Path("/tmp/michi_test_lib"))
        tmp.mkdir(exist_ok=True)
        (tmp / "Depeche Mode - a.mp3").write_text("")
        (tmp / "Toto - b.mp3").write_text("")

        lib = LibraryService(FilesystemLibraryScanner())
        lib.scan(str(tmp))
        assert len(lib.state.visible_tracks) == 2
        lib.search("depeche")
        assert len(lib.state.visible_tracks) == 1

    def test_activate_filtered_via_session_single(self, fake_audio):
        (tmp := Path("/tmp/michi_test_act"))
        tmp.mkdir(exist_ok=True)
        (tmp / "a.mp3").write_text("")
        (tmp / "b.mp3").write_text("")
        (tmp / "c.mp3").write_text("")

        from michi.infrastructure.filesystem_scanner import FilesystemLibraryScanner

        lib = LibraryService(FilesystemLibraryScanner())
        lib.scan(str(tmp))
        lib.search("b")
        assert len(lib.state.visible_tracks) == 1
        # generic track click → SINGLE via the coordinator (no Queue)
        from michi.application.library_playback_coordinator import (
            LibraryPlaybackCoordinator,
        )

        svc, q, session = _graph(fake_audio)
        coord = LibraryPlaybackCoordinator(lib, session)
        coord.play_visible_track(0)
        fake_audio.trigger_media_accepted(Path(tmp) / "b.mp3")
        assert session.state.context_type.name == "SINGLE"
        assert q.state.count == 0  # Queue untouched


class TestPlaybackAuthority:
    def test_error_only_through_service(self, fake_audio):
        svc = PlaybackService(fake_audio)
        svc.report_error("test")
        assert svc.state.error_message == "test"

    def test_rejection_reaches_playback_without_coordinator_wiring(self, fake_audio):
        svc = PlaybackService(fake_audio)
        svc.load_and_play(Path("/tmp/a.mp3"))
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))
        fake_audio.trigger_media_rejected(Path("/tmp/a.mp3"), "e")
        assert svc.state.error_message == "e"

    def test_coordinator_does_not_mutate_queue_state(self, fake_audio):
        svc, q, session = _graph(fake_audio)
        q.add(Path("/tmp/a.mp3"))
        q.add(Path("/tmp/b.mp3"))
        c = PlaybackCoordinator(fake_audio, svc)
        c.start()
        fake_audio.trigger_position(1000)
        fake_audio.trigger_duration(2000)
        assert q.state.count == 2
        assert svc.state.position_ms == 1000
        assert svc.state.duration_ms == 2000


class TestSettingsPreservation:
    def test_full_state_preserved_on_shutdown(self, tmp_path):
        from michi.domain.settings import SettingsState
        from michi.infrastructure.sqlite_settings import SQLiteSettingsRepository

        db = tmp_path / "test.db"
        repo = SQLiteSettingsRepository(db)
        repo.save(
            SettingsState(
                volume=20,
                muted=False,
                last_directory="/music",
                recent_files=["a.mp3", "b.mp3"],
            )
        )

        # Simulate runtime change during shutdown
        s = repo.load()
        s.volume = 55
        s.muted = True
        repo.save(s)

        s2 = repo.load()
        assert s2.volume == 55
        assert s2.muted is True
        assert s2.last_directory == "/music"
        assert s2.recent_files == ["a.mp3", "b.mp3"]


class TestBridgeDispose:
    def test_dispose_unsubscribes(self, fake_audio):
        svc = PlaybackService(fake_audio)
        from michi.presentation.playback_bridge import PlaybackBridge

        bridge = PlaybackBridge(svc)
        # bridge subscribed during init
        assert len(svc._subscribers) == 1
        bridge.dispose()
        assert len(svc._subscribers) == 0


class TestLibraryBridgeSearchQuery:
    def test_search_query_property(self, fake_audio):
        from michi.presentation.library_bridge import LibraryBridge

        class FakeScanner:
            def scan(self, root):
                return [root / "a.mp3"]

            def validate_file(self, path):
                return None

        lib = LibraryService(FakeScanner())
        lib.scan("/tmp")
        bridge = LibraryBridge(lib)
        lib.search("depeche")
        assert bridge.property("searchQuery") == "depeche"
