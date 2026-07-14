from core.metadata.cancellation import MetadataCancellationToken, MetadataCancellationSource


class TestMetadataCancellationToken:
    def test_not_cancelled_by_default(self):
        token = MetadataCancellationToken()
        assert token.cancelled is False

    def test_cancel(self):
        token = MetadataCancellationToken()
        token.cancel()
        assert token.cancelled is True

    def test_reset(self):
        token = MetadataCancellationToken()
        token.cancel()
        token.reset()
        assert token.cancelled is False


class TestMetadataCancellationSource:
    def test_creates_token(self):
        source = MetadataCancellationSource()
        assert source.token is not None

    def test_cancel_increments_generation(self):
        source = MetadataCancellationSource()
        gen1 = source.generation
        source.cancel()
        assert source.generation > gen1

    def test_is_stale(self):
        source = MetadataCancellationSource()
        gen = source.generation
        source.cancel()
        assert source.is_stale(gen)

    def test_reset(self):
        source = MetadataCancellationSource()
        source.cancel()
        source.reset()
        assert source.token.cancelled is False
