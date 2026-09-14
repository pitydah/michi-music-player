"""DAC-V35-060 unit gates for the single volume execution authority."""

from __future__ import annotations

import pytest

from michi.application.audio_output_ports import (
    DeviceControlUnavailableError,
    OutputVolumeLockedError,
    UnknownVolumeAuthorityError,
    VolumeAuthority,
    VolumeRestoreError,
)
from michi.application.volume_policy_service import VolumePolicyService
from michi.domain.audio_output import VolumePolicy


class AudioSpy:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []
        self.fail_on: str | None = None

    def set_volume(self, value: int) -> None:
        self.calls.append(("volume", value))
        if self.fail_on == "volume":
            raise RuntimeError("volume failed")

    def set_muted(self, muted: bool) -> None:
        self.calls.append(("muted", muted))
        if self.fail_on == "muted":
            raise RuntimeError("mute failed")


class OutputTruth:
    def __init__(
        self,
        *,
        mode: str = "shared",
        policy: VolumePolicy | None = None,
        authority: VolumeAuthority | None = None,
    ) -> None:
        self.mode = mode
        self.volume_policy = policy
        self.volume_authority = authority


def service_for(**truth):
    audio = AudioSpy()
    service = VolumePolicyService(audio, OutputTruth(**truth))
    return service, audio


def test_v60_01_shared_volume_delegates_and_confirms_effective_truth() -> None:
    service, audio = service_for()

    applied = service.apply_volume(37)

    assert audio.calls == [("volume", 37)]
    assert (applied.requested_percent, applied.effective_percent) == (37, 37)
    assert applied.mode == VolumeAuthority.MICHI_SOFTWARE.value
    assert applied.signal_mutated is True
    assert service.preference() == (37, False)


def test_v60_02_shared_volume_clamps_before_execution() -> None:
    service, audio = service_for()

    applied = service.apply_volume(133)

    assert audio.calls == [("volume", 100)]
    assert applied.effective_percent == 100


def test_v60_03_fixed_rejects_attenuation_without_mechanism_write() -> None:
    service, audio = service_for(mode="direct", policy=VolumePolicy.FIXED)

    with pytest.raises(OutputVolumeLockedError):
        service.apply_volume(37)

    assert audio.calls == []
    assert service.preference() == (100, False)


def test_v60_04_fixed_idempotent_unity_is_confirmed() -> None:
    service, audio = service_for(mode="direct", policy=VolumePolicy.FIXED)

    applied = service.apply_volume(100)

    assert audio.calls == [("volume", 100)]
    assert applied.effective_percent == 100
    assert applied.signal_mutated is False


def test_v60_05_external_authority_is_non_adjustable_and_unity() -> None:
    service, audio = service_for(
        mode="direct",
        policy=VolumePolicy.FIXED,
        authority=VolumeAuthority.DEVICE_EXTERNAL,
    )

    assert service.authority is VolumeAuthority.DEVICE_EXTERNAL
    assert service.volume_adjustable is False
    with pytest.raises(OutputVolumeLockedError):
        service.apply_volume(99)
    assert service.apply_volume(100).effective_percent == 100
    assert audio.calls == [("volume", 100)]


def test_v60_06_unqualified_hardware_authority_fails_without_write() -> None:
    service, audio = service_for(mode="direct", policy=VolumePolicy.HARDWARE)

    with pytest.raises(DeviceControlUnavailableError):
        service.apply_volume(50)

    assert audio.calls == []


def test_v60_07_unknown_direct_authority_fails_closed_without_write() -> None:
    service, audio = service_for(mode="direct", policy=VolumePolicy.SOFTWARE)

    with pytest.raises(UnknownVolumeAuthorityError):
        service.apply_volume(50)

    assert audio.calls == []


def test_v60_07_unknown_output_mode_cannot_enable_software_attenuation() -> None:
    service, audio = service_for(mode="recovering", policy=None)

    with pytest.raises(UnknownVolumeAuthorityError):
        service.apply_volume(50)

    assert audio.calls == []


def test_v60_08_fixed_unmute_establishes_unity_before_unmuting() -> None:
    service, audio = service_for(mode="direct", policy=VolumePolicy.FIXED)

    applied = service.apply_muted(False)

    assert audio.calls == [("volume", 100), ("muted", False)]
    assert applied.effective_percent == 100
    assert applied.muted is False


def test_v60_09_fixed_mute_is_explicit_and_reports_muted_truth() -> None:
    service, audio = service_for(mode="direct", policy=VolumePolicy.FIXED)

    applied = service.apply_muted(True)

    assert audio.calls[-1] == ("muted", True)
    assert applied.muted is True


def test_v60_10_unknown_mute_fails_closed_without_write() -> None:
    service, audio = service_for(mode="direct", policy=VolumePolicy.SOFTWARE)

    with pytest.raises(UnknownVolumeAuthorityError):
        service.apply_muted(True)

    assert audio.calls == []


def test_v60_11_restore_in_fixed_seeds_shared_preference_but_applies_unity() -> None:
    service, audio = service_for(mode="direct", policy=VolumePolicy.FIXED)

    applied = service.restore(37, True)

    assert audio.calls == [("volume", 100), ("muted", True)]
    assert applied.effective_percent == 100
    assert applied.muted is True
    assert service.preference() == (37, True)


def test_v60_12_restore_mute_failure_reports_last_confirmed_unmuted_truth() -> None:
    service, audio = service_for()
    audio.fail_on = "muted"

    with pytest.raises(VolumeRestoreError) as raised:
        service.restore(37, True)

    assert raised.value.applied.effective_percent == 37
    assert raised.value.applied.muted is False
    assert service.preference() == (37, False)


def test_v60_13_restore_volume_failure_does_not_claim_requested_effective() -> None:
    service, audio = service_for()
    service.restore(61, False)
    audio.fail_on = "volume"

    with pytest.raises(VolumeRestoreError) as raised:
        service.restore(37, True)

    assert raised.value.applied.effective_percent == 61
    assert raised.value.applied.muted is False
    assert service.preference() == (61, False)


@pytest.mark.parametrize(
    ("authority", "label"),
    [
        (VolumeAuthority.FIXED, "Fixed / Unity"),
        (VolumeAuthority.DEVICE_EXTERNAL, "External volume"),
        (VolumeAuthority.ALSA_HARDWARE, "Hardware volume unavailable"),
        (VolumeAuthority.MICHI_SOFTWARE, "Software volume"),
        (VolumeAuthority.UNKNOWN, "Volume authority unavailable"),
    ],
)
def test_v60_14_authority_labels_are_truthful(
    authority: VolumeAuthority, label: str
) -> None:
    service, _ = service_for(
        mode="direct",
        policy=VolumePolicy.FIXED,
        authority=authority,
    )

    assert service.volume_label == label


def test_v60_15_shared_mode_ignores_stale_direct_authority_projection() -> None:
    service, _ = service_for(
        mode="shared",
        policy=VolumePolicy.FIXED,
        authority=VolumeAuthority.UNKNOWN,
    )

    assert service.authority is VolumeAuthority.MICHI_SOFTWARE
    assert service.volume_adjustable is True
