"""DoP topology loss bound to the canonical AudioDeviceRegistry."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from michi.application.audio_device_registry import AudioDeviceRegistry
from michi.application.audio_output_planner import OutputPlanner
from michi.application.dop_planner import DopPlannerV3
from michi.application.output_session_service import (
    DopSessionPrepared,
    OutputRequest,
    OutputSessionService,
)
from michi.domain.audio_device import BindingKind
from michi.domain.audio_output import OutputSessionState
from michi.domain.dop import (
    DopCarrierLayout,
    DopCarrierQualification,
    DopCarrierSupport,
    DopDeviceInterpretationEvidence,
    DopInterpretationState,
    DopPolicyDecision,
)
from michi.domain.dsd_signal import (
    DsdBitOrder,
    DsdOrganization,
    DsdPacking,
    DsdSignalFormat,
)
from michi.infrastructure.audio_devices.udev_observer import UdevObserver
from tests.dac._fixtures import AlsaCard, UsbDevice, build_linux_sysfs, make_roots

DAC = UsbDevice("2-1", "2622", "0105", serial="DX5HOTPLUG1")


class _Tx:
    def __init__(self) -> None:
        self.aborted: list[str] = []

    def prepare(self, plan, _path, _instance) -> DopSessionPrepared:
        return DopSessionPrepared(
            plan=plan,
            execution_id=plan.execution_id,
            stable_device_id=plan.stable_device_id,
            runtime_identity={},
            evidence_refs=(),
        )

    def commit(self, _prepared) -> None:
        return None

    def abort(self, _prepared, reason) -> dict[str, Any]:
        self.aborted.append(reason)
        return {"aborted": True, "stale": False}

    def stop(self, _prepared, _reason) -> dict[str, Any]:
        return {"stopped": True, "stale": False}


def _registry(tmp_path: Path):
    sysfs = make_roots(tmp_path)
    build_linux_sysfs(sysfs, usb_devices=(DAC,), cards=(AlsaCard(1, "DX5", "2-1"),))
    registry = AudioDeviceRegistry()
    observer = UdevObserver(registry, sysfs_root=sysfs)
    observer.rescan()
    stable_id = registry.snapshot()[0].stable_device_id
    binding = registry.binding_for(stable_id, BindingKind.ALSA_PCM)
    assert binding is not None
    return sysfs, observer, stable_id, binding


def _plan(stable_id: str, locator: str, generation: int):
    source = DsdSignalFormat(
        bit_rate_hz=2_822_400,
        channels=2,
        packing=DsdPacking.DSD_U8,
        bit_order=DsdBitOrder.MSBF,
        organization=DsdOrganization.PLANAR,
        layout=("FL", "FR"),
    )
    carrier = DopCarrierQualification(
        stable_device_id=stable_id,
        carrier_layout_id=DopCarrierLayout.S32_LE_LSB24.value,
        carrier_rate_hz=176_400,
        alsa_format="S32_LE",
        channels=2,
        support=DopCarrierSupport.QUALIFIED,
        environment_fingerprint="env:hotplug",
        evidence_refs=("alsa:hotplug",),
        binding_generation=generation,
        binding_locator=locator,
        significant_transport_bits=24,
        provenance="registry:test",
    )
    interpretation = DopDeviceInterpretationEvidence(
        stable_device_id=stable_id,
        source_dsd_multiplier=64,
        state=DopInterpretationState.USER_CONFIRMED,
        source="test",
        device_revision="rev:hotplug",
        evidence_refs=("user:hotplug",),
    )
    return DopPlannerV3().plan(
        stable_device_id=stable_id,
        binding_locator=locator,
        binding_generation=generation,
        execution_id="exec:hotplug",
        host_generation=1,
        environment_fingerprint="env:hotplug",
        source=source,
        carrier_qualifications=(carrier,),
        interpretation=(interpretation,),
        policy=DopPolicyDecision(
            explicit_requested=True,
            auto_allowed=False,
            minimum_interpretation_state=DopInterpretationState.USER_CONFIRMED,
        ),
        current_device_revision="rev:hotplug",
    )


def _session(plan, tx: _Tx) -> OutputSessionService:
    return OutputSessionService(
        OutputPlanner(),
        request_provider=lambda _path: OutputRequest.dop(plan, "profile:dop"),
        dop_prepare=tx.prepare,
        dop_commit=tx.commit,
        dop_abort=tx.abort,
        dop_stop=tx.stop,
        dop_plan_still_current=lambda _plan: True,
    )


def test_registry_generation_drives_dop_topology_loss(tmp_path: Path) -> None:
    _sysfs, _observer, stable_id, binding = _registry(tmp_path)
    plan = _plan(stable_id, binding.locator, binding.generation)
    tx = _Tx()
    session = _session(plan, tx)
    token = session.prepare_for_media(tmp_path / "track.dsf")
    session.commit_media(token, tmp_path / "track.dsf")
    assert session.notify_dop_playing(plan.execution_id) is True
    session.device_lost(stable_id, binding.generation)
    assert "device_lost" in tx.aborted
    assert session._dop_prepared is None
    assert session.state is OutputSessionState.LOST
    assert session.mode == "lost"
    assert session.notify_dop_eos(plan.execution_id) is False


def test_other_dac_loss_does_not_touch_active_dop(tmp_path: Path) -> None:
    _sysfs, _observer, stable_id, binding = _registry(tmp_path)
    plan = _plan(stable_id, binding.locator, binding.generation)
    tx = _Tx()
    session = _session(plan, tx)
    session.prepare_for_media(tmp_path / "track.dsf")
    session.device_lost("usb:other", binding.generation)
    assert tx.aborted == []
    assert session._dop_prepared is not None


def test_device_loss_during_ready_aborts_without_playing(tmp_path: Path) -> None:
    _sysfs, _observer, stable_id, binding = _registry(tmp_path)
    plan = _plan(stable_id, binding.locator, binding.generation)
    tx = _Tx()
    session = _session(plan, tx)
    session.prepare_for_media(tmp_path / "track.dsf")
    assert session.state is OutputSessionState.READY
    session.device_lost(stable_id, binding.generation)
    assert "device_lost" in tx.aborted
    assert session._dop_prepared is None
    assert session.state is OutputSessionState.LOST


def test_registry_binding_feeds_supervised_qualification(tmp_path: Path) -> None:
    from michi.domain.dop import DopCarrierLayout, DopCarrierSupport
    from michi.infrastructure.audio_devices.alsa_dop_probe import (
        DopCarrierProbeEvidence,
        DopCarrierProbeRequest,
    )
    from michi.infrastructure.audio_devices.dop_qualification import (
        qualification_from_probe,
    )

    _sysfs, _observer, stable_id, binding = _registry(tmp_path)
    evidence = DopCarrierProbeEvidence(
        stable_device_id=stable_id,
        binding_locator=binding.locator,
        binding_generation=binding.generation,
        request=DopCarrierProbeRequest(
            layout=DopCarrierLayout.S32_LE_LSB24,
            alsa_format="S32_LE",
            rate_hz=176_400,
            channels=2,
        ),
        negotiated_rate_hz=176_400,
        negotiated_format="S32_LE",
        negotiated_channels=2,
        support=DopCarrierSupport.QUALIFIED,
        disposition="DOP_CARRIER_EXACT_NEGOTIATED",
        errno_code=None,
        environment_fingerprint="env:registry",
        evidence_ref="registry:probe:1",
        provenance="ALSA_SUPERVISED",
    )
    qualification = qualification_from_probe(
        evidence, environment_fingerprint="env:registry"
    )
    assert qualification.stable_device_id == stable_id
    assert qualification.binding_locator == binding.locator
    assert qualification.binding_generation == binding.generation
    assert qualification.provenance == "ALSA_SUPERVISED"
