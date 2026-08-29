"""M6-EXT-R4-B — stable catalog identity domain contracts."""

import uuid

import pytest

from michi.domain.library_catalog import (
    LibrarySource,
    LibrarySourceId,
    MediaAvailability,
    MediaFileId,
    MediaFileRecord,
    SourceLifecycle,
    TrackId,
    TrackRecord,
    legacy_media_id,
    legacy_source_id,
    legacy_track_id,
    new_library_source_id,
    new_media_file_id,
    new_track_id,
    validate_relative_media_path,
)

# Pinned project namespaces: changing them would split every migrated id.
_PINNED_NAMESPACES = (
    "3c9d1b4e-8f2a-4c6d-9e01-2b7a3c4d5e6f",
    "7a4e2f3c-1b9d-4e5a-8c6f-0d1e2f3a4b5c",
    "5b1a6d2e-3c4f-4a7b-9e8d-1f2a3b4c5d6e",
)


class TestNewIdentities:
    def test_new_ids_are_uuid4_strings(self) -> None:
        for factory in (new_library_source_id, new_media_file_id, new_track_id):
            value = factory()
            assert isinstance(value, str)
            assert uuid.UUID(value).version == 4

    def test_new_ids_are_unique(self) -> None:
        assert len({new_library_source_id() for _ in range(20)}) == 20
        assert len({new_media_file_id() for _ in range(20)}) == 20
        assert len({new_track_id() for _ in range(20)}) == 20

    def test_new_ids_across_families_never_collide(self) -> None:
        all_ids = {new_library_source_id() for _ in range(5)}
        all_ids |= {new_media_file_id() for _ in range(5)}
        all_ids |= {new_track_id() for _ in range(5)}
        assert len(all_ids) == 15


class TestLegacyIdentities:
    def test_legacy_ids_are_deterministic(self) -> None:
        path = "/Music/A/song.flac"
        assert legacy_source_id(path) == legacy_source_id(path)
        assert legacy_media_id(path) == legacy_media_id(path)
        assert legacy_track_id(path) == legacy_track_id(path)

    def test_legacy_families_are_distinct(self) -> None:
        path = "/Music/A/song.flac"
        ids = {legacy_source_id(path), legacy_media_id(path), legacy_track_id(path)}
        assert len(ids) == 3

    def test_legacy_track_id_matches_uuid5_reference(self) -> None:
        path = "/Music/A/song.flac"
        expected = str(
            uuid.uuid5(uuid.UUID(_PINNED_NAMESPACES[2]), f"legacy-track::{path}")
        )
        assert legacy_track_id(path) == expected

    def test_namespaces_are_pinned(self) -> None:
        # Regression: the fixed project namespaces must never change.
        import michi.domain.library_catalog as catalog

        assert str(catalog._MICHI_LEGACY_SOURCE_NS) == _PINNED_NAMESPACES[0]
        assert str(catalog._MICHI_LEGACY_MEDIA_NS) == _PINNED_NAMESPACES[1]
        assert str(catalog._MICHI_LEGACY_TRACK_NS) == _PINNED_NAMESPACES[2]

    def test_legacy_ids_are_migration_only_by_documentation(self) -> None:
        # The legacy helpers must not be the path the future scan algorithm
        # uses: new-id factories are the canonical allocation path.
        assert new_track_id() != legacy_track_id("/Music/A/song.flac")


class TestCatalogRecords:
    def test_library_source_defaults(self) -> None:
        source = LibrarySource(
            library_source_id=new_library_source_id(),
            display_name="Local Music",
            root_path="/Music",
        )
        assert source.enabled is True
        assert source.lifecycle is SourceLifecycle.ACTIVE

    def test_media_file_record_unresolved_legacy_shape(self) -> None:
        record = MediaFileRecord(
            media_file_id=new_media_file_id(),
            library_source_id=None,
            relative_path=None,
            last_known_path="/old/Music/gone.flac",
        )
        assert record.library_source_id is None
        assert record.relative_path is None
        assert record.availability is MediaAvailability.UNKNOWN

    def test_track_record_binds_track_to_media(self) -> None:
        media_id = new_media_file_id()
        track = TrackRecord(track_id=new_track_id(), media_file_id=media_id)
        assert track.media_file_id == media_id

    def test_records_are_frozen(self) -> None:
        with pytest.raises((AttributeError, Exception)):
            record = TrackRecord(
                track_id=new_track_id(), media_file_id=new_media_file_id()
            )
            record.track_id = "other"  # type: ignore[misc]


class TestRelativePathValidation:
    def test_accepts_posix_relative_path(self) -> None:
        assert validate_relative_media_path("Album/Song.flac") == "Album/Song.flac"

    def test_posix_backslash_is_a_literal_filename_character(self) -> None:
        # PurePosixPath semantics: backslash is NOT a separator on POSIX.
        assert validate_relative_media_path("Album\\Song.flac") == "Album\\Song.flac"

    @pytest.mark.parametrize(
        "raw",
        [
            "/absolute/path.flac",
            "a/../escape.flac",
            "../escape.flac",
            "",
            ".",
            "a/../../up.flac",
        ],
    )
    def test_rejects_unsafe_paths(self, raw: str) -> None:
        with pytest.raises(ValueError):
            validate_relative_media_path(raw)


class TestTypeAliases:
    def test_semantic_aliases_are_distinct_names_for_str(self) -> None:
        # NewType aliases: distinct semantic names, plain str at runtime.
        assert TrackId is not MediaFileId
        assert MediaFileId is not LibrarySourceId
        assert TrackId("x") == "x"
