from core.lyrics.cancellation import (
    LyricsCancellationToken, LyricsCancellationSource, LyricsRequestTracker,
)


class TestLyricsCancellationToken:
    def test_not_cancelled_by_default(self):
        token = LyricsCancellationToken()
        assert not token.cancelled

    def test_cancel(self):
        token = LyricsCancellationToken()
        token.cancel()
        assert token.cancelled

    def test_reset(self):
        token = LyricsCancellationToken()
        token.cancel()
        token.reset()
        assert not token.cancelled


class TestLyricsCancellationSource:
    def test_generates_token(self):
        source = LyricsCancellationSource()
        assert source.token is not None

    def test_cancel_increments_generation(self):
        source = LyricsCancellationSource()
        gen1 = source.generation
        source.cancel()
        assert source.generation > gen1

    def test_is_stale(self):
        source = LyricsCancellationSource()
        gen = source.generation
        source.cancel()
        assert source.is_stale(gen)

    def test_reset(self):
        source = LyricsCancellationSource()
        source.cancel()
        gen_after = source.generation
        source.reset()
        assert source.generation > gen_after
        assert not source.token.cancelled


class TestLyricsRequestTracker:
    def test_begin_returns_token(self):
        tracker = LyricsRequestTracker()
        token = tracker.begin("req-1", "hash-1")
        assert token is not None

    def test_cancel_current(self):
        tracker = LyricsRequestTracker()
        tracker.begin("req-1", "hash-1")
        assert not tracker._source.token.cancelled
        tracker.cancel_current()
        assert tracker._source.token.cancelled

    def test_is_stale_with_old_generation(self):
        tracker = LyricsRequestTracker()
        gen = tracker.generation
        tracker.begin("req-2", "hash-2")
        assert tracker.is_stale(gen)

    def test_not_stale_with_current(self):
        tracker = LyricsRequestTracker()
        gen = tracker.generation
        assert not tracker.is_stale(gen)

    def test_new_request_cancels_old(self):
        tracker = LyricsRequestTracker()
        token1 = tracker.begin("req-1", "hash-1")
        token2 = tracker.begin("req-2", "hash-2")
        assert token1.cancelled
        assert not token2.cancelled
