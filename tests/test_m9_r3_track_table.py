"""M9-R3 P1 gates for canonical track facts and shared table geometry."""

from pathlib import Path

import pytest

from michi.application.library_format import normalize_track_format
from michi.application.library_track_query import (
    LibraryAlbumQueryService,
    LibraryTrackQueryService,
)
from michi.domain.library import AlbumRef, TrackRef
from michi.presentation.library_bridge import LibraryBridge


@pytest.mark.parametrize(
    ("codec", "container", "path", "format_key", "label"),
    [
        ("FLAC", "FLAC", "a.flac", "flac", "FLAC"),
        ("MPEG Layer III", "MP3", "a.mp3", "mp3", "MP3"),
        ("AAC LC", "M4A", "a.m4a", "aac", "AAC"),
        ("ALAC", "M4A", "a.m4a", "alac", "ALAC"),
        ("PCM", "WAV", "a.wav", "wav", "WAV"),
        ("PCM", "AIFF", "a.aiff", "aiff", "AIFF"),
        ("PCM", "AIF", "a.aif", "aif", "AIF"),
        ("", "M4A", "a.m4a", "m4a", "M4A"),
        ("Vorbis", "OGG", "a.ogg", "ogg", "OGG"),
        ("Opus", "OGG", "a.opus", "opus", "OPUS"),
        ("WMA", "ASF", "a.wma", "wma", "WMA"),
        ("Monkey's Audio", "APE", "a.ape", "ape", "APE"),
        ("WavPack", "WavPack", "a.wv", "wavpack", "WV"),
        ("DSD", "DSF", "a.dsf", "dsf", "DSF"),
        ("DSD", "DFF", "a.dff", "dff", "DFF"),
        ("", "", "a.mystery", "unknown", "UNKNOWN"),
    ],
)
def test_format_taxonomy_uses_codec_container_then_suffix(
    codec, container, path, format_key, label
) -> None:
    facts = normalize_track_format(codec, container, Path(path))
    assert facts.key == format_key
    assert facts.label == label


@pytest.mark.parametrize(
    ("sample_rate", "expected"),
    [(2_822_400, "DSD64"), (5_644_800, "DSD128"), (11_289_600, "DSD256")],
)
def test_dsd_rate_is_derived_only_from_dsd_codec_fact(sample_rate, expected) -> None:
    facts = normalize_track_format("DSD", "DSF", Path("a.dsf"), sample_rate)
    assert facts.dsd_rate == expected
    assert (
        normalize_track_format("PCM", "WAV", Path("a.wav"), sample_rate).dsd_rate == ""
    )


def test_bridge_projects_canonical_identity_and_complete_technical_facts() -> None:
    ref = TrackRef(
        file_path=Path("/music/Depeche Mode/Spirit/01.flac"),
        title="Policy of Truth",
        artist="Depeche Mode",
        album="Spirit",
        album_artist="Depeche Mode",
        genre="Electronic",
        composer="Martin Gore",
        year=2017,
        track_number=1,
        disc_number=1,
        codec="FLAC",
        container="FLAC",
        sample_rate_hz=96_000,
        bit_depth=24,
        bitrate_bps=2_304_000,
        channels=2,
        file_size=42_000_000,
    )

    row = LibraryBridge._track_row(ref)

    # M6-EXT-R4-F: pre-catalog records project the documented legacy-path
    # fallback; migrated records project the stable TrackId.
    assert row["trackId"] == f"legacy-path::{ref.file_path}"
    assert row["path"] == str(ref.file_path)
    assert row["albumKey"]
    assert row["artistKey"] == "depeche mode"
    assert row["formatKey"] == "flac"
    assert row["formatLabel"] == "FLAC"
    assert row["container"] == "FLAC"
    assert row["bitrateBps"] == 2_304_000
    assert row["genre"] == "Electronic"
    assert row["composer"] == "Martin Gore"


def test_track_sort_query_is_application_owned_and_deterministic() -> None:
    query = LibraryTrackQueryService()
    refs = [
        TrackRef(Path("/b.flac"), title="Beta", artist="Zulu", album="One"),
        TrackRef(Path("/a.flac"), title="Alpha", artist="Alpha", album="Two"),
    ]

    query.set_sort("title")
    assert [ref.title for ref in query.sort_tracks(refs)] == ["Alpha", "Beta"]
    query.set_sort("title")
    assert [ref.title for ref in query.sort_tracks(refs)] == ["Beta", "Alpha"]
    query.set_sort("artist")
    assert query.state.column == "artist"
    assert query.state.descending is False


def test_album_query_owns_filtering_and_sorting_without_quality_inference() -> None:
    query = LibraryAlbumQueryService()
    albums = [
        AlbumRef("b", "Beta", "Zulu", 2, 200, has_artwork=False, year=2020),
        AlbumRef("a", "Alpha", "Alpha", 1, 100, has_artwork=True, year=0),
    ]

    assert [album.title for album in query.project(albums)] == ["Alpha", "Beta"]
    assert query.set_filter_mode("artwork") is True
    assert [album.key for album in query.project(albums)] == ["a"]
    assert query.set_filter_mode("hires") is False
    assert query.set_filter_mode("all") is True
    assert query.set_sort_mode("artist") is True
    assert [album.artist for album in query.project(albums)] == ["Alpha", "Zulu"]


def test_column_state_is_the_single_geometry_authority() -> None:
    state = Path(
        "src/michi/presentation/qml/theme/LibraryTrackColumnState.qml"
    ).read_text()
    header = Path(
        "src/michi/presentation/qml/media/ResizableTrackHeader.qml"
    ).read_text()
    row = Path("src/michi/presentation/qml/media/TrackRow.qml").read_text()
    table = Path("src/michi/presentation/qml/media/MichiTrackTable.qml").read_text()

    assert "pragma Singleton" in state
    for column in (
        "artwork",
        "title",
        "artist",
        "album",
        "format",
        "sampleRate",
        "bitDepth",
        "dsdRate",
        "bitrate",
        "channels",
        "fileSize",
        "genre",
        "composer",
        "year",
        "duration",
        "actions",
    ):
        assert f"property real {column}Width" in state
        assert f"property bool {column}Visible" in state
    # SEMANTIC INTEGRATION: la geometría de columnas de main vive en el
    # MichiTrackTable/header premium (la tabla de la rama ya no es la
    # autoridad para las vistas primarias).
    assert "LibraryTrackColumnState" in table
    resize_cell = Path(
        "src/michi/presentation/qml/media/ResizableHeaderCell.qml"
    ).read_text()
    assert "Qt.SplitHCursor" in resize_cell
    assert "Reset Column Widths" in header
    assert "Restore Default Columns" in header


def test_shared_track_table_is_used_by_primary_library_track_views() -> None:
    views = Path("src/michi/presentation/qml/views")
    # SEMANTIC INTEGRATION: las vistas primarias de main usan TrackRow
    # (su componente de tabla) — no la MichiTrackTable de la rama.
    for name in (
        "SongsView.qml",
        "FavoritesView.qml",
        "HistoryView.qml",
        "RecentlyAddedView.qml",
    ):
        text = (views / name).read_text()
        assert "TrackRow" in text or "MichiTrackTable" in text


def test_format_badge_never_claims_quality_or_output_state() -> None:
    badge = Path("src/michi/presentation/qml/media/MichiFormatBadge.qml").read_text()
    assert "property string formatKey" in badge
    assert "property string displayLabel" in badge
    for forbidden in ("Hi-Res", "Bit Perfect", "bitPerfect", "outputState"):
        assert forbidden not in badge
