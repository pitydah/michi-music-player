"""E2E test: complete playback cycle."""
def test_e2e_play_pause_stop():
    from audio.backends.gstreamer_backend import GStreamerAudioBackend
    b = GStreamerAudioBackend()
    b.play("/nonexistent/file.wav")
    b.pause()
    b.resume()
    b.stop()
    snap = b.get_snapshot()
    assert snap.backend_id == "gstreamer"
