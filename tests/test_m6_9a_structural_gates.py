"""M6.9A — permanent structural regression gates.

Pytest-encoded equivalents of the WP shell gates (rg / git diff), so the
firewall is enforced by CI forever, not just by a one-off verification:

- TrackMetadata schema byte-for-byte unchanged (exact field set)
- AlbumRef / ArtistRef / MusicModel / TrackRef / GenreRef unchanged
- LibraryIndexEntry + metadata codec unchanged
- MetadataExtractorPort unchanged (single ``extract`` method)
- ZERO implementation references to external identity/enrichment concepts
  in the canonical local-metadata files
- Enrichment modules import NOTHING from library-index/metadata-extractor
  and contain no tag-write logic (no mutagen)
"""

from pathlib import Path

ROOT = Path(__file__).parent.parent

TRACK_METADATA_FIELDS = {
    "title",
    "artist",
    "album",
    "duration_ms",
    "genre",
    "year",
    "album_artist",
    "track_number",
    "track_total",
    "disc_number",
    "disc_total",
    "composer",
    "date",
    "compilation",
    "sort_title",
    "sort_artist",
    "sort_album",
    "sort_album_artist",
    "codec",
    "container",
    "sample_rate_hz",
    "bit_depth",
    "channels",
    "bitrate_bps",
    "file_size",
}

FORBIDDEN_LOCAL_TOKENS = (
    "musicbrainz",
    "wikidata",
    "wikipedia",
    "wikimedia",
    "biography",
    "external_genre",
    "external_cover",
    "external_year",
    "external_label",
    "mbid",
    "enrichment",
)

FORBIDDEN_METADATA_FIELD_NAMES = {
    "musicbrainz_artist_id",
    "musicbrainz_album_id",
    "musicbrainz_release_group_id",
    "musicbrainz_recording_id",
    "wikidata_id",
    "biography",
    "artist_image",
    "external_cover",
    "external_genres",
    "external_country",
    "external_year",
    "external_label",
}

CANONICAL_FILES = (
    "src/michi/domain/library.py",
    "src/michi/domain/library_index.py",
    "src/michi/infrastructure/metadata_extractor.py",
    "src/michi/infrastructure/library_index.py",
)

ENRICHMENT_MODULES = (
    "src/michi/domain/enrichment.py",
    "src/michi/application/enrichment_ports.py",
    "src/michi/application/enrichment_service.py",
    "src/michi/infrastructure/enrichment_repository.py",
    "src/michi/infrastructure/enrichment_assets.py",
)


def read(relative: str) -> str:
    return (ROOT / relative).read_text()


class TestTrackMetadataSchemaFrozen:
    def test_track_metadata_field_set_byte_for_byte(self):
        from michi.domain.library import TrackMetadata

        assert set(TrackMetadata.__dataclass_fields__) == TRACK_METADATA_FIELDS

    def test_no_forbidden_field_names_on_local_carriers(self):
        from michi.domain.library import (
            AlbumRef,
            ArtistRef,
            MusicModel,
            TrackMetadata,
            TrackRef,
        )

        for model in (TrackMetadata, TrackRef, AlbumRef, ArtistRef, MusicModel):
            assert not set(model.__dataclass_fields__).intersection(
                FORBIDDEN_METADATA_FIELD_NAMES
            )

    def test_album_artist_music_model_fields_unchanged(self):
        from michi.domain.library import AlbumRef, ArtistRef, MusicModel

        assert set(AlbumRef.__dataclass_fields__) == {
            "key",
            "title",
            "artist",
            "track_count",
            "duration_ms",
            "track_paths",
            "has_artwork",
            "year",
            "disc_count",
            "genres",
            "composers",
            "technical_summary",
        }
        assert set(ArtistRef.__dataclass_fields__) == {
            "key",
            "name",
            "track_count",
            "album_count",
        }
        assert set(MusicModel.__dataclass_fields__) == {
            "albums",
            "artists",
            "genres",
            "composers",
        }


class TestLibraryIndexFrozen:
    def test_library_index_entry_fields_unchanged(self):
        from michi.domain.library_index import LibraryIndexEntry

        assert set(LibraryIndexEntry.__dataclass_fields__) == {
            "track_id",
            "file_size",
            "mtime_ns",
            "metadata",
        }

    def test_library_index_schema_version_unchanged(self):
        from michi.infrastructure.library_index import (
            CURRENT_LIBRARY_INDEX_SCHEMA,
        )

        assert CURRENT_LIBRARY_INDEX_SCHEMA == 1

    def test_metadata_codec_signatures_unchanged(self):
        import inspect

        from michi.domain.library_index import (
            decode_index_metadata,
            encode_index_metadata,
        )

        assert list(inspect.signature(encode_index_metadata).parameters) == ["meta"]
        assert list(inspect.signature(decode_index_metadata).parameters) == ["raw"]


class TestMetadataExtractorFrozen:
    def test_metadata_extractor_port_has_only_extract(self):
        from michi.application.ports import MetadataExtractorPort

        assert set(MetadataExtractorPort.__abstractmethods__) == {"extract"}

    def test_extractor_module_has_no_forbidden_tokens(self):
        source = read("src/michi/infrastructure/metadata_extractor.py")
        for token in FORBIDDEN_LOCAL_TOKENS:
            assert token not in source, token


class TestCanonicalFilesContainZeroExternalReferences:
    def test_rg_gate(self):
        for relative in CANONICAL_FILES:
            source = read(relative)
            for token in FORBIDDEN_LOCAL_TOKENS:
                assert token not in source, f"{relative}: {token}"


class TestEnrichmentModulesAreIsolated:
    @staticmethod
    def _analysis(source: str) -> tuple[list[str], set[str]]:
        import ast

        tree = ast.parse(source)
        imports: list[str] = []
        attrs: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            elif isinstance(node, ast.Attribute):
                attrs.add(node.attr)
        return imports, attrs

    def test_enrichment_modules_import_nothing_canonical_writable(self):
        for relative in ENRICHMENT_MODULES:
            imports, _ = self._analysis(read(relative))
            for module in imports:
                for forbidden in (
                    "library_index",
                    "metadata_extractor",
                    "mutagen",
                    "artwork",
                ):
                    assert forbidden not in module, f"{relative}: {module}"

    def test_enrichment_service_has_no_tag_write_or_index_write_path(self):
        imports, attrs = self._analysis(
            read("src/michi/application/enrichment_service.py")
        )
        for module in imports:
            assert "michi.application.ports" not in module
        for banned in ("save", "delete", "tags"):
            assert banned not in attrs, banned
