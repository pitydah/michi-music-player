"""DAC-V35-030 — AudioOutputProfileService (spec §402).

Único caller de mutaciones autoritativas de profile/selection (C07).
La cache de qualification se muta por su puerto explícito vía
DacQualificationService; aquí no existe ni el método.
"""

from __future__ import annotations

from michi.application.audio_output_ports import AudioOutputProfileRepositoryPort
from michi.domain.audio_output import AudioOutputProfile, AudioOutputSelection


class AudioOutputProfileService:
    def __init__(self, repository: AudioOutputProfileRepositoryPort) -> None:
        self._repository = repository

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
        if profile.resync_delay_ms < 0:
            raise ValueError("resync_delay_ms debe ser >= 0")
        if (
            profile.fallback.value == "specific_device"
            and not profile.fallback_device_id
        ):
            raise ValueError("fallback specific_device exige fallback_device_id")
        self._repository.save_profile(profile)

    def load_selection(self) -> AudioOutputSelection:
        return self._repository.load_selection()

    def save_selection(self, selection: AudioOutputSelection) -> None:
        if selection.selected_device_id is not None and not isinstance(
            selection.selected_device_id, str
        ):
            raise ValueError(
                "selected_device_id debe ser un id estable textual, nunca un índice"
            )
        self._repository.save_selection(selection)

    # C07: la cache de qualification NO se muta desde aquí: su autoridad
    # es el DacQualificationService (QualificationCachePort).
