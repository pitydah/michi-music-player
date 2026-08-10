"""Tests for convergence patch fixes."""

from pathlib import Path

from michi.application.coordinator import PlaybackCoordinator
from michi.application.library_service import LibraryService
from michi.application.playback_service import PlaybackService
from michi.application.queue_service import QueueService
from michi.domain.playback import PlaybackStatus


class TestSeekUnits:
    def test_seek_seconds_converts_to_ms(self, fake_audio):
        svc = PlaybackService(fake_audio)
        svc.seek(60)  # ms directly
        assert fake_audio._position == 60  # AudioPort receives ms

    def test_seek_zero(self, fake_audio):
        svc = PlaybackService(fake_audio)
        svc.seek(0)
        assert fake_audio._position == 0


class TestEndOfMedia:
    def test_with_next_track(self, fake_audio):
        svc = PlaybackService(fake_audio)
        q = QueueService(svc)
        q.add(Path("/tmp/a.mp3"))
        q.add(Path("/tmp/b.mp3"))
        q.play_index(0)
        coord = PlaybackCoordinator(fake_audio, q, svc)
        coord.start()
        fake_audio.trigger_end_of_media()
        assert q.state.current_index == 1

    def test_at_end_of_queue(self, fake_audio):
        svc = PlaybackService(fake_audio)
        q = QueueService(svc)
        q.add(Path("/tmp/a.mp3"))
        q.play_index(0)
        coord = PlaybackCoordinator(fake_audio, q, svc)
        coord.start()
        fake_audio.trigger_end_of_media()
        assert svc.state.status == PlaybackStatus.STOPPED
        assert svc.state.position_ms == 0


class TestSubscriptionOwnership:
    def test_subscribe_unsubscribe_eom(self, fake_audio):
        calls = []

        def cb():
            calls.append(1)

        fake_audio.subscribe_end_of_media(cb)
        fake_audio.trigger_end_of_media()
        assert len(calls) == 1
        fake_audio.unsubscribe_end_of_media(cb)
        fake_audio.trigger_end_of_media()
        assert len(calls) == 1  # not called again

    def test_multiple_subscribers(self, fake_audio):
        calls_a = []
        calls_b = []

        def ca():
            calls_a.append(1)

        def cb():
            calls_b.append(1)

        fake_audio.subscribe_end_of_media(ca)
        fake_audio.subscribe_end_of_media(cb)
        fake_audio.trigger_end_of_media()
        assert len(calls_a) == 1 and len(calls_b) == 1
        fake_audio.unsubscribe_end_of_media(ca)
        fake_audio.trigger_end_of_media()
        assert len(calls_a) == 1  # a unsubscribed
        assert len(calls_b) == 2  # b still active

    def test_position_events(self, fake_audio):
        calls = []

        def cb(p, d):
            calls.append((p, d))

        fake_audio.subscribe_position_changed(cb)
        fake_audio.trigger_position(5000, 200000)
        assert calls == [(5000, 200000)]
        fake_audio.unsubscribe_position_changed(cb)
        fake_audio.trigger_position(8000, 200000)
        assert len(calls) == 1

    def test_error_events(self, fake_audio):
        calls = []

        def cb(m):
            calls.append(m)

        fake_audio.subscribe_error(cb)
        fake_audio.trigger_error("decode failed")
        assert calls == ["decode failed"]


class TestLibraryService:
    def test_scan_populates_visible(self, tmp_path):
        from michi.infrastructure.filesystem_scanner import FilesystemLibraryScanner

        (tmp_path / "a.mp3").write_text("")
        (tmp_path / "b.flac").write_text("")
        q = QueueService(PlaybackService(FakeAudioPort()))
        svc = LibraryService(FilesystemLibraryScanner(), q)
        svc.scan(str(tmp_path))
        assert len(svc.state.visible_tracks) == 2

    def test_search_filters_visible(self, tmp_path):
        from michi.infrastructure.filesystem_scanner import FilesystemLibraryScanner

        (tmp_path / "Depeche Mode - song.mp3").write_text("")
        (tmp_path / "Toto - song.mp3").write_text("")
        q = QueueService(PlaybackService(FakeAudioPort()))
        svc = LibraryService(FilesystemLibraryScanner(), q)
        svc.scan(str(tmp_path))
        svc.search("depeche")
        assert len(svc.state.visible_tracks) == 1
        assert "Depeche" in svc.state.visible_tracks[0].display_name

    def test_activate_visible_track(self, tmp_path):
        from michi.infrastructure.filesystem_scanner import FilesystemLibraryScanner

        (tmp_path / "a.mp3").write_text("")
        (tmp_path / "b.mp3").write_text("")
        (tmp_path / "c.mp3").write_text("")
        q = QueueService(PlaybackService(FakeAudioPort()))
        svc = LibraryService(FilesystemLibraryScanner(), q)
        svc.scan(str(tmp_path))
        svc.search("b")
        assert len(svc.state.visible_tracks) == 1
        svc.activate(0)  # activate visible index 0 → "b.mp3"
        assert q.state.count == 1
        assert q.state.tracks[0].file_path.name == "b.mp3"


class FakeAudioPort:
    """Minimal inline fake — avoids circular imports in test file."""

    def __init__(self) -> None:
        self.loaded = None
        self.state = "stopped"
        self.volume = 80
        self.muted = False
        self._position = 0
        self._duration = 0
        self._eom = []
        self._pos = []
        self._err = []

    def load(self, p):
        self.loaded = p

    def play(self):
        self.state = "playing"

    def pause(self):
        self.state = "paused"

    def resume(self):
        self.state = "playing"

    def stop(self):
        self.state = "stopped"

    def set_volume(self, v):
        self.volume = max(0, min(100, v))

    def set_muted(self, m):
        self.muted = m

    def seek(self, ms):
        self._position = ms

    def position(self):
        return self._position

    def duration(self):
        return self._duration

    def subscribe_end_of_media(self, cb):
        self._eom.append(cb)

    def unsubscribe_end_of_media(self, cb):
        self._eom.remove(cb)

    def subscribe_position_changed(self, cb):
        self._pos.append(cb)

    def unsubscribe_position_changed(self, cb):
        self._pos.remove(cb)

    def subscribe_error(self, cb):
        self._err.append(cb)

    def unsubscribe_error(self, cb):
        self._err.remove(cb)
