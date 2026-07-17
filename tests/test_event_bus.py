from core.event_bus import EventBus


class TestEventBus:
    def test_create_and_publish(self):
        bus = EventBus()
        received = []
        bus.subscribe("test", lambda *a, **kw: received.append((a, kw)))
        bus.publish("test", 1, 2, key="val")
        assert len(received) == 1

    def test_unsubscribe(self):
        bus = EventBus()
        def handler(*a, **kw): pass
        bus.subscribe("evt", handler)
        bus.unsubscribe("evt", handler)
        assert "evt" not in bus._handlers or handler not in bus._handlers["evt"]
