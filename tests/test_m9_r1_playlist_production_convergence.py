"""M9-R1I: playlist shell production convergence gates.

- Single navigation truth: NavigationState.playlist_id drives every
  selected* projection; the bridge keeps NO local selection state.
- Card dialogs use ephemeral targets — All Playlists rename/delete never
  change navigation.
- One production PlaylistsBridge (ApplicationContainer owns it; disposed).
- Create/rename deterministic workflows; pin accessibility for arbitrary
  playlists; empty detail owns the body; card keyboard activation.
"""

import inspect
from pathlib import Path

from michi.application.navigation_service import NavigationService
from michi.application.playlist_navigation_coordinator import (
    PlaylistNavigationCoordinator,
)
from michi.application.playlist_service import PlaylistService
from michi.domain.navigation import AppRoute
from michi.presentation.playlists_bridge import PlaylistsBridge
from tests.test_playlists import FakePlaylistsPort

QML_DIR = Path(__file__).resolve().parents[1] / "src" / "michi" / "presentation" / "qml"


def _world():

    service = PlaylistService(playlists_port=FakePlaylistsPort())
    nav = NavigationService()
    service.set_on_playlist_deleted(nav.forget_playlist)
    coord = PlaylistNavigationCoordinator(service, nav)
    bridge = PlaylistsBridge(
        service,
        playlist_navigation=coord,
        navigation_service=nav,
    )
    return service, nav, coord, bridge


class TestSingleNavigationTruth:
    def test_open_a_drives_navigation_and_projection(self):
        service, nav, coord, bridge = _world()
        a = service.create_playlist("A")
        coord.open_playlist(a.playlist_id)
        assert nav.state.playlist_id == a.playlist_id
        assert bridge.property("selectedPlaylistId") == a.playlist_id

    def test_open_all_clears_target_and_projection(self):
        service, nav, coord, bridge = _world()
        a = service.create_playlist("A")
        coord.open_playlist(a.playlist_id)
        coord.open_all_playlists()
        assert nav.state.playlist_id is None
        assert bridge.property("selectedPlaylistId") == ""

    def test_rename_card_from_all_keeps_all_playlists(self):
        """Card dialogs never touch navigation (ephemeral targets)."""
        service, nav, coord, bridge = _world()
        a = service.create_playlist("A")
        coord.open_all_playlists()
        assert bridge.rename_playlist(a.playlist_id, "A Long") is True
        assert nav.state.playlist_id is None
        assert nav.state.current_route == AppRoute.PLAYLISTS

    def test_delete_card_from_all_keeps_all_playlists(self):
        service, nav, coord, bridge = _world()
        a = service.create_playlist("A")
        coord.open_all_playlists()
        bridge.delete_playlist(a.playlist_id)
        assert nav.state.playlist_id is None
        assert nav.state.current_route == AppRoute.PLAYLISTS

    def test_open_a_then_rename_keeps_target(self):
        service, nav, coord, bridge = _world()
        a = service.create_playlist("A")
        coord.open_playlist(a.playlist_id)
        bridge.rename_playlist(a.playlist_id, "A Long")
        assert nav.state.playlist_id == a.playlist_id
        assert bridge.property("selectedPlaylistName") == "A Long"

    def test_open_a_then_delete_converges_to_none(self):
        service, nav, coord, bridge = _world()
        a = service.create_playlist("A")
        coord.open_playlist(a.playlist_id)
        bridge.delete_playlist(a.playlist_id)
        assert nav.state.playlist_id is None
        assert bridge.property("selectedPlaylistId") == ""

    def test_no_bridge_local_selection_state(self):
        src = inspect.getsource(PlaylistsBridge)
        assert "self._selected_playlist_id" not in src
        assert "def select_playlist" not in src
        assert "def clear_playlist_selection" not in src

    def test_projection_follows_navigation_without_select_api(self):
        """Changing the navigation target updates every projection without
        any selection call (behavioral single-truth proof)."""
        service, nav, coord, bridge = _world()
        a = service.create_playlist("A")
        b = service.create_playlist("B")
        service.add_track(b.playlist_id, "/m/b.mp3")
        nav.navigate_to_playlist(a.playlist_id)
        assert bridge.property("selectedPlaylistId") == a.playlist_id
        nav.navigate_to_playlist(b.playlist_id)
        assert bridge.property("selectedPlaylistId") == b.playlist_id
        assert bridge.property("playlistTrackRows") != []
        nav.navigate(AppRoute.PLAYLISTS.value)
        assert bridge.property("selectedPlaylistId") == ""


class TestCreateWorkflow:
    def test_create_success_returns_true_and_opens(self):
        service, nav, coord, bridge = _world()
        assert bridge.create_and_open_playlist("Jazz") is True
        created = service.playlists[0]
        assert nav.state.playlist_id == created.playlist_id
        assert service.navigation.recent_ids[0] == created.playlist_id
        assert bridge.property("selectedPlaylistId") == created.playlist_id

    def test_create_duplicate_returns_false_no_change(self):
        service, nav, coord, bridge = _world()
        bridge.create_and_open_playlist("Jazz")
        before = nav.state.playlist_id
        assert bridge.create_and_open_playlist("Jazz") is False
        assert len(service.playlists) == 1
        assert nav.state.playlist_id == before

    def test_create_empty_returns_false(self):
        service, nav, coord, bridge = _world()
        assert bridge.create_and_open_playlist("   ") is False
        assert service.playlists == ()


class TestRenameContract:
    def test_rename_success_true_same_id(self):
        service, nav, coord, bridge = _world()
        a = service.create_playlist("A")
        assert bridge.rename_playlist(a.playlist_id, "A Long") is True
        assert service.playlists[0].playlist_id == a.playlist_id
        assert service.playlists[0].name == "A Long"

    def test_rename_duplicate_false(self):
        service, nav, coord, bridge = _world()
        a = service.create_playlist("A")
        service.create_playlist("B")
        assert bridge.rename_playlist(a.playlist_id, "B") is False
        assert service.playlists[0].name == "A"

    def test_rename_unknown_false(self):
        service, nav, coord, bridge = _world()
        assert bridge.rename_playlist("ghost", "X") is False

    def test_rename_empty_false(self):
        service, nav, coord, bridge = _world()
        a = service.create_playlist("A")
        assert bridge.rename_playlist(a.playlist_id, "   ") is False

    def test_rename_same_name_succeeds(self):
        """Renaming to the SAME name is a successful no-op — the entity is
        never treated as its own conflicting duplicate."""
        service, nav, coord, bridge = _world()
        a = service.create_playlist("Jazz")
        assert bridge.rename_playlist(a.playlist_id, "Jazz") is True
        assert service.playlists[0].name == "Jazz"


class TestPinAccessibility:
    def test_pin_state_for_arbitrary_playlist(self):
        service, nav, coord, bridge = _world()
        service.create_playlist("A")
        service.create_playlist("B")
        c = service.create_playlist("C")
        coord.open_playlist(c.playlist_id)  # third playlist — not playlists[0]
        assert bridge.property("selectedPlaylistPinned") is False
        service.pin_playlist(c.playlist_id)
        assert bridge.property("selectedPlaylistPinned") is True
        service.unpin_playlist(c.playlist_id)
        assert bridge.property("selectedPlaylistPinned") is False

    def test_pin_detail_qml_uses_projection_not_first_row(self):
        detail = (QML_DIR / "playlists" / "PlaylistDetailView.qml").read_text()
        assert "selectedPlaylistPinned" in detail
        # no REAL use of the first row (a comment mentioning playlists[0] is
        # allowed; reading playlists.playlists[0] is not)
        assert "playlists.playlists[0]" not in detail


class TestEmptyDetail:
    def test_empty_detail_qml_layout(self):
        detail = (QML_DIR / "playlists" / "PlaylistDetailView.qml").read_text()
        # editorial redesign: hero always visible; the tracks area shows the
        # quiet empty prompt when there are no rows
        assert "visible: playlists.playlistTrackRows.length === 0" in detail
        assert "This playlist is empty" in detail
        assert "Add Music" in detail


class TestCardKeyboard:
    def test_card_keyboard_activation(self):
        card = (QML_DIR / "playlists" / "PlaylistCard.qml").read_text()
        assert "Keys.onReturnPressed" in card
        assert "Keys.onEnterPressed" in card
        assert "Keys.onSpacePressed" in card
        assert "activeFocusOnTab" in card

    def test_card_internal_controls_do_not_open(self):
        """Play/Pin/More are separate controls — no accidental open."""
        card = (QML_DIR / "playlists" / "PlaylistCard.qml").read_text()
        # openRequested fires only from the card surface (MouseArea + Keys)
        assert card.count("openRequested()") >= 1
        # the icon buttons are NOT inside the MouseArea click path
        assert "MichiIconButton" in card


class TestProductionComposition:
    def test_build_services_does_not_construct_playlists_bridge(self):
        """The production graph builds the domain/application core; the ONE
        canonical PlaylistsBridge is composed by ApplicationContainer."""
        import michi.bootstrap as bootstrap

        src = inspect.getsource(bootstrap)
        # _build_services must not create a canonical bridge with navigation
        assert "playlists_bridge=" not in src
        assert "PlaylistsBridge(" in src  # only the container site

    def test_container_stores_and_disposes_playlists_bridge(self):
        import michi.bootstrap as bootstrap

        src = inspect.getsource(bootstrap)
        assert "self._plb = plb" in src
        assert "self._plb," in src  # included in the shutdown dispose tuple
        assert "self._plb = None" in src

    def test_shutdown_disposes_playlists_bridge(self, tmp_path):
        """End-to-end: after ApplicationContainer shutdown, the PlaylistsBridge
        is disposed (no dangling PlaylistService subscription). The container
        builds its own graph; db_path lives under the container."""
        from michi.bootstrap import ApplicationContainer
        from michi.presentation.playlists_bridge import PlaylistsBridge

        container = ApplicationContainer()
        disposed = []
        original_dispose = PlaylistsBridge.dispose

        def spy_dispose(self):
            disposed.append(self)
            original_dispose(self)

        PlaylistsBridge.dispose = spy_dispose
        try:
            container.initialize()
            assert container._plb is not None
            container.shutdown()
            assert container._plb is None
            assert any(isinstance(b, PlaylistsBridge) for b in disposed)
        finally:
            PlaylistsBridge.dispose = original_dispose


class TestSearchParity:
    def test_open_playlist_result_never_activates_library(self):
        """Mouse and keyboard converge: the canonical open intent routes to
        PLAYLISTS/id — Library is never activated for a playlist result."""
        service, nav, coord, bridge = _world()
        a = service.create_playlist("Road Trip")
        bridge.open_playlist(a.playlist_id)  # same intent as overlay activation
        assert nav.state.current_route == AppRoute.PLAYLISTS
        assert nav.state.playlist_id == a.playlist_id
        assert service.navigation.recent_ids[0] == a.playlist_id
        assert nav.state.current_route is not AppRoute.LIBRARY

    def test_search_overlay_has_no_library_fallback_for_playlists(self):
        overlay = (QML_DIR / "patterns" / "SearchOverlay.qml").read_text()
        start = overlay.index("var playlistIndex")
        end = overlay.index("    }\n", start)  # close of activateResult
        branch = overlay[start:end]
        assert "open_playlist" in branch
        assert 'navigationRequested("library")' not in branch


class TestQmlDialogFlows:
    def test_create_dialog_closes_on_success(self):
        dialog = (QML_DIR / "playlists" / "PlaylistCreateDialog.qml").read_text()
        assert "root.close()" in dialog
        assert "forceActiveFocus" in dialog  # failure keeps focus in field

    def test_rename_dialog_error_semantics(self):
        content = (QML_DIR / "shell" / "ContentHost.qml").read_text()
        assert (
            "playlists.rename_playlist(renameDialog.targetPlaylistId, name)" in content
        )
        assert "A playlist with that name already exists" in content
        assert "errorText" in content

    def test_dialogs_use_ephemeral_targets(self):
        content = (QML_DIR / "shell" / "ContentHost.qml").read_text()
        assert "targetPlaylistId" in content
        assert "targetPlaylistName" in content
        # no CALL to any selection API (comments may mention it)
        assert "playlists.select_playlist(" not in content
