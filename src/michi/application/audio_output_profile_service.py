"""DAC-V35-030 — AudioOutputProfileService (spec §402).

Único caller de mutaciones autoritativas de profile/selection (C07).
La cache de qualification se muta por su puerto explícito vía
DacQualificationService; aquí no existe ni el método.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager

from michi.application.audio_output_ports import AudioOutputProfileRepositoryPort
from michi.domain.audio_output import AudioOutputProfile, AudioOutputSelection


def _reject_ephemeral_alsa_identity(value: str | None, *, field: str) -> None:
    if value is None:
        return
    normalized = value.strip().casefold()
    raw_names = {"default", "null", "pipewire", "pulse"}
    raw_prefixes = (
        "hw:",
        "plughw:",
        "default:",
        "sysdefault:",
        "front:",
        "surround",
        "dmix:",
        "dsnoop:",
        "null:",
        "pipewire:",
        "pulse:",
    )
    if normalized in raw_names or normalized.startswith(raw_prefixes):
        raise ValueError(
            f"{field} must be a stable device identity, never a raw ALSA locator"
        )


class AudioOutputProfileService:
    def __init__(self, repository: AudioOutputProfileRepositoryPort) -> None:
        self._repository = repository
        self._subscribers: list[Callable[[], None]] = []
        self._notification_depth = 0
        self._notification_pending = False

    def subscribe_changed(self, callback: Callable[[], None]) -> None:
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe_changed(self, callback: Callable[[], None]) -> None:
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def _notify(self) -> None:
        if self._notification_depth:
            self._notification_pending = True
            return
        for callback in tuple(self._subscribers):
            callback()

    @contextmanager
    def batch_changes(self) -> Iterator[None]:
        """Publish one coherent notification after related repository writes."""
        self._notification_depth += 1
        try:
            yield
        finally:
            self._notification_depth -= 1
            if self._notification_depth == 0 and self._notification_pending:
                self._notification_pending = False
                self._notify()

    def load_profiles(self) -> tuple[AudioOutputProfile, ...]:
        return self._repository.load_profiles()

    def save_profile(self, profile: AudioOutputProfile) -> None:
        """Valida invariantes del §0I antes de persistir.

        Nunca se guarda un índice de card ALSA: solo stable_device_id
        textual. El fallback a dispositivo específico exige id.
        """
        if profile.stable_device_id is not None and not isinstance(
            profile.stable_device_id, str
        ):
            raise ValueError(
                "stable_device_id debe ser un id estable textual, nunca un índice"
            )
        _reject_ephemeral_alsa_identity(
            profile.stable_device_id, field="stable_device_id"
        )
        _reject_ephemeral_alsa_identity(
            profile.fallback_device_id, field="fallback_device_id"
        )
        if profile.resync_delay_ms < 0:
            raise ValueError("resync_delay_ms debe ser >= 0")
        if (
            profile.fallback.value == "specific_device"
            and not profile.fallback_device_id
        ):
            raise ValueError("fallback specific_device exige fallback_device_id")
        self._repository.save_profile(profile)
        self._notify()

    def load_selection(self) -> AudioOutputSelection:
        return self._repository.load_selection()

    def save_selection(self, selection: AudioOutputSelection) -> None:
        if selection.selected_device_id is not None and not isinstance(
            selection.selected_device_id, str
        ):
            raise ValueError(
                "selected_device_id debe ser un id estable textual, nunca un índice"
            )
        _reject_ephemeral_alsa_identity(
            selection.selected_device_id, field="selected_device_id"
        )
        self._repository.save_selection(selection)
        self._notify()

    # C07: la cache de qualification NO se muta desde aquí: su autoridad
    # es el DacQualificationService (QualificationCachePort).
