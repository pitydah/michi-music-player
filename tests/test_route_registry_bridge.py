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
            "ecosystem",
            "audio_lab",
            "michi_ai",
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
                "playlists",
            ],
            "streaming": ["streaming.radio"],
            "audio_lab": [
                "audio_lab.analysis",
                "audio_lab.processing",
                "audio_lab.metadata",
                "audio_lab.capture",
                "audio_lab.library_health",
            ],
        }

    def test_removed_chain_planner_is_not_visible_in_sidebar(self):
        from ui_qml_bridge.route_registry import ROUTES

        route = ROUTES["home_audio.chain_planner"]

        assert route["sidebar_visible"] is False
        assert route["status"] == "removed"

    def test_ecosystem_hub_groups_ecosystem_domains(self):
        """Ecosistema is a functional hub; its domains stay navigable
        through hub cards but out of the sidebar."""
        from ui_qml_bridge.route_registry import ROUTES

        hub = ROUTES["ecosystem"]
        assert hub["status"] == "functional"
        assert hub["source"].endswith("EcosystemHubPage.qml")
        assert hub["sidebar_visible"] is True

        for route_key in ("connections", "home_audio", "sync"):
            assert ROUTES[route_key]["parent"] == "ecosystem"
            assert ROUTES[route_key]["sidebar_visible"] is False, (
                f"{route_key} should be reachable via the ecosystem hub, "
                "not as a sidebar section"
            )

    def test_playlists_is_child_of_library(self):
        from ui_qml_bridge.route_registry import ROUTES

        route = ROUTES["playlists"]
        assert route["parent"] == "library"
        assert route["sidebar_group"] == "library"
        assert route["sidebar_visible"] is True

    def test_nowplaying_queue_history_stay_out_of_sidebar(self):
        from ui_qml_bridge.route_registry import ROUTES, SIDEBAR_ORDER

        for route_key in ("nowplaying", "queue", "history"):
            assert route_key not in SIDEBAR_ORDER
            assert ROUTES[route_key]["sidebar_visible"] is False

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
