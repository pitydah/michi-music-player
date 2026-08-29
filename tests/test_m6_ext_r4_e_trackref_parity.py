"""M6-EXT-R4-E — TrackRef metadata-carrier parity + stable identity fields."""

from dataclasses import asdict
from pathlib import Path

from michi.domain.library import TrackMetadata, TrackRef
from michi.domain.library_catalog import MediaAvailability


def _full_metadata() -> TrackMetadata:
    return TrackMetadata(
        title="Title",
        artist="Artist",
        album="Album",
        duration_ms=123456,
        genre="Jazz",
        year=1959,
        album_artist="Album Artist",
        track_number=2,
        track_total=9,
        disc_number=1,
        disc_total=2,
        composer="Composer",
        date="1959-08-17",
        compilation=True,
        sort_title="title",
        sort_artist="artist",
        sort_album="album",
        sort_album_artist="album artist",
        codec="FLAC",
        container="flac",
        sample_rate_hz=96000,
        bit_depth=24,
        channels=2,
        bitrate_bps=0,
        file_size=42_000_000,
    )


class TestMetadataParity:
    def test_trackref_carries_every_metadata_field_unchanged(self) -> None:
        from michi.application.library_service import LibraryService

        service = LibraryService(scanner=None)  # type: ignore[arg-type]
        ref = service._trackref_from_metadata(Path("/a/song.flac"), _full_metadata())

        # Every TrackMetadata field must survive into TrackRef unchanged.
        meta = asdict(_full_metadata())
        for name, expected in meta.items():
            assert getattr(ref, name) == expected, name

    def test_identity_fields_default_empty_for_legacy(self) -> None:
        ref = TrackRef(file_path=Path("/a.flac"))
        assert ref.track_id == ""
        assert ref.media_file_id == ""
        assert ref.library_source_id == ""

    def test_identity_fields_populated_via_projection(self) -> None:
        from michi.application.library_service import LibraryService

        service = LibraryService(scanner=None)  # type: ignore[arg-type]
        ref = service._trackref_from_metadata(
            Path("/a/song.flac"),
            _full_metadata(),
            track_id="T1",
            media_file_id="M1",
            library_source_id="S1",
        )
        assert ref.track_id == "T1"
        assert ref.media_file_id == "M1"
        assert ref.library_source_id == "S1"

    def test_availability_is_observable_state_not_path(self) -> None:
        # A non-empty path with MISSING availability must never imply playable.
        ref = TrackRef(
            file_path=Path("/gone.flac"),
            availability=MediaAvailability.MISSING,
        )
        assert ref.file_path
        assert ref.availability is MediaAvailability.MISSING


class TestLegacyConstructionCompat:
    def test_positional_construction_still_works(self) -> None:
        # Legacy code constructs TrackRef(file_path=...) with keywords; the
        # new identity fields are all defaulted so nothing breaks.
        ref = TrackRef(Path("/a.flac"), "Display")
        assert ref.display_name == "Display"
        assert ref.track_id == ""

    def test_metadata_parity_does_not_change_equality_of_legacy_records(self) -> None:
        first = TrackRef(Path("/a.flac"), title="A")
        second = TrackRef(Path("/a.flac"), title="A")
        assert first == second
