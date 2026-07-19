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
        assert fixed == []
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
            "streaming": ["streaming.radio", "streaming.podcasts"],
            "connections": [
                "connections.micro_server",
                "connections.big_server",
                "connections.navidrome",
                "connections.jellyfin",
                "connections.home_assistant",
            ],
        }
