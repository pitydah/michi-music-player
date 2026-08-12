"""Tests for convergence patch 3."""

from pathlib import Path

import pytest

from michi.application.coordinator import PlaybackCoordinator
from michi.application.library_service import LibraryService
from michi.application.playback_service import PlaybackService
from michi.application.queue_service import QueueService
from michi.domain.playback import PlaybackStatus
from michi.presentation.playback_bridge import PlaybackBridge


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
    def test_with_next(self, fake_audio):
        svc = PlaybackService(fake_audio)
        q = QueueService(svc)
        q.add(Path("/tmp/a.mp3"))
        q.add(Path("/tmp/b.mp3"))
        q.play_index(0)
        coord = PlaybackCoordinator(fake_audio, q, svc)
        coord.start()
        fake_audio.trigger_end_of_media()
        assert q.state.current_index == 1

    def test_auto_advance_failure_preserves_index(self, fake_audio, monkeypatch):
        svc = PlaybackService(fake_audio)
        q = QueueService(svc)
        q.add(Path("/tmp/a.mp3"))
        q.add(Path("/tmp/b.mp3"))
        q.play_index(0)
        coord = PlaybackCoordinator(fake_audio, q, svc)
        coord.start()

        def failing_load(p):
            raise RuntimeError("load failed")

        monkeypatch.setattr(fake_audio, "load", failing_load)

        with pytest.raises(RuntimeError):
            fake_audio.trigger_end_of_media()

        assert q.state.current_index == 0

    def test_at_end(self, fake_audio):
        svc = PlaybackService(fake_audio)
        q = QueueService(svc)
        q.add(Path("/tmp/a.mp3"))
        q.play_index(0)
        coord = PlaybackCoordinator(fake_audio, q, svc)
        coord.start()
        fake_audio.trigger_end_of_media()
        assert svc.state.status == PlaybackStatus.STOPPED
        assert svc.state.position_ms == 0


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

    def test_error_events(self, fake_audio):
        calls = []

        def cb(m):
            calls.append(m)

        fake_audio.subscribe_error(cb)
        fake_audio.trigger_error("decode failed")
        assert calls == ["decode failed"]


class TestCoordinatorIdempotent:
    def test_double_start_safe(self, fake_audio):
        svc = PlaybackService(fake_audio)
        q = QueueService(svc)
        c = PlaybackCoordinator(fake_audio, q, svc)
        c.start()
        c.start()  # idempotent
        assert c._started

    def test_double_stop_safe(self, fake_audio):
        svc = PlaybackService(fake_audio)
        q = QueueService(svc)
        c = PlaybackCoordinator(fake_audio, q, svc)
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

    def test_queue_notify_from_library_activate(self, fake_audio):
        svc = PlaybackService(fake_audio)
        q = QueueService(svc)

        # Need a scanner fake
        class FakeScanner:
            def scan(self, root):
                return [root / "a.mp3"]

        lib = LibraryService(FakeScanner(), q)
        lib.scan("/tmp")

        calls = []

        def cb():
            calls.append(1)

        q.subscribe_changed(cb)
        lib.activate(0)
        assert len(calls) >= 1  # queue was mutated
        assert q.state.count >= 1

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
        svc = PlaybackService(fake_audio)
        q = QueueService(svc)

        class FakeScanner:
            def scan(self, root):
                return [root / "a.mp3"]

        lib = LibraryService(FakeScanner(), q)
        calls = []

        def cb():
            calls.append(1)

        lib.subscribe_changed(cb)
        lib.scan("/tmp")
        assert len(calls) == 1


class TestLibraryService:
    def test_scan_and_search(self, fake_audio):
        svc = PlaybackService(fake_audio)
        q = QueueService(svc)

        from michi.infrastructure.filesystem_scanner import FilesystemLibraryScanner

        (tmp := Path("/tmp/michi_test_lib"))
        tmp.mkdir(exist_ok=True)
        (tmp / "Depeche Mode - a.mp3").write_text("")
        (tmp / "Toto - b.mp3").write_text("")

        lib = LibraryService(FilesystemLibraryScanner(), q)
        lib.scan(str(tmp))
        assert len(lib.state.visible_tracks) == 2
        lib.search("depeche")
        assert len(lib.state.visible_tracks) == 1

    def test_activate_filtered(self, fake_audio):
        svc = PlaybackService(fake_audio)
        q = QueueService(svc)

        (tmp := Path("/tmp/michi_test_act"))
        tmp.mkdir(exist_ok=True)
        (tmp / "a.mp3").write_text("")
        (tmp / "b.mp3").write_text("")
        (tmp / "c.mp3").write_text("")

        from michi.infrastructure.filesystem_scanner import FilesystemLibraryScanner

        lib = LibraryService(FilesystemLibraryScanner(), q)
        lib.scan(str(tmp))
        lib.search("b")
        assert len(lib.state.visible_tracks) == 1
        lib.activate(0)
        assert q.state.tracks[0].file_path.name == "b.mp3"


class TestPlaybackAuthority:
    def test_error_only_through_service(self, fake_audio):
        svc = PlaybackService(fake_audio)
        svc.report_error("test")
        assert svc.state.error_message == "test"

    def test_coordinator_does_not_mutate_state(self, fake_audio):
        svc = PlaybackService(fake_audio)
        q = QueueService(svc)
        c = PlaybackCoordinator(fake_audio, q, svc)
        c.start()
        fake_audio.trigger_error("e")
        assert svc.state.error_message == "e"


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
        from michi.application.library_service import LibraryService
        from michi.application.playback_service import PlaybackService
        from michi.application.queue_service import QueueService
        from michi.presentation.library_bridge import LibraryBridge

        svc = PlaybackService(fake_audio)
        q = QueueService(svc)

        class FakeScanner:
            def scan(self, root):
                return [root / "a.mp3"]

        lib = LibraryService(FakeScanner(), q)
        lib.scan("/tmp")
        bridge = LibraryBridge(lib)
        lib.search("depeche")
        assert bridge.property("searchQuery") == "depeche"
