"""M6-EXT-R4-M — persistent artwork-cache lookup (offline startup)."""

from pathlib import Path

from michi.domain.library import Artwork
from michi.infrastructure.artwork import ArtworkCache


class TestArtworkCacheLookup:
    def test_lookup_returns_none_before_any_store(self, tmp_path) -> None:
        cache = ArtworkCache(tmp_path / "cache")
        assert cache.lookup("album-1") is None

    def test_store_then_lookup_survives_restart(self, tmp_path) -> None:
        cache = ArtworkCache(tmp_path / "cache")
        artwork = Artwork(data=b"\x89PNG fake", mime_type="image/png")
        stored = cache.store("album-1", artwork)
        assert stored is not None
        assert stored.is_file()

        # A NEW instance (simulated restart) resolves the SAME mapping.
        restarted = ArtworkCache(tmp_path / "cache")
        resolved = restarted.lookup("album-1")
        assert resolved == stored
        assert resolved.is_file()

    def test_missing_file_invalidates_entry_without_crash(self, tmp_path) -> None:
        cache = ArtworkCache(tmp_path / "cache")
        artwork = Artwork(data=b"\x89PNG fake", mime_type="image/png")
        stored = cache.store("album-1", artwork)

        stored.unlink()  # cached file vanishes (corrupt/missing)
        restarted = ArtworkCache(tmp_path / "cache")
        assert restarted.lookup("album-1") is None  # honest invalidation

    def test_corrupt_manifest_degrades_to_empty(self, tmp_path) -> None:
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir(parents=True)
        (cache_dir / "manifest.json").write_text("not json {{", encoding="utf-8")
        cache = ArtworkCache(cache_dir)
        assert cache.lookup("album-1") is None

    def test_manifest_is_rebuildable_cache_not_authority(self, tmp_path) -> None:
        # Deleting the manifest never crashes; a rescan rebuilds it.
        cache = ArtworkCache(tmp_path / "cache")
        artwork = Artwork(data=b"\x89PNG fake", mime_type="image/png")
        cache.store("album-1", artwork)
        (tmp_path / "cache" / "manifest.json").unlink()

        cache2 = ArtworkCache(tmp_path / "cache")
        assert cache2.lookup("album-1") is None
        cache2.store("album-1", artwork)
        assert cache2.lookup("album-1") is not None


class TestEnrichmentCachedFirst:
    def test_enrich_uses_cached_artwork_before_provider(self, tmp_path) -> None:
        from michi.application.library_service import LibraryService
        from michi.domain.library import AlbumRef

        cache = ArtworkCache(tmp_path / "cache")
        artwork = Artwork(data=b"\x89PNG fake", mime_type="image/png")
        cache.store("4::kind of blue::miles davis", artwork)

        class _NoProvider:
            def get_embedded_artwork(self, path):
                raise AssertionError("provider must not run when cached")

            def get_embedded_front_artwork(self, path):
                raise AssertionError("provider must not run when cached")

            def get_local_artwork(self, album_dir):
                raise AssertionError("provider must not run when cached")

        service = LibraryService(
            scanner=None,  # type: ignore[arg-type]
            artwork_provider=_NoProvider(),  # type: ignore[arg-type]
            artwork_cache=cache,
        )
        albums = (
            AlbumRef(
                key="4::kind of blue::miles davis",
                title="Kind of Blue",
                artist="Miles Davis",
                track_count=1,
                duration_ms=1000,
                track_paths=(Path("/a.flac"),),
            ),
        )
        enriched = service._enrich_albums(albums)
        assert enriched[0].has_artwork is True
        assert service.artwork_path_for(enriched[0].key) is not None

    def test_offline_cached_cover_survives_rebuild(self, tmp_path) -> None:
        # Golden: cached artwork still displays after restart with the
        # source offline (no provider contact, no blank).

        cache = ArtworkCache(tmp_path / "cache")
        cache.store("k1", Artwork(data=b"\x89PNG fake", mime_type="image/png"))
        restarted = ArtworkCache(tmp_path / "cache")
        assert restarted.lookup("k1") is not None
