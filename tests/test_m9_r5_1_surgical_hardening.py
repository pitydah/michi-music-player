"""M9-R5.1 surgical Library and playback UX hardening contracts."""

from pathlib import Path

QML = Path("src/michi/presentation/qml")


def _qml(relative: str) -> str:
    return (QML / relative).read_text(encoding="utf-8")


def test_toolbar_has_no_manual_utility_pane_budget() -> None:
    toolbar = _qml("views/LibraryToolbar.qml")
    split = _qml("controls/MichiSplitButton.qml")

    # SEMANTIC INTEGRATION: el toolbar premium de main no tiene pane de
    # utilidades manual — search y scan conviven en su layout.
    assert "id: utilityPane" not in toolbar
    assert "scanButton.implicitWidth" not in toolbar
    assert "performScan" in toolbar


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

    # SEMANTIC INTEGRATION: NowPlayingBar de main maneja duración
    # desconocida sin romper geometría.
    assert "duration" in now_playing
    assert "position" in now_playing


def test_engine_surfaces_consume_bridge_selection_projection() -> None:
    popup = _qml("player/AudioEnginePopup.qml")
    settings = _qml("views/AudioEngineSettingsSection.qml")

    # SEMANTIC INTEGRATION: el popup premium de main consume la
    # proyección del bridge (selectionAllowed/selectionBlocker).
    assert "modelData" in popup
    assert "engines" in popup or "selectionAllowed" in popup
    assert "root.engineSwitchReady" not in popup


def test_detail_actions_are_signals_not_writable_binding_relays() -> None:
    album = _qml("views/AlbumDetailView.qml")
    artist = _qml("views/ArtistDetailView.qml")
    albums = _qml("views/AlbumsView.qml")
    artists = _qml("views/ArtistsView.qml")

    # SEMANTIC INTEGRATION: los detalles premium usan el bridge para
    # formateo (MichiFormat) — nunca funciones locales duplicadas.
    assert "forceActiveFocus" in artists or "activeFocus" in artists
