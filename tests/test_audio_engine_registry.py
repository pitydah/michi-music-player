"""M11.3A: AudioEngineRegistry + provider port gates."""

import pytest

from michi.application.audio_engine_registry import (
    AudioEngineProviderPort,
    AudioEngineRegistry,
    DuplicateEngineProviderError,
)
from michi.application.ports import AudioPort
from michi.domain.audio_engine import (
    AudioEngineDescriptor,
    AudioEngineId,
)


class FakeProvider(AudioEngineProviderPort):
    def __init__(self, engine_id, available=True, reason=None, calls=None):
        self._engine_id = engine_id
        self._available = available
        self._reason = reason
        self.calls = calls if calls is not None else []

    @property
    def engine_id(self):
        return self._engine_id

    def probe(self):
        self.calls.append(f"probe:{self._engine_id.value}")
        return AudioEngineDescriptor(
            engine_id=self._engine_id,
            display_name=self._engine_id.value,
            available=self._available,
            unavailable_reason=self._reason,
        )

    def open(self):
        self.calls.append(f"open:{self._engine_id.value}")
        return None  # fake

    def close(self):
        self.calls.append(f"close:{self._engine_id.value}")


class TestRegistry:
    def test_canonical_deterministic_order(self):
        registry = AudioEngineRegistry(
            [
                FakeProvider(AudioEngineId.MPD),
                FakeProvider(AudioEngineId.QT_MULTIMEDIA),
                FakeProvider(AudioEngineId.GSTREAMER),
            ]
        )
        assert registry.engine_ids == (
            AudioEngineId.QT_MULTIMEDIA,
            AudioEngineId.GSTREAMER,
            AudioEngineId.MPD,
        )

    def test_duplicate_provider_rejected(self):
        registry = AudioEngineRegistry()
        registry.register(FakeProvider(AudioEngineId.QT_MULTIMEDIA))
        with pytest.raises(DuplicateEngineProviderError):
            registry.register(FakeProvider(AudioEngineId.QT_MULTIMEDIA))

    def test_unavailable_retains_explicit_reason(self):
        registry = AudioEngineRegistry(
            [
                FakeProvider(
                    AudioEngineId.GSTREAMER,
                    available=False,
                    reason="gi/Gst typelib no disponible",
                )
            ]
        )
        desc = registry.descriptor(AudioEngineId.GSTREAMER)
        assert desc.available is False
        assert "typelib" in desc.unavailable_reason

    def test_lookup_by_canonical_id(self):
        provider = FakeProvider(AudioEngineId.MPD)
        registry = AudioEngineRegistry([provider])
        assert registry.provider(AudioEngineId.MPD) is provider

    def test_unknown_engine_lookup_raises(self):
        registry = AudioEngineRegistry()
        with pytest.raises(KeyError):
            registry.provider(AudioEngineId.GSTREAMER)

    def test_descriptors_in_canonical_order(self):
        registry = AudioEngineRegistry(
            [
                FakeProvider(AudioEngineId.GSTREAMER),
                FakeProvider(AudioEngineId.QT_MULTIMEDIA),
                FakeProvider(AudioEngineId.MPD),
            ]
        )
        ids = [d.engine_id for d in registry.descriptors()]
        assert ids == [
            AudioEngineId.QT_MULTIMEDIA,
            AudioEngineId.GSTREAMER,
            AudioEngineId.MPD,
        ]

    def test_is_available_reflects_probe(self):
        registry = AudioEngineRegistry(
            [
                FakeProvider(AudioEngineId.QT_MULTIMEDIA, available=True),
                FakeProvider(AudioEngineId.GSTREAMER, available=False),
            ]
        )
        assert registry.is_available(AudioEngineId.QT_MULTIMEDIA) is True
        assert registry.is_available(AudioEngineId.GSTREAMER) is False


class TestActivationGates:
    def test_is_available_differs_from_can_activate(self):
        """Installed-but-not-implemented: runtime present, activation NO."""
        registry = AudioEngineRegistry(
            [
                FakeProvider(AudioEngineId.QT_MULTIMEDIA, available=True),
                # instalado pero adaptador NO implementado
                FakeProvider(AudioEngineId.GSTREAMER, available=True)
                if False
                else _UnimplementedProvider(),
            ]
        )
        assert registry.is_available(AudioEngineId.GSTREAMER) is True
        assert registry.can_activate(AudioEngineId.GSTREAMER) is False

    def test_can_activate_qt_true(self):
        from michi.infrastructure.audio_engines.providers import QtEngineProvider

        registry = AudioEngineRegistry([QtEngineProvider()])
        assert registry.can_activate(AudioEngineId.QT_MULTIMEDIA) is True

    def test_activation_blocker_reason(self):
        from michi.infrastructure.audio_engines.providers import (
            GStreamerEngineProvider,
        )

        registry = AudioEngineRegistry([GStreamerEngineProvider()])
        blocker = registry.activation_blocker(AudioEngineId.GSTREAMER)
        assert blocker is not None
        assert "M11.3C" in blocker


class _UnimplementedProvider(AudioEngineProviderPort):
    @property
    def engine_id(self):
        return AudioEngineId.GSTREAMER

    def probe(self):
        return AudioEngineDescriptor(
            engine_id=self.engine_id,
            display_name="GStreamer",
            available=True,
            implemented=False,
            implementation_reason="adapter pendiente (M11.3C)",
        )

    def open(self):
        raise NotImplementedError

    def close(self):
        pass


class TestProviderContract:
    def test_probe_must_not_activate(self):
        """probe() reports truth; it must not open/start anything."""
        calls = []
        provider = FakeProvider(AudioEngineId.QT_MULTIMEDIA, calls=calls)
        registry = AudioEngineRegistry([provider])
        registry.descriptors()
        assert calls == ["probe:qt_multimedia"]
        assert "open:" not in " ".join(calls)

    def test_open_returns_transport_port(self):
        class QtLike(AudioPort):
            def load(self, file_path): ...
            def play(self): ...
            def pause(self): ...
            def resume(self): ...
            def stop(self): ...
            def set_volume(self, value): ...
            def set_muted(self, muted): ...
            def seek(self, position_ms): ...
            def position(self):
                return 0

            def duration(self):
                return 0

            def subscribe_end_of_media(self, cb): ...
            def unsubscribe_end_of_media(self, cb): ...
            def subscribe_position_changed(self, cb): ...
            def unsubscribe_position_changed(self, cb): ...
            def subscribe_duration_changed(self, cb): ...
            def unsubscribe_duration_changed(self, cb): ...
            def subscribe_media_accepted(self, cb): ...
            def unsubscribe_media_accepted(self, cb): ...
            def subscribe_media_rejected(self, cb): ...
            def unsubscribe_media_rejected(self, cb): ...
            def subscribe_playback_state_changed(self, cb): ...
            def unsubscribe_playback_state_changed(self, cb): ...

        class Provider(AudioEngineProviderPort):
            @property
            def engine_id(self):
                return AudioEngineId.QT_MULTIMEDIA

            def probe(self):
                return AudioEngineDescriptor(
                    engine_id=self.engine_id, display_name="Qt", available=True
                )

            def open(self):
                return QtLike()

            def close(self):
                pass

        port = Provider().open()
        assert isinstance(port, AudioPort)
