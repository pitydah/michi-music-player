from ui_qml_bridge.route_registry_bridge import RouteRegistryBridge
from ui_qml_bridge.route_registry import get_sidebar_sections


class TestRouteRegistryBridge:
    def test_create(self):
        bridge = RouteRegistryBridge()
        assert bridge is not None

    def test_premium_sidebar_structure(self):
        sections, fixed = get_sidebar_sections()
        assert [section["route"] for section in sections] == [
            "home",
            "library",
            "mix",
            "streaming",
            "playlists",
            "connections",
            "audio_lab",
            "home_audio",
            "michi_ai",
            "sync",
        ]
        assert [item["route"] for item in fixed] == ["settings"]
        assert {
            section["route"]: [child["route"] for child in section["children"]]
            for section in sections
            if section["children"]
        } == {
            "library": [
                "library.songs",
                "library.albums",
                "library.artists",
                "library.folders",
            ],
            "streaming": ["streaming.radio"],
            "connections": ["connections.micro_server"],
            "audio_lab": [
                "audio_lab.analysis",
                "audio_lab.processing",
                "audio_lab.metadata",
                "audio_lab.capture",
                "audio_lab.library_health",
            ],
            "home_audio": [
                "home_audio.stream",
                "home_audio.rooms",
                "home_audio.distribution",
            ],
            "sync": ["sync.mobile"],
        }

    def test_removed_chain_planner_is_not_visible_in_sidebar(self):
        from ui_qml_bridge.route_registry import ROUTES

        route = ROUTES["home_audio.chain_planner"]

        assert route["sidebar_visible"] is False
        assert route["status"] == "removed"

    def test_planned_routes_are_hidden_from_sidebar(self):
        """Planned/configuration_required routes have no real functionality
        and must not clutter the sidebar."""
        from ui_qml_bridge.route_registry import ROUTES

        hidden = [
            "streaming.podcasts",
            "connections.big_server",
            "connections.navidrome",
            "connections.jellyfin",
            "connections.home_assistant",
            "sync.portable_players",
            "sync.plans",
            "sync.history",
        ]
        for route_key in hidden:
            assert ROUTES[route_key]["sidebar_visible"] is False, (
                f"{route_key} should be hidden from the sidebar"
            )
