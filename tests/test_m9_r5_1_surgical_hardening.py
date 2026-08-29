"""M9-R5.1 surgical Library and playback UX hardening contracts."""

from pathlib import Path

QML = Path("src/michi/presentation/qml")


def _qml(relative: str) -> str:
    return (QML / relative).read_text(encoding="utf-8")


def test_toolbar_has_no_manual_utility_pane_budget() -> None:
    toolbar = _qml("views/LibraryToolbar.qml")
    split = _qml("controls/MichiSplitButton.qml")

    assert "id: utilityPane" not in toolbar
    assert "scanButton.implicitWidth" not in toolbar
    assert 'objectName: "librarySearchResizeHandle"' in toolbar
    assert 'objectName: "resizableLibrarySearchPane"' in toolbar
    assert 'objectName: "libraryScanSplitButton"' in toolbar
    assert "MichiSemanticColors.controlSurface" in split
    assert 'secondaryIconName: "folder"' not in split


def test_track_resize_uses_persisted_baseline_and_neighbor_compensation() -> None:
    table = _qml("media/MichiTrackTable.qml")
    header = _qml("media/ResizableTrackHeader.qml")
    cell = _qml("media/ResizableHeaderCell.qml")
    state = _qml("theme/LibraryTrackColumnState.qml")

    assert "resizeBaseWidth" in cell
    assert "LibraryTrackColumnState.titleWidth" in header
    assert "resizeWithNeighbor" in state
    assert "titleResizeNeighbor" in header
    assert "Math.max(LibraryTrackColumnState.titleWidth" not in table
    assert "? LibraryTrackColumnState.titleWidth : 0" in table
    assert "resizable: false" in header


def test_unknown_duration_has_explicit_timeline_state_without_geometry_change() -> None:
    now_playing = _qml("player/NowPlayingBar.qml")

    assert "readonly property bool durationKnown" in now_playing
    assert "to: root.durationKnown ? root.duration : 1" in now_playing
    assert "value: root.durationKnown ? Math.min(root.position, to) : 0" in now_playing
    assert "enabled: root.durationKnown" in now_playing
    assert 'root.durationKnown ? formatTime(root.duration) : qsTr("—")' in now_playing


def test_engine_surfaces_consume_bridge_selection_projection() -> None:
    popup = _qml("player/AudioEnginePopup.qml")
    settings = _qml("views/AudioEngineSettingsSection.qml")

    assert "enabled: row.modelData.canSelectNow" in popup
    assert "enabled: card.modelData.canSelectNow" in settings
    assert "root.engineSwitchReady" not in popup
    assert 'root.switchingTo === ""' not in settings


def test_detail_actions_are_signals_not_writable_binding_relays() -> None:
    album = _qml("views/AlbumDetailView.qml")
    artist = _qml("views/ArtistDetailView.qml")
    albums = _qml("views/AlbumsView.qml")
    artists = _qml("views/ArtistsView.qml")

    # P1-A: detail playlist intents are TrackId-native.
    assert "signal addToPlaylistRequested(string trackId)" in album
    assert "signal addToPlaylistRequested(string trackId)" in artist
    assert "onAddTargetPathChanged" not in albums
    assert "onAddTargetPathChanged" not in artists
    assert "function formatDuration" not in album
    assert "function formatFileSize" not in album
    assert "MichiFormat.formatHoursMinutes" in album
    assert "MichiFormat.formatFileSize" in album
    assert "root.height * 0.67" not in artist
    assert "artistGrid.forceActiveFocus()" in artists
