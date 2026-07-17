"""E2E: fake AudioBackend → PlayerService pipeline.

Creates a FakeBackend implementing the AudioBackend Protocol, verifies
state transitions, injects it into PlayerService via HybridAudioManager,
and confirms the full playback flow works without real audio hardware.
"""

from __future__ import annotations

import pytest

from audio.backends.types import (
    BackendCapabilities,
    PlaybackSnapshot,
    AudioDiagnostics,
)


class FakeBackend:
    """Implementa AudioBackend Protocol con comportamiento predecible."""

    backend_id = "fake"
    capabilities = BackendCapabilities(
        backend_id="fake",
        display_name="Fake Backend",
        supports_eq=False,
        supports_replaygain=False,
        supports_spectrum=False,
        supports_radio=True,
        supports_streams=True,
        supports_bitperfect=False,
        supports_dsd=False,
        supports_dop=False,
        supports_remote=False,
        supports_server_mode=False,
        supports_digital_volume=True,
    )

    def __init__(self):
        self._state = "stopped"
        self._current_path = ""
        self._position = 0.0
        self._duration = 0.0
        self._volume = 70
        self._queue: list[dict] = []
        self._queue_index = -1

    def play(self, path_or_uri: str) -> None:
        self._state = "playing"
        self._current_path = path_or_uri
        self._position = 0.0
        self._duration = 240.0

    def pause(self) -> None:
        if self._state == "playing":
            self._state = "paused"

    def resume(self) -> None:
        if self._state == "paused":
            self._state = "playing"

    def toggle(self) -> None:
        if self._state == "playing":
            self.pause()
        else:
            self.resume()

    def stop(self) -> None:
        self._state = "stopped"
        self._position = 0.0

    def seek(self, seconds: float) -> None:
        self._position = seconds

    def set_volume(self, volume: int) -> None:
        self._volume = volume

    def set_queue(self, paths: list[str], start_index: int = 0) -> None:
        self._queue = [{"filepath": p} for p in paths]
        self._queue_index = start_index

    def enqueue(self, paths: list[str], play_now: bool = True) -> None:
        for p in paths:
            self._queue.append({"filepath": p})
        if play_now and paths:
            self._queue_index = len(self._queue) - len(paths)

    def enqueue_next(self, paths: list[str]) -> None:
        idx = max(self._queue_index + 1, 0)
        for p in reversed(paths):
            self._queue.insert(idx, {"filepath": p})

    def clear_queue(self) -> None:
        self._queue = []
        self._queue_index = -1

    def play_next(self) -> bool:
        if not self._queue or self._queue_index >= len(self._queue) - 1:
            return False
        self._queue_index += 1
        self._current_path = self._queue[self._queue_index].get("filepath", "")
        self._state = "playing"
        return True

    def play_prev(self) -> bool:
        if self._queue_index <= 0:
            return False
        self._queue_index -= 1
        self._current_path = self._queue[self._queue_index].get("filepath", "")
        self._state = "playing"
        return True

    def get_queue(self) -> list[dict]:
        return list(self._queue)

    def get_queue_index(self) -> int:
        return self._queue_index

    def get_snapshot(self) -> PlaybackSnapshot:
        return PlaybackSnapshot(
            backend_id=self.backend_id,
            state=self._state,
            current_path=self._current_path,
            position_seconds=self._position,
            duration_seconds=self._duration,
            volume=self._volume,
            queue_index=self._queue_index,
            queue_length=len(self._queue),
        )

    def get_diagnostics(self) -> AudioDiagnostics:
        return AudioDiagnostics(
            backend_id=self.backend_id,
            profile="standard",
        )

    def shutdown(self) -> None:
        self._state = "stopped"
        self._queue = []
        self._queue_index = -1


# ── Tests ──


class TestFakeBackend:
    """Pure unit tests for FakeBackend state machine."""

    def test_fake_backend_play(self):
        """FakeBackend.play() cambia estado a PLAYING."""
        backend = FakeBackend()
        backend.play("/test/file.flac")
        snap = backend.get_snapshot()
        assert snap.state == "playing"
        assert snap.current_path == "/test/file.flac"

    def test_fake_backend_pause_resume(self):
        """Pause y resume alternan estados."""
        backend = FakeBackend()
        backend.play("/test/file.flac")
        assert backend.get_snapshot().state == "playing"

        backend.pause()
        assert backend.get_snapshot().state == "paused"

        backend.resume()
        assert backend.get_snapshot().state == "playing"

    def test_fake_backend_stop(self):
        """Stop retorna a stopped."""
        backend = FakeBackend()
        backend.play("/test/file.flac")
        backend.stop()
        snap = backend.get_snapshot()
        assert snap.state == "stopped"
        assert snap.position_seconds == 0.0

    def test_fake_backend_seek(self):
        """Seek actualiza posicion."""
        backend = FakeBackend()
        backend.play("/test/file.flac")
        backend.seek(42.5)
        assert backend.get_snapshot().position_seconds == 42.5

    def test_fake_backend_volume(self):
        """set_volume se refleja en snapshot."""
        backend = FakeBackend()
        backend.set_volume(55)
        assert backend.get_snapshot().volume == 55

    def test_fake_backend_queue(self):
        """set_queue / enqueue / clear_queue funcionan."""
        backend = FakeBackend()
        backend.set_queue(["/a/1.flac", "/a/2.flac"], start_index=0)
        assert len(backend.get_queue()) == 2
        assert backend.get_queue_index() == 0

        backend.enqueue(["/a/3.flac"], play_now=False)
        assert len(backend.get_queue()) == 3

        backend.clear_queue()
        assert backend.get_queue() == []
        assert backend.get_queue_index() == -1

    def test_fake_backend_next_prev(self):
        """play_next y play_prev navegan cola."""
        backend = FakeBackend()
        backend.set_queue(["/a/1.flac", "/a/2.flac", "/a/3.flac"], start_index=0)
        backend.play("/a/1.flac")

        assert backend.play_next()
        assert backend.get_snapshot().current_path == "/a/2.flac"

        assert backend.play_next()
        assert backend.get_snapshot().current_path == "/a/3.flac"

        assert not backend.play_next()
        assert backend.get_snapshot().state == "playing"

        assert backend.play_prev()
        assert backend.get_snapshot().current_path == "/a/2.flac"

    def test_fake_backend_toggle(self):
        """toggle alterna play/pause."""
        backend = FakeBackend()
        backend.play("/test/file.flac")
        backend.toggle()
        assert backend.get_snapshot().state == "paused"
        backend.toggle()
        assert backend.get_snapshot().state == "playing"

    def test_fake_backend_shutdown(self):
        """shutdown detiene y limpia."""
        backend = FakeBackend()
        backend.play("/test/file.flac")
        backend.enqueue(["/a/1.flac"])
        backend.shutdown()
        snap = backend.get_snapshot()
        assert snap.state == "stopped"
        assert backend.get_queue() == []

    def test_fake_backend_diagnostics(self):
        """get_diagnostics devuelve AudioDiagnostics."""
        backend = FakeBackend()
        diag = backend.get_diagnostics()
        assert diag.backend_id == "fake"
        assert diag.profile == "standard"

    def test_fake_backend_capabilities(self):
        """capabilities es BackendCapabilities."""
        backend = FakeBackend()
        assert backend.capabilities.backend_id == "fake"
        assert backend.capabilities.supports_digital_volume is True


class TestPlayerServiceWithFakeBackend:
    """PlayerService funciona con FakeBackend via HybridAudioManager."""

    @pytest.fixture
    def fake_backend(self):
        return FakeBackend()

    def test_player_service_with_fake_backend(self, fake_backend):
        """PlayerService funciona con FakeBackend."""
        from audio.backends.hybrid_audio_manager import HybridAudioManager
        hybrid = HybridAudioManager(default_backend=fake_backend)
        from audio.player_service import PlayerService
        player = PlayerService(parent=None)
        player._hybrid = hybrid
        player._active_backend_id = "fake"

        player.play("/test/file.flac")
        assert player.state == "playing"
        assert player.current == "/test/file.flac"

        player.pause()
        assert player.state == "paused"

        player.resume()
        assert player.state == "playing"

        player.stop()
        assert player.state == "stopped"

    def test_player_service_volume(self, fake_backend):
        """set_volume via PlayerService afecta al backend."""
        from audio.backends.hybrid_audio_manager import HybridAudioManager
        hybrid = HybridAudioManager(default_backend=fake_backend)
        from audio.player_service import PlayerService
        player = PlayerService(parent=None)
        player._hybrid = hybrid
        player._active_backend_id = "fake"

        player.set_volume(42)
        assert fake_backend.get_snapshot().volume == 42

    def test_player_service_queue(self, fake_backend):
        """Queue operations via PlayerService."""
        from audio.backends.hybrid_audio_manager import HybridAudioManager
        hybrid = HybridAudioManager(default_backend=fake_backend)
        from audio.player_service import PlayerService
        player = PlayerService(parent=None)
        player._hybrid = hybrid
        player._active_backend_id = "fake"

        player.enqueue(["/a/1.flac", "/a/2.flac"], play_now=True)
        assert len(fake_backend.get_queue()) == 2

        player.play_next()
        assert player.state == "playing"

        player.clear_queue()
        assert fake_backend.get_queue() == []

    def test_player_service_snapshot(self, fake_backend):
        """get_playback_snapshot y state property."""
        from audio.backends.hybrid_audio_manager import HybridAudioManager
        hybrid = HybridAudioManager(default_backend=fake_backend)
        from audio.player_service import PlayerService
        player = PlayerService(parent=None)
        player._hybrid = hybrid
        player._active_backend_id = "fake"

        player.play("/test/song.flac")
        snap = player.get_playback_snapshot()
        assert snap.state == "playing"
        assert snap.current_path == "/test/song.flac"
        assert snap.duration_seconds == 240.0

    def test_player_service_get_backend_capabilities(self, fake_backend):
        """get_backend_capabilities refleja FakeBackend."""
        from audio.backends.hybrid_audio_manager import HybridAudioManager
        hybrid = HybridAudioManager(default_backend=fake_backend)
        from audio.player_service import PlayerService
        player = PlayerService(parent=None)
        player._hybrid = hybrid
        player._active_backend_id = "fake"

        caps = player.get_backend_capabilities()
        assert caps.backend_id == "fake"
        assert caps.supports_digital_volume is True

    def test_player_get_active_backend_id(self, fake_backend):
        """get_active_backend_id() devuelve 'fake'."""
        from audio.backends.hybrid_audio_manager import HybridAudioManager
        hybrid = HybridAudioManager(default_backend=fake_backend)
        from audio.player_service import PlayerService
        player = PlayerService(parent=None)
        player._hybrid = hybrid
        player._active_backend_id = "fake"

        assert player.get_active_backend_id() == "fake"
