"""E2E test: queue save and restore."""
def test_e2e_queue():
    from audio.backends.gstreamer_backend import GStreamerAudioBackend
    b = GStreamerAudioBackend()
    b.set_queue(["a.flac", "b.flac", "c.flac"], 0)
    assert b.get_queue_index() == 0
    b.play_next()
    assert b.get_queue_index() == 1
    b.play_prev()
    assert b.get_queue_index() == 0
