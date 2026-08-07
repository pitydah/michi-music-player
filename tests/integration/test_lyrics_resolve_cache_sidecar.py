"""Lyrics resolve/cache/sidecar integration (Slice 5).

Canonical LyricsService over temporary storage: resolve writes a sidecar when
asked, cache serves repeat resolves without a second provider fetch,
load_sidecar READS what was saved (regression for the confirmed bug), and a
save -> load roundtrip preserves the document.
"""
from __future__ import annotations

from core.lyrics.models import (
    TrackIdentity, LyricsDocument, LyricsSource,
    LyricsOperationResult,
)
from core.lyrics.service import LyricsService
from core.lyrics.resolver import LyricsResolver
from core.lyrics.registry import LyricsProviderRegistry
from core.lyrics.storage import LyricsStorageService
from core.lyrics.editor import LyricsEditorService


class _StubProvider:
    """Records every fetch; serves canned documents (mirrors the canonical
    provider behaviour: checks and fills the cache repository)."""

    def __init__(self, doc: LyricsDocument | None, cache=None):
        self._doc = doc
        self._cache = cache
        self.fetches = 0
        self._contract = None

    @property
    def contract(self):
        if self._contract is None:
            from core.lyrics.models import ProviderContract
            self._contract = ProviderContract(
                provider_id="stub", display_name="Stub", priority=10,
            )
        return self._contract

    def resolve(self, identity, timeout_ms=10000):
        cache_key = f"stub:{identity.title.lower().strip()}|{identity.artist.lower().strip()}"
        if self._cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return LyricsOperationResult(ok=True, document=cached, source="cache")
        self.fetches += 1
        if self._doc is None:
            if self._cache:
                self._cache.put_negative(cache_key)
            return LyricsOperationResult(ok=False, code="not_found")
        if self._cache:
            self._cache.put(cache_key, self._doc)
        return LyricsOperationResult(ok=True, document=self._doc)

    def search(self, identity, timeout_ms=10000):
        return LyricsOperationResult(ok=True, candidates=[self._doc] if self._doc else [])

    def close(self):
        pass


class _FakeCache:
    """In-memory cache repository implementing the LyricsCacheRepository API."""

    def __init__(self):
        self._store: dict[str, LyricsDocument] = {}
        self._negative: set[str] = set()

    def get(self, cache_key):
        return self._store.get(cache_key)

    def put(self, cache_key, doc, ttl_s=86400):
        self._store[cache_key] = doc

    def get_negative(self, cache_key):
        return cache_key in self._negative

    def put_negative(self, cache_key, ttl_s=3600):
        self._negative.add(cache_key)

    def invalidate(self, cache_key):
        self._store.pop(cache_key, None)
        self._negative.discard(cache_key)

    def invalidate_all(self):
        self._store.clear()
        self._negative.clear()

    def close(self):
        pass


def _build_service(sidecar_dir: str, provider: _StubProvider, cache=None):
    from infrastructure.lyrics.sidecar_provider import FileSidecarProvider
    from infrastructure.lyrics.embedded_writer import MutagenEmbeddedLyricsWriter
    from core.lyrics.models import LyricsSettings

    registry = LyricsProviderRegistry()
    registry.register(provider)
    cache = cache or _FakeCache()
    sidecar = FileSidecarProvider()
    settings = LyricsSettings(provider_order=[provider.contract.provider_id])
    storage = LyricsStorageService(
        sidecar_provider=sidecar,
        embedded_writer=MutagenEmbeddedLyricsWriter(),
    )
    resolver = LyricsResolver(
        provider_registry=registry,
        cache_repo=cache,
        sidecar_provider=sidecar,
        settings=settings,
    )
    return LyricsService(
        resolver=resolver,
        provider_registry=registry,
        cache_repo=cache,
        storage_service=storage,
        editor_service=LyricsEditorService(),
        settings=settings,
    ), cache


class TestLyricsResolveCacheSidecar:
    def test_resolve_then_sidecar_write(self, tmp_path):
        doc = LyricsDocument(
            identity=TrackIdentity(title="Test Song", artist="Test Artist"),
            plain_text="Line one\nLine two",
            synced_text="",
            source=LyricsSource.REMOTE_PROVIDER,
            provider_id="stub",
        )
        svc, _ = _build_service(str(tmp_path), _StubProvider(doc))
        identity = TrackIdentity(title="Test Song", artist="Test Artist")
        result = svc.resolve(identity)
        assert result.ok and result.document

        saved = svc.save_sidecar(str(tmp_path), result.document)
        assert saved.ok

    def test_second_resolve_served_from_cache(self, tmp_path):
        doc = LyricsDocument(
            identity=TrackIdentity(title="Cached", artist="Artist"),
            plain_text="Cached lyrics",
            synced_text="",
            source=LyricsSource.REMOTE_PROVIDER,
            provider_id="stub",
        )
        cache = _FakeCache()
        provider = _StubProvider(doc, cache=cache)
        svc, _ = _build_service(str(tmp_path), provider, cache=cache)
        identity = TrackIdentity(title="Cached", artist="Artist")

        first = svc.resolve(identity)
        assert first.ok
        assert provider.fetches == 1

        second = svc.resolve(identity)
        assert second.ok
        assert provider.fetches == 1, "second resolve must come from cache"

    def test_load_sidecar_reads_what_was_saved(self, tmp_path):
        svc, _ = _build_service(str(tmp_path), _StubProvider(None))
        identity = TrackIdentity(title="Sidecar Song", artist="Sidecar Artist")
        doc = LyricsDocument(
            identity=identity,
            plain_text="Roundtrip line 1\nRoundtrip line 2",
            source=LyricsSource.MANUAL,
        )

        saved = svc.save_sidecar(str(tmp_path), doc)
        assert saved.ok

        loaded = svc.load_sidecar(str(tmp_path), identity)
        assert loaded.ok
        assert loaded.document is not None
        assert "Roundtrip line 1" in loaded.document.plain_text

    def test_load_sidecar_regression_no_write(self, tmp_path):
        """The confirmed bug wrote an empty document instead of reading."""
        svc, _ = _build_service(str(tmp_path), _StubProvider(None))
        identity = TrackIdentity(title="Missing", artist="Nobody")
        result = svc.load_sidecar(str(tmp_path), identity)
        assert not result.ok  # NOT_FOUND — nothing was written
        assert not list(tmp_path.iterdir()), "load_sidecar must never write files"

    def test_cache_hit_returns_same_document(self, tmp_path):
        doc = LyricsDocument(
            identity=TrackIdentity(title="Same", artist="Artist"),
            plain_text="Identical content",
            synced_text="",
            source=LyricsSource.REMOTE_PROVIDER,
            provider_id="stub",
        )
        svc, cache = _build_service(str(tmp_path), _StubProvider(doc))
        identity = TrackIdentity(title="Same", artist="Artist")

        first = svc.resolve(identity)
        second = svc.resolve(identity)
        assert first.ok and second.ok
        assert second.document.plain_text == first.document.plain_text

    def test_save_embedded_and_sidecar(self, tmp_path):
        import wave
        audio = tmp_path / "song.wav"
        with wave.open(str(audio), "w") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(44100)
            w.writeframes(b"\x00\x00" * 44100)

        svc, _ = _build_service(str(tmp_path), _StubProvider(None))
        doc = LyricsDocument(
            identity=TrackIdentity(title="Embed", artist="Artist", filepath=str(audio)),
            plain_text="Embedded line",
            source=LyricsSource.MANUAL,
        )
        result = svc.save_local(str(audio), doc)
        assert result.ok
        assert result.details.get("embedded") is False  # wav: sidecar only
        assert result.details.get("path", "").endswith("song.lrc")
        assert (tmp_path / "song.lrc").exists()
