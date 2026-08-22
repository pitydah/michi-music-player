"""Audio engine registry + provider port (M11.3A).

Registry owns the SET of providers (exactly one per AudioEngineId, canonical
order); it does NOT select engines and does NOT own AudioEngineState.
Providers own engine lifecycle for one concrete implementation; the AudioPort
returned by open() owns transport operations only."""

from abc import ABC, abstractmethod

from michi.application.ports import AudioPort
from michi.domain.audio_engine import AudioEngineDescriptor, AudioEngineId


class AudioEngineProviderPort(ABC):
    """One concrete engine implementation: availability probe + lifecycle."""

    @property
    @abstractmethod
    def engine_id(self) -> AudioEngineId: ...

    @abstractmethod
    def probe(self) -> AudioEngineDescriptor:
        """Truthful availability. MUST NOT start playback, mutate Queue,
        modify PlaybackState or install dependencies."""

    @abstractmethod
    def open(self) -> AudioPort:
        """Initialize the engine runtime and return its transport port."""

    @abstractmethod
    def close(self) -> None:
        """Release engine runtime resources. No engine may continue emitting
        callbacks after close()."""


class DuplicateEngineProviderError(ValueError):
    """Raised when two providers claim the same AudioEngineId."""


class AudioEngineRegistry:
    """Deterministic provider set: QT_MULTIMEDIA, GSTREAMER, MPD."""

    _CANONICAL_ORDER = (
        AudioEngineId.QT_MULTIMEDIA,
        AudioEngineId.GSTREAMER,
        AudioEngineId.MPD,
    )

    def __init__(self, providers: list[AudioEngineProviderPort] | None = None) -> None:
        self._providers: dict[AudioEngineId, AudioEngineProviderPort] = {}
        for provider in providers or ():
            self.register(provider)

    def register(self, provider: AudioEngineProviderPort) -> None:
        engine_id = provider.engine_id
        if engine_id in self._providers:
            raise DuplicateEngineProviderError(
                f"provider ya registrado para {engine_id.value}"
            )
        self._providers[engine_id] = provider

    @property
    def engine_ids(self) -> tuple[AudioEngineId, ...]:
        """Canonical deterministic order."""
        return tuple(e for e in self._CANONICAL_ORDER if e in self._providers)

    def descriptors(self) -> tuple[AudioEngineDescriptor, ...]:
        return tuple(self.provider(e).probe() for e in self.engine_ids)

    def descriptor(self, engine_id: AudioEngineId) -> AudioEngineDescriptor:
        return self.provider(engine_id).probe()

    def is_available(self, engine_id: AudioEngineId) -> bool:
        return self.provider(engine_id).probe().available

    def provider(self, engine_id: AudioEngineId) -> AudioEngineProviderPort:
        try:
            return self._providers[engine_id]
        except KeyError:
            raise KeyError(
                f"engine provider no registrado: {engine_id.value}"
            ) from None
