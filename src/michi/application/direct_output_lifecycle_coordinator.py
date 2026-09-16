"""DAC-V35-080 application orchestration for Direct topology lifecycle."""

from __future__ import annotations

from michi.application.audio_device_registry import (
    AudioDeviceRegistry,
    AudioDeviceTopologyChange,
)
from michi.application.output_session_service import OutputSessionService
from michi.application.playback_service import PlaybackService
from michi.domain.audio_device import BindingKind


class DirectOutputLifecycleCoordinator:
    """Routes canonical topology truth without taking authority from services."""

    def __init__(
        self,
        registry: AudioDeviceRegistry,
        playback: PlaybackService,
        output_session: OutputSessionService,
    ) -> None:
        self._registry = registry
        self._playback = playback
        self._output_session = output_session
        self._active = False

    @property
    def active(self) -> bool:
        return self._active

    def start(self) -> None:
        if self._active:
            return
        self._active = True
        self._registry.subscribe_topology_changed(self.handle_topology_changed)

    def shutdown(self) -> None:
        if not self._active:
            return
        self._active = False
        self._registry.unsubscribe_topology_changed(self.handle_topology_changed)

    def handle_topology_changed(self, change: AudioDeviceTopologyChange) -> None:
        if not self._active:
            return
        if self._registry.generation_for(change.stable_device_id) != (
            change.current_generation
        ):
            return  # queued callback from an older binding generation
        registry_available = change.stable_device_id in self._registry.available_ids()
        if registry_available != change.current_available:
            return
        if not change.current_available:
            if self._output_session.active_device_id == change.stable_device_id:
                self._playback.converge_after_output_loss(
                    change.stable_device_id,
                    change.current_generation,
                )
            return
        if not any(
            binding.kind is BindingKind.ALSA_PCM
            and binding.currently_available
            and binding.generation == change.current_generation
            for binding in change.current_bindings
        ):
            return
        self._output_session.rebind_after_topology_change(
            change.stable_device_id,
            change.current_generation,
        )
