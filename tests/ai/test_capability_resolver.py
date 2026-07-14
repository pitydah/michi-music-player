from __future__ import annotations

from michi_ai.v2.intent.capability_resolver import CapabilityResolver


class TestCapabilityResolver:
    def test_register_and_resolve(self):
        resolver = CapabilityResolver()
        resolver.register("playback.control", available=True)
        result = resolver.resolve("playback.control")
        assert "playback.control" in result
        assert result["playback.control"].available is True

    def test_unregistered_returns_unavailable(self):
        resolver = CapabilityResolver()
        result = resolver.resolve("nonexistent.cap")
        assert "nonexistent.cap" in result
        assert result["nonexistent.cap"].available is False

    def test_all_available_returns_true(self):
        resolver = CapabilityResolver()
        resolver.register("a", available=True)
        resolver.register("b", available=True)
        assert resolver.all_available(["a", "b"]) is True

    def test_all_available_returns_false(self):
        resolver = CapabilityResolver()
        resolver.register("a", available=True)
        resolver.register("b", available=False)
        assert resolver.all_available(["a", "b"]) is False

    def test_available_returns_only_available(self):
        resolver = CapabilityResolver()
        resolver.register("a", available=True)
        resolver.register("b", available=False)
        avail = resolver.available()
        assert "a" in avail
        assert "b" not in avail

    def test_list_all(self):
        resolver = CapabilityResolver()
        resolver.register("a", available=True)
        resolver.register("b", available=False)
        all_caps = resolver.list_all()
        assert len(all_caps) == 2

    def test_clear(self):
        resolver = CapabilityResolver()
        resolver.register("a", available=True)
        resolver.clear()
        assert len(resolver.list_all()) == 0

    def test_intent_to_capabilities_playback(self):
        caps = CapabilityResolver.intent_to_capabilities("pause")
        assert "playback.control" in caps

    def test_intent_to_capabilities_library(self):
        caps = CapabilityResolver.intent_to_capabilities("search_library")
        assert "library.search" in caps

    def test_intent_to_capabilities_mix(self):
        caps = CapabilityResolver.intent_to_capabilities("create_smart_mix")
        assert "mix.generate" in caps

    def test_intent_to_capabilities_unknown(self):
        caps = CapabilityResolver.intent_to_capabilities("nonexistent")
        assert caps == []

    def test_register_from_gateways(self):
        resolver = CapabilityResolver()
        gateways = {
            "playback": object(),
            "library": object(),
        }
        resolver.register_from_gateways(gateways)
        assert resolver.all_available("playback.control")
        assert resolver.all_available("library.search")
        assert not resolver.all_available("devices.read")
