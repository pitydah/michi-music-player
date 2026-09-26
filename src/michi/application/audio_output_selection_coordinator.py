"""Semantic audio-output selection intents for DAC-V35-090.

The coordinator owns no state. It validates one explicit user intent, asks the
profile authority to persist it, then aligns the registry/session read models.
It never probes hardware, starts playback, or changes the audio engine.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable
from dataclasses import replace

from michi.application.audio_device_registry import AudioDeviceRegistry
from michi.application.audio_engine_service import AudioEngineService
from michi.application.audio_output_profile_service import AudioOutputProfileService
from michi.application.output_session_service import OutputSessionService
from michi.domain.audio_device import BindingKind
from michi.domain.audio_engine import AudioEngineId
from michi.domain.audio_output import (
    AudioOutputProfile,
    AudioOutputSelection,
    OutputPathPreference,
    is_direct_path,
    stable_direct_preset,
)


class AudioOutputSelectionError(RuntimeError):
    """Typed refusal of one output-selection intent."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


class AudioOutputSelectionCoordinator:
    """Coordinate existing output authorities without becoming one."""

    _PATH_MODE_POLICIES = {
        "strict": OutputPathPreference.HARDWARE_DIRECT,
        "direct": OutputPathPreference.HARDWARE_DIRECT,
        "compatible": OutputPathPreference.HARDWARE_DIRECT_COMPATIBLE,
        "compatible_direct": OutputPathPreference.HARDWARE_DIRECT_COMPATIBLE,
    }

    def __init__(
        self,
        *,
        profiles: AudioOutputProfileService,
        devices: AudioDeviceRegistry,
        output_session: OutputSessionService,
        engines: AudioEngineService,
        clock_ms: Callable[[], int] = lambda: time.time_ns() // 1_000_000,
    ) -> None:
        self._profiles = profiles
        self._devices = devices
        self._output_session = output_session
        self._engines = engines
        self._clock_ms = clock_ms

    def select_shared_output(self) -> None:
        """Use Shared routing WITHOUT forgetting the selected hardware.

        R1.3.1 §6/§7: ``Shared`` means "do not route playback through Direct",
        never "forget the selected DAC". Clearing the hardware identity is a
        separate explicit intent (:meth:`clear_device_selection`).
        """
        selection = self._profiles.load_selection()
        device_id = selection.selected_device_id
        with self._profiles.batch_changes():
            self._profiles.save_selection(
                AudioOutputSelection(None, device_id, self._clock_ms())
            )
            self._devices.select_device(device_id)
            self._output_session.select(device_id=device_id, profile_id=None)

    def clear_device_selection(self) -> None:
        """Explicit intent: forget the selected hardware identity entirely."""
        with self._profiles.batch_changes():
            self._profiles.save_selection(
                AudioOutputSelection(None, None, self._clock_ms())
            )
            self._devices.select_device(None)
            self._output_session.select(device_id=None, profile_id=None)

    def select_device(self, stable_device_id: str) -> None:
        """Select hardware IDENTITY only; the path policy is preserved.

        DAC-V35-100R1.3 §3: selecting a DAC never implies Strict Direct. When
        the current policy is Shared the device is remembered for later policy
        changes but routing stays Shared; when a Direct policy is active the
        same policy is re-bound to the new device.
        """
        stable_device_id = stable_device_id.strip()
        if not stable_device_id:
            self.select_shared_output()
            return
        self._require_playback_device(stable_device_id)

        current = self._selected_profile(self._profiles.load_selection())
        if current is None or not is_direct_path(current.path):
            with self._profiles.batch_changes():
                self._profiles.save_selection(
                    AudioOutputSelection(None, stable_device_id, self._clock_ms())
                )
                self._devices.select_device(stable_device_id)
                self._output_session.select(device_id=stable_device_id, profile_id=None)
            return
        with self._profiles.batch_changes():
            self._select_device_policy(stable_device_id, current.path)

    def select_profile(self, profile_id: str) -> None:
        profile = next(
            (
                item
                for item in self._profiles.load_profiles()
                if item.profile_id == profile_id
            ),
            None,
        )
        if profile is None:
            raise AudioOutputSelectionError(
                "OUTPUT_PROFILE_UNKNOWN", "The requested output profile is unknown."
            )
        stable_device_id = profile.stable_device_id
        if stable_device_id is None:
            if is_direct_path(profile.path):
                raise AudioOutputSelectionError(
                    "SELECTED_DEVICE_MISSING",
                    "Direct output requires a selected physical DAC.",
                )
            self.select_shared_output()
            return
        self._require_playback_device(stable_device_id)
        with self._profiles.batch_changes():
            self._select_profile(profile, stable_device_id=stable_device_id)

    def select_path_mode(self, mode: str) -> None:
        """Select the transport POLICY without changing device identity.

        Accepted modes: ``shared``, ``strict``/``direct`` (exact carrier only)
        and ``compatible`` (exact carrier first, then bounded container-width
        adaptation).
        """
        normalized = mode.strip().casefold().replace("-", "_")
        if normalized == "shared":
            self.select_shared_output()
            return
        policy = self._PATH_MODE_POLICIES.get(normalized)
        if policy is None:
            raise AudioOutputSelectionError(
                "OUTPUT_PATH_MODE_UNKNOWN", "The requested output path is unknown."
            )
        selection = self._profiles.load_selection()
        if selection.selected_device_id is None:
            raise AudioOutputSelectionError(
                "SELECTED_DEVICE_MISSING",
                "Select an available physical DAC before choosing Direct output.",
            )
        self._require_playback_device(selection.selected_device_id)
        with self._profiles.batch_changes():
            self._select_device_policy(selection.selected_device_id, policy)

    def select_volume_mode(self, mode: str) -> None:
        """Accept only modes already supported by the current Stable slice."""
        normalized = mode.strip().casefold()
        selection = self._profiles.load_selection()
        if normalized == "software" and selection.selected_device_id is None:
            self.select_shared_output()
            return
        profile = self._selected_profile(selection)
        if (
            normalized == "fixed"
            and profile is not None
            and profile.volume_policy.value == "fixed"
        ):
            return
        raise AudioOutputSelectionError(
            "VOLUME_MODE_UNAVAILABLE",
            "The requested volume mode is not qualified for this output.",
        )

    def set_resync_delay_ms(self, value: int) -> None:
        if value < 0 or value > 5_000:
            raise AudioOutputSelectionError(
                "RESYNC_DELAY_INVALID", "Resync delay must be between 0 and 5000 ms."
            )
        selection = self._profiles.load_selection()
        profile = self._selected_profile(selection)
        if profile is None or not is_direct_path(profile.path):
            raise AudioOutputSelectionError(
                "DIRECT_PROFILE_REQUIRED",
                "Resync delay requires a selected Direct output profile.",
            )
        with self._profiles.batch_changes():
            self._profiles.save_profile(replace(profile, resync_delay_ms=value))

    def _require_playback_device(self, stable_device_id: str):
        snapshots = {
            item.identity.stable_device_id: item
            for item in self._devices.device_snapshots()
        }
        snapshot = snapshots.get(stable_device_id)
        if snapshot is None:
            raise AudioOutputSelectionError(
                "OUTPUT_DEVICE_UNKNOWN", "The requested audio output is unknown."
            )
        if not snapshot.available:
            raise AudioOutputSelectionError(
                "DEVICE_UNAVAILABLE", "The selected audio output is disconnected."
            )
        if not any(
            binding.kind is BindingKind.ALSA_PCM and binding.currently_available
            for binding in snapshot.bindings
        ):
            raise AudioOutputSelectionError(
                "OUTPUT_DEVICE_NOT_PLAYBACK_CAPABLE",
                "The selected hardware has no current audio playback endpoint.",
            )
        return snapshot

    def _selected_profile(
        self, selection: AudioOutputSelection
    ) -> AudioOutputProfile | None:
        return next(
            (
                item
                for item in self._profiles.load_profiles()
                if item.profile_id == selection.selected_profile_id
            ),
            None,
        )

    def _select_device_policy(
        self, stable_device_id: str, policy: OutputPathPreference
    ) -> None:
        """Bind the canonical ``(device, policy)`` pair to one profile."""
        self._require_playback_device(stable_device_id)
        candidates = sorted(
            (
                profile
                for profile in self._profiles.load_profiles()
                if profile.stable_device_id == stable_device_id
                and profile.path is policy
            ),
            key=lambda profile: profile.profile_id,
        )
        if candidates:
            selection = self._profiles.load_selection()
            profile = next(
                (
                    candidate
                    for candidate in candidates
                    if candidate.profile_id == selection.selected_profile_id
                ),
                candidates[0],
            )
        else:
            profile = stable_direct_preset(
                self._direct_profile_id(stable_device_id, policy),
                stable_device_id,
                path=policy,
            )
            self._require_direct_engine(profile)
            self._profiles.save_profile(profile)
        self._select_profile(profile, stable_device_id=stable_device_id)

    def _select_profile(
        self, profile: AudioOutputProfile, *, stable_device_id: str
    ) -> None:
        if profile.stable_device_id != stable_device_id:
            raise AudioOutputSelectionError(
                "OUTPUT_PROFILE_DEVICE_MISMATCH",
                "The output profile belongs to a different DAC.",
            )
        self._require_direct_engine(profile)
        selection = AudioOutputSelection(
            profile.profile_id, stable_device_id, self._clock_ms()
        )
        self._profiles.save_selection(selection)
        self._devices.select_device(stable_device_id)
        self._output_session.select(
            device_id=stable_device_id, profile_id=profile.profile_id
        )

    def _require_direct_engine(self, profile: AudioOutputProfile) -> None:
        if (
            is_direct_path(profile.path)
            and self._engines.state.active_engine_id is not AudioEngineId.GSTREAMER
        ):
            raise AudioOutputSelectionError(
                "ENGINE_UNSUPPORTED_FOR_DIRECT",
                "Select GStreamer explicitly to use Direct output.",
            )

    @staticmethod
    def _direct_profile_id(
        stable_device_id: str,
        policy: OutputPathPreference = OutputPathPreference.HARDWARE_DIRECT,
    ) -> str:
        digest = hashlib.sha256(stable_device_id.encode("utf-8")).hexdigest()[:16]
        prefix = (
            "compatible"
            if policy is OutputPathPreference.HARDWARE_DIRECT_COMPATIBLE
            else "direct"
        )
        return f"{prefix}:{digest}"
