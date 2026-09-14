"""DAC-V35-060 — single application-layer volume execution authority."""

from __future__ import annotations

from typing import Protocol

from michi.application.audio_output_ports import (
    AppliedVolume,
    DeviceControlUnavailableError,
    OutputVolumeLockedError,
    UnknownVolumeAuthorityError,
    VolumeAuthority,
    VolumeRestoreError,
)
from michi.application.ports import AudioPort
from michi.domain.audio_output import VolumePolicy


class OutputVolumeTruthPort(Protocol):
    @property
    def mode(self) -> str: ...

    @property
    def volume_policy(self) -> VolumePolicy | None: ...

    @property
    def volume_authority(self) -> VolumeAuthority | None: ...


class VolumePolicyService:
    """Resolve legal commands from current output-session truth.

    The persisted percentage remains the Shared/reference preference. Direct
    effective unity is a projection and never overwrites that preference.
    """

    def __init__(self, audio: AudioPort, output: OutputVolumeTruthPort) -> None:
        self._audio = audio
        self._output = output
        self._shared_volume = 100
        self._effective_volume = 100
        self._muted = False

    @property
    def authority(self) -> VolumeAuthority:
        if self._output.mode == "shared":
            return VolumeAuthority.MICHI_SOFTWARE
        if self._output.mode != "direct":
            return VolumeAuthority.UNKNOWN
        resolved = getattr(self._output, "volume_authority", None)
        if resolved is not None:
            return resolved
        policy = self._output.volume_policy
        if policy is VolumePolicy.FIXED:
            return VolumeAuthority.FIXED
        if policy is VolumePolicy.HARDWARE:
            return VolumeAuthority.ALSA_HARDWARE
        return VolumeAuthority.UNKNOWN

    @property
    def volume_adjustable(self) -> bool:
        return self.authority is VolumeAuthority.MICHI_SOFTWARE

    @property
    def volume_label(self) -> str:
        labels = {
            VolumeAuthority.FIXED: "Fixed / Unity",
            VolumeAuthority.DEVICE_EXTERNAL: "External volume",
            VolumeAuthority.ALSA_HARDWARE: "Hardware volume unavailable",
            VolumeAuthority.MICHI_SOFTWARE: "Software volume",
            VolumeAuthority.UNKNOWN: "Volume authority unavailable",
        }
        return labels[self.authority]

    def apply_volume(self, value: int) -> AppliedVolume:
        requested = self._clamp(value)
        authority = self.authority
        if authority is VolumeAuthority.MICHI_SOFTWARE:
            self._audio.set_volume(requested)
            self._shared_volume = requested
            self._effective_volume = requested
            return self._applied(requested, requested)
        if authority in (VolumeAuthority.FIXED, VolumeAuthority.DEVICE_EXTERNAL):
            if requested != 100:
                raise OutputVolumeLockedError(
                    "Direct fixed output is locked at unity (100%)."
                )
            self._audio.set_volume(100)
            self._effective_volume = 100
            return self._applied(requested, 100)
        if authority is VolumeAuthority.ALSA_HARDWARE:
            raise DeviceControlUnavailableError(
                "No qualified hardware-volume control is available."
            )
        raise UnknownVolumeAuthorityError(
            "Direct volume authority is unknown; software gain is forbidden."
        )

    def apply_muted(self, muted: bool) -> AppliedVolume:
        authority = self.authority
        if authority is VolumeAuthority.UNKNOWN:
            raise UnknownVolumeAuthorityError(
                "Direct volume authority is unknown; mute cannot be applied safely."
            )
        if authority in (
            VolumeAuthority.FIXED,
            VolumeAuthority.DEVICE_EXTERNAL,
            VolumeAuthority.ALSA_HARDWARE,
        ):
            # Unity first: unmute can never expose an attenuated Direct path.
            self._audio.set_volume(100)
            self._effective_volume = 100
        self._audio.set_muted(bool(muted))
        self._muted = bool(muted)
        effective = (
            self._shared_volume if authority is VolumeAuthority.MICHI_SOFTWARE else 100
        )
        self._effective_volume = effective
        return self._applied(effective, effective)

    def restore(self, value: int, muted: bool) -> AppliedVolume:
        requested = self._clamp(value)
        authority = self.authority
        if authority is VolumeAuthority.UNKNOWN:
            raise UnknownVolumeAuthorityError(
                "Direct volume authority is unknown; restore fails closed."
            )
        if authority is VolumeAuthority.ALSA_HARDWARE:
            raise DeviceControlUnavailableError(
                "No qualified hardware-volume control is available."
            )
        effective = requested
        try:
            if authority is VolumeAuthority.MICHI_SOFTWARE:
                self._audio.set_volume(requested)
            else:
                effective = 100
                self._audio.set_volume(100)
        except Exception as exc:
            raise VolumeRestoreError(
                f"Volume restore did not complete: {exc}",
                self._applied(requested, self._effective_volume),
            ) from exc

        # A successful gain command confirms both the current effective gain
        # and the persisted Shared/reference preference. Direct unity remains
        # only a projection; it never replaces that preference.
        self._shared_volume = requested
        self._effective_volume = effective
        try:
            self._audio.set_muted(bool(muted))
        except Exception as exc:
            raise VolumeRestoreError(
                f"Volume restore did not complete: {exc}",
                self._applied(requested, effective),
            ) from exc
        self._muted = bool(muted)
        return self._applied(requested, effective)

    def synchronize(self) -> AppliedVolume:
        authority = self.authority
        if authority is VolumeAuthority.UNKNOWN:
            raise UnknownVolumeAuthorityError(
                "Direct volume authority is unknown; synchronization fails closed."
            )
        if authority is VolumeAuthority.ALSA_HARDWARE:
            raise DeviceControlUnavailableError(
                "No qualified hardware-volume control is available."
            )
        effective = (
            self._shared_volume if authority is VolumeAuthority.MICHI_SOFTWARE else 100
        )
        self._effective_volume = effective
        return self._applied(effective, effective)

    def preference(self) -> tuple[int, bool]:
        return self._shared_volume, self._muted

    def _applied(self, requested: int, effective: int) -> AppliedVolume:
        return AppliedVolume(
            requested_percent=requested,
            effective_percent=effective,
            muted=self._muted,
            mode=self.authority.value,
            signal_mutated=(
                self.authority is VolumeAuthority.MICHI_SOFTWARE and effective != 100
            ),
        )

    @staticmethod
    def _clamp(value: int) -> int:
        return max(0, min(100, int(value)))
