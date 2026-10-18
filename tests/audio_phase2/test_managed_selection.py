"""AP2-F06 WU-B — Managed is a real, selectable, persistent output family."""

from __future__ import annotations

import pytest

from michi.application.audio_device_registry import AudioDeviceSnapshot
from michi.application.audio_output_selection_coordinator import (
    AudioOutputSelectionCoordinator,
    AudioOutputSelectionError,
)
from michi.domain.audio_device import (
    AudioDeviceBinding,
    AudioDeviceIdentity,
    BindingKind,
    IdentityConfidence,
)
from michi.domain.audio_engine import AudioEngineId
from michi.domain.audio_output import (
    AudioOutputProfile,
    AudioOutputSelection,
    FallbackKind,
    OutputPathPreference,
    VolumePolicy,
)


class _ProfileStore:
    def __init__(self) -> None:
        self.profiles: dict[str, AudioOutputProfile] = {}
        self.selection = AudioOutputSelection(None, None, 0)

    def batch_changes(self):
        from contextlib import contextmanager

        @contextmanager
        def _batch():
            yield

        return _batch()

    def load_profiles(self):
        return tuple(self.profiles.values())

    def save_profile(self, profile):
        self.profiles[profile.profile_id] = profile

    def load_selection(self):
        return self.selection

    def save_selection(self, selection):
        self.selection = selection

    def snapshot_output_intent(self):
        return ("intent", self.selection.revision)


def _binding(device: str, available: bool = True, locator="hw:2,0"):
    return AudioDeviceBinding(
        kind=BindingKind.ALSA_PCM,
        locator=locator,
        generation=3,
        currently_available=available,
    )


class _Devices:
    def __init__(self, available: dict[str, bool] | None = None) -> None:
        self.available = available or {"dev:dac": True, "dev:other": True}
        self.selected: str | None = None

    def device_snapshots(self):
        return tuple(
            AudioDeviceSnapshot(
                identity=AudioDeviceIdentity(
                    stable_device_id=device,
                    vendor_id=None,
                    product_id=None,
                    serial=None,
                    manufacturer=None,
                    product=device,
                    physical_path=None,
                    bus=None,
                    bcd_device=None,
                    confidence=IdentityConfidence.HIGH,
                ),
                available=available,
                generation=3,
                bindings=(_binding(device, available),),
            )
            for device, available in self.available.items()
        )

    def select_device(self, device):
        self.selected = device


class _Engines:
    def __init__(self, engine=AudioEngineId.GSTREAMER):
        self.state = type("State", (), {"active_engine_id": engine})()


class _OutputSession:
    def __init__(self) -> None:
        self.selection: tuple[str | None, str | None] | None = None
        self.cancelled = 0

    def select(self, *, device_id, profile_id):
        self.selection = (device_id, profile_id)

    def cancel_pending_prepare(self):
        self.cancelled += 1


def _coordinator(
    store=None, devices=None, engines=None, session=None, clock=lambda: 100
):
    return AudioOutputSelectionCoordinator(
        profiles=store or _ProfileStore(),
        devices=devices or _Devices(),
        output_session=session or _OutputSession(),
        engines=engines or _Engines(),
        clock_ms=clock,
    )


def test_selecting_managed_persists_a_managed_profile() -> None:
    store = _ProfileStore()
    devices = _Devices()
    session = _OutputSession()
    coordinator = _coordinator(store, devices, session=session)
    # Device identity must be selected first (normal-flow requirement).
    coordinator.select_device("dev:dac")
    coordinator.select_path_mode("managed")

    profile = store.profiles[store.selection.selected_profile_id]
    assert profile.path is OutputPathPreference.MANAGED
    assert profile.stable_device_id == "dev:dac"
    assert profile.allow_processing is True
    assert profile.allow_resample is False
    assert profile.allow_remix is False
    assert profile.fallback is FallbackKind.STOP
    assert profile.volume_policy is VolumePolicy.SOFTWARE
    assert devices.selected == "dev:dac"
    assert session.selection == ("dev:dac", profile.profile_id)
    assert session.cancelled >= 1


def test_managed_selection_survives_a_reload() -> None:
    store = _ProfileStore()
    devices = _Devices()
    coordinator = _coordinator(store, devices)
    coordinator.select_device("dev:dac")
    coordinator.select_path_mode("managed")
    profile_id = store.selection.selected_profile_id
    # A new coordinator over the SAME persisted authority sees the profile.
    reloaded = _coordinator(store, devices)
    reloaded.select_profile(profile_id)
    profile = store.profiles[profile_id]
    assert profile.path is OutputPathPreference.MANAGED
    assert store.selection.selected_profile_id == profile_id


def test_changing_dac_preserves_the_managed_family() -> None:
    store = _ProfileStore()
    devices = _Devices()
    coordinator = _coordinator(store, devices)
    coordinator.select_device("dev:dac")
    coordinator.select_path_mode("managed")
    old_profile = store.selection.selected_profile_id
    coordinator.select_device("dev:other")
    new_profile_id = store.selection.selected_profile_id
    assert new_profile_id != old_profile
    profile = store.profiles[new_profile_id]
    assert profile.path is OutputPathPreference.MANAGED
    assert profile.stable_device_id == "dev:other"


def test_normal_playback_intent_preserves_managed() -> None:
    store = _ProfileStore()
    devices = _Devices()
    coordinator = _coordinator(store, devices)
    coordinator.select_device("dev:dac")
    coordinator.select_path_mode("managed")
    coordinator.select_device_for_playback("dev:other")
    profile = store.profiles[store.selection.selected_profile_id]
    assert profile.path is OutputPathPreference.MANAGED
    assert profile.stable_device_id == "dev:other"


def test_managed_direct_and_shared_transitions() -> None:
    store = _ProfileStore()
    devices = _Devices()
    coordinator = _coordinator(store, devices)
    coordinator.select_device("dev:dac")
    coordinator.select_path_mode("managed")
    coordinator.select_path_mode("direct")
    assert store.profiles[store.selection.selected_profile_id].path is (
        OutputPathPreference.HARDWARE_DIRECT
    )
    coordinator.select_path_mode("managed")
    assert store.profiles[store.selection.selected_profile_id].path is (
        OutputPathPreference.MANAGED
    )
    coordinator.select_path_mode("shared")
    assert store.selection.selected_profile_id is None
    assert store.selection.selected_device_id == "dev:dac"


def test_managed_requires_a_selected_available_dac() -> None:
    store = _ProfileStore()
    coordinator = _coordinator(store)
    with pytest.raises(AudioOutputSelectionError) as info:
        coordinator.select_path_mode("managed")
    assert info.value.code == "SELECTED_DEVICE_MISSING"

    unavailable = _Devices({"dev:dac": False})
    coordinator = _coordinator(_ProfileStore(), unavailable)
    with pytest.raises(AudioOutputSelectionError) as info:
        coordinator._select_device_policy("dev:dac", OutputPathPreference.MANAGED)
    assert info.value.code == "DEVICE_UNAVAILABLE"


def test_managed_rejects_a_non_gstreamer_engine() -> None:
    store = _ProfileStore()
    devices = _Devices()
    coordinator = _coordinator(store, devices, engines=_Engines(AudioEngineId.MPD))
    coordinator.select_device("dev:dac")  # shared selection is engine-neutral
    with pytest.raises(AudioOutputSelectionError) as info:
        coordinator.select_path_mode("managed")
    assert info.value.code == "ENGINE_UNSUPPORTED_FOR_MANAGED"
    assert store.selection.selected_profile_id is None


def test_managed_software_volume_is_accepted() -> None:
    store = _ProfileStore()
    coordinator = _coordinator(store)
    coordinator.select_device("dev:dac")
    coordinator.select_path_mode("managed")
    coordinator.select_volume_mode("software")  # no refusal
