from pathlib import Path

import pytest

from michi.application.settings_service import SettingsService
from michi.domain.library import TrackRef, build_music_model
from michi.domain.settings import (
    GalleryViewPreferences,
    LibraryViewPreferences,
    SettingsState,
    library_view_preferences_from_json,
    library_view_preferences_to_json,
)
from michi.infrastructure.sqlite_settings import SQLiteSettingsRepository


class MemorySettingsRepository:
    def __init__(self, state: SettingsState | None = None) -> None:
        self.snapshot = state or SettingsState()
        self.fail = False

    def load(self) -> SettingsState:
        return self.snapshot

    def save(self, state: SettingsState) -> None:
        if self.fail:
            raise OSError("persistence unavailable")
        self.snapshot = state


def test_library_view_preferences_round_trip_all_six_views() -> None:
    expected = LibraryViewPreferences(
        active_mode="vinyl",
        sort_mode="year",
        sort_descending=True,
        filter_mode="hires",
        gallery=GalleryViewPreferences(artwork_size="large", spacing="airy"),
    )
    decoded, malformed = library_view_preferences_from_json(
        library_view_preferences_to_json(expected)
    )
    assert malformed is False
    assert decoded == expected


def test_library_view_preferences_isolate_a_malformed_field() -> None:
    raw = library_view_preferences_to_json(LibraryViewPreferences()).replace(
        '"artworkSize":"medium"', '"artworkSize":"enormous"'
    )
    decoded, malformed = library_view_preferences_from_json(raw)
    assert malformed is True
    assert decoded.gallery.artwork_size == "medium"
    assert decoded.flow.visible_albums == "auto"
    assert decoded.studio_list.format_column is True


def test_library_view_preferences_rollback_on_save_failure() -> None:
    repo = MemorySettingsRepository()
    service = SettingsService(repo)
    original = service.state.library_views
    repo.fail = True
    changed = LibraryViewPreferences(active_mode="cover")
    with pytest.raises(OSError, match="persistence unavailable"):
        service.set_library_view_preferences(changed)
    assert service.state.library_views == original


def test_library_view_preferences_survive_sqlite_restart(tmp_path: Path) -> None:
    db_path = tmp_path / "michi.db"
    repo = SQLiteSettingsRepository(db_path)
    expected = LibraryViewPreferences(active_mode="timeline", filter_mode="artwork")
    repo.save(SettingsState(library_views=expected))
    assert SQLiteSettingsRepository(db_path).load().library_views == expected


def test_album_technical_facts_are_structured_not_parsed_from_labels() -> None:
    tracks = [
        TrackRef(
            Path("/music/a.flac"),
            title="A",
            artist="Artist",
            album="Album",
            codec="FLAC",
            sample_rate_hz=96_000,
            bit_depth=24,
            channels=2,
        ),
        TrackRef(
            Path("/music/b.flac"),
            title="B",
            artist="Artist",
            album="Album",
            codec="FLAC",
            sample_rate_hz=44_100,
            bit_depth=16,
            channels=2,
        ),
    ]
    album = build_music_model(tracks).albums[0]
    assert album.codecs == ("FLAC",)
    assert album.max_sample_rate_hz == 96_000
    assert album.max_bit_depth == 24
    assert album.contains_high_resolution is True
    assert album.technical_summary == "Mixed formats"


def test_library_qml_truth_contracts_are_explicit() -> None:
    root = Path(__file__).parents[1] / "src/michi/presentation/qml"
    card = (root / "media/AlbumCard.qml").read_text()
    grid = (root / "views/AlbumGridView.qml").read_text()
    toolbar = (root / "views/LibraryToolbar.qml").read_text()
    popup = (root / "views/LibraryViewOptionsPopup.qml").read_text()
    header = (root / "views/LibraryHeader.qml").read_text()
    albums = (root / "views/AlbumsView.qml").read_text()

    assert "signal playRequested()" in card
    assert "onPlayRequested: library.play_album" in grid
    assert "onSingleTapped:" in card and "root.selectedRequested()" in card
    assert "exclusiveSignals: TapHandler.SingleTap | TapHandler.DoubleTap" in card
    assert "onDoubleTapped:" in card and "root.openRequested()" in card
    assert 'objectName: "stableLibrarySearchPane"' in toolbar
    assert "SplitView" not in toolbar
    assert 'root.albumMode !== "timeline"' in popup
    assert 'iconName: "view-options"' in header
    assert 'iconName: "sliders"' not in header
    assert "containsHighResolution" in albums
    filter_body = albums.split("function albumMatchesFilter", 1)[1].split("}", 1)[0]
    assert "technicalSummary" not in filter_body
