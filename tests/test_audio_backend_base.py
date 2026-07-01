"""Tests for AudioBackend API — models, errors, and protocol."""


class TestBackendCapabilities:
    def test_defaults(self):
        from audio.backends.types import BackendCapabilities
        caps = BackendCapabilities(backend_id="test", display_name="Test")
        assert caps.backend_id == "test"
        assert caps.supports_eq is False
        assert caps.supports_digital_volume is True

    def test_custom_values(self):
        from audio.backends.types import BackendCapabilities
        caps = BackendCapabilities(
            backend_id="hifi", display_name="Hi-Fi",
            supports_bitperfect=True, supports_dsd=True,
            supports_digital_volume=False)
        assert caps.supports_bitperfect is True
        assert caps.supports_digital_volume is False


class TestPlaybackSnapshot:
    def test_defaults(self):
        from audio.backends.types import PlaybackSnapshot
        snap = PlaybackSnapshot(backend_id="test", state="stopped")
        assert snap.state == "stopped"
        assert snap.volume == 70
        assert snap.queue_index == -1

    def test_full_snapshot(self):
        from audio.backends.types import PlaybackSnapshot
        snap = PlaybackSnapshot(
            backend_id="gst", state="playing",
            current_path="/tmp/song.flac", title="Song",
            artist="Artist", album="Album",
            position_seconds=30.0, duration_seconds=240.0,
            volume=50, queue_index=2, queue_length=10)
        assert snap.current_path == "/tmp/song.flac"
        assert snap.position_seconds == 30.0

    def test_state_literals(self):
        from audio.backends.types import PlaybackSnapshot
        for s in ("stopped", "playing", "paused", "buffering", "error"):
            snap = PlaybackSnapshot(backend_id="t", state=s)
            assert snap.state == s


class TestAudioDiagnostics:
    def test_defaults(self):
        from audio.backends.types import AudioDiagnostics
        diag = AudioDiagnostics(backend_id="test", profile="standard")
        assert diag.bitperfect_status == "unknown"
        assert diag.warnings == []

    def test_bitperfect_states(self):
        from audio.backends.types import AudioDiagnostics
        diag = AudioDiagnostics(
            backend_id="mpd", profile="bitperfect_pcm",
            bitperfect_requested=True, bitperfect_possible=True,
            bitperfect_verified=True, bitperfect_status="verified")
        assert diag.bitperfect_verified is True
        assert diag.bitperfect_status == "verified"

    def test_dsp_flags(self):
        from audio.backends.types import AudioDiagnostics
        diag = AudioDiagnostics(
            backend_id="gst", profile="standard",
            dsp_active=True, eq_active=True,
            replaygain_active=True, spectrum_active=True)
        assert diag.dsp_active is True


class TestBackendErrors:
    def test_base_error(self):
        from audio.backends.errors import AudioBackendError
        err = AudioBackendError("base error")
        assert str(err) == "base error"

    def test_not_available(self):
        from audio.backends.errors import BackendNotAvailableError
        err = BackendNotAvailableError("MPD not found")
        assert "MPD" in str(err)

    def test_connection_error(self):
        from audio.backends.errors import BackendConnectionError
        err = BackendConnectionError("Connection refused")
        assert "Connection" in str(err)

    def test_playback_error(self):
        from audio.backends.errors import BackendPlaybackError
        err = BackendPlaybackError("Failed to play")
        assert "play" in str(err)

    def test_capability_error(self):
        from audio.backends.errors import BackendCapabilityError
        err = BackendCapabilityError("Not supported")
        assert "Not" in str(err)


class TestAudioBackendProtocol:
    def test_protocol_is_importable(self):
        from audio.backends.base import AudioBackend
        assert AudioBackend is not None

    def test_protocol_has_required_methods(self):
        from audio.backends.base import AudioBackend
        methods = [
            "play", "pause", "resume", "toggle", "stop", "seek",
            "set_volume", "set_queue", "enqueue", "enqueue_next",
            "clear_queue", "play_next", "play_prev",
            "get_queue", "get_queue_index",
            "get_snapshot", "get_diagnostics", "shutdown",
        ]
        for attr in methods:
            assert hasattr(AudioBackend, attr), f"Missing {attr}"

    def test_protocol_accepts_concrete_implementation(self):
        from audio.backends.base import AudioBackend
        from audio.backends.types import BackendCapabilities

        class FakeBackend:
            backend_id = "fake"
            capabilities = BackendCapabilities(backend_id="fake", display_name="Fake")
            def play(self, path_or_uri): pass
            def pause(self): pass
            def resume(self): pass
            def toggle(self): pass
            def stop(self): pass
            def seek(self, seconds): pass
            def set_volume(self, volume): pass
            def set_queue(self, paths, start_index=0): pass
            def enqueue(self, paths, play_now=True): pass
            def enqueue_next(self, paths): pass
            def clear_queue(self): pass
            def play_next(self): return False
            def play_prev(self): return False
            def get_queue(self): return []
            def get_queue_index(self): return -1
            def get_snapshot(self): pass
            def get_diagnostics(self): pass
            def shutdown(self): pass

        fb: AudioBackend = FakeBackend()
        assert fb.backend_id == "fake"
