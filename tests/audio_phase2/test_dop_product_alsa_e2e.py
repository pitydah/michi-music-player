"""AP2-F09 — selected-ALSA DoP through PlaybackService (hardware opt-in)."""

from __future__ import annotations

import dataclasses
import importlib.util
import os
import time
from pathlib import Path

import pytest

from michi.application.audio_output_planner import OutputPlanner
from michi.application.dsd_output_planner import NativeDsdPlanner
from michi.application.dsd_source_characterizer import DsdSourceStatus
from michi.application.output_session_service import (
    DopSessionPrepared,
    OutputSessionService,
)
from michi.application.playback_service import PlaybackService
from michi.domain.audio_device import AudioDeviceBinding, BindingKind
from michi.domain.audio_output import OutputPathPreference, VolumePolicy
from michi.domain.dop import DopCarrierLayout, DopInterpretationState, DopPolicyDecision
from michi.domain.signal_truth import OutputFamilyState, SignalTruthRecorder
from michi.infrastructure.audio_output.dop_runtime import DopOutputExecutor
from tests.audio_phase2.test_dop_resolver import _dop_interp
from tests.audio_phase2.test_dsd_source_truth import build_dsf
from tests.audio_phase2.test_productive_output_resolver import (
    _Characterizer,
    _dsd_qualification,
    _DsdCharacterizer,
    _Engines,
    _Metadata,
    _profile,
    _Profiles,
    _Qualification,
)
from tests.dop.test_dop_planner import _carrier

_HAS_GI = importlib.util.find_spec("gi") is not None


def _resolved_prefix():
    from michi.infrastructure.audio_output.dop_plugin import resolve_dop_prefix

    try:
        return resolve_dop_prefix()
    except RuntimeError:
        return None


_PREFIX = _resolved_prefix()
_PLUGIN = (
    _PREFIX / "libmichidop.so"
    if _PREFIX is not None
    else Path("/nonexistent/libmichidop.so")
)
_DEVICE = os.environ.get("MICHI_DOP_ALSA_DEVICE", "")

pytestmark = pytest.mark.skipif(
    not _HAS_GI
    or os.environ.get("MICHI_RUN_DOP_HARDWARE") != "1"
    or not _DEVICE
    or not _PLUGIN.exists(),
    reason="selected-ALSA product DoP test requires explicit hardware opt-in",
)


class _Devices:
    def bindings_for(self, _device, _kind):
        return [
            AudioDeviceBinding(
                kind=BindingKind.ALSA_PCM,
                locator=_DEVICE,
                generation=7,
                currently_available=True,
            )
        ]

    def generation_for(self, _device):
        return 7

    def available_ids(self):
        return {"dev:dac"}


class _Volume:
    def synchronize(self):
        raise AssertionError("DoP must not synchronize PCM volume")


def _resolver():
    return __import__(
        "michi.application.output_session_service",
        fromlist=["ProductiveOutputRequestResolver"],
    ).ProductiveOutputRequestResolver(
        profiles=_Profiles(
            dataclasses.replace(
                _profile(OutputPathPreference.HARDWARE_DIRECT),
                volume_policy=VolumePolicy.HARDWARE,
            )
        ),
        devices=_Devices(),
        qualification=_Qualification(),
        engines=_Engines(),
        source_metadata=_Metadata(),
        source_characterizer=_Characterizer(),
        dsd_source_characterizer=_DsdCharacterizer(DsdSourceStatus.DSD_PROVEN),
        dsd_planner=NativeDsdPlanner(),
        dsd_qualification=_dsd_qualification,
        dop_policy_provider=lambda _source: DopPolicyDecision(
            explicit_requested=True,
            auto_allowed=False,
            minimum_interpretation_state=DopInterpretationState.USER_CONFIRMED,
        ),
        dop_qualification=lambda _device, binding, _source: (
            dataclasses.replace(
                _carrier(layout=DopCarrierLayout.S32_LE_LSB24),
                stable_device_id="dev:dac",
                binding_generation=binding.generation,
                binding_locator=binding.locator,
                environment_fingerprint="env:1",
            ),
        ),
        dop_interpretation=_dop_interp,
        dop_host_generation=lambda: 1,
        dop_environment_fingerprint=lambda: "env:1",
        dop_device_revision=lambda _device: "rev:1",
        dop_layout_preference=(DopCarrierLayout.S32_LE_LSB24,),
    )


def test_selected_alsa_product_e2e(tmp_path, monkeypatch) -> None:
    from michi.infrastructure.audio_engines.gstreamer_host_client import (
        GStreamerHostSupervisor,
    )
    from michi.infrastructure.audio_engines.gstreamer_host_port import (
        GStreamerHostedAudioPort,
    )

    monkeypatch.setenv("GST_PLUGIN_PATH", str(_PREFIX))
    monkeypatch.setenv("MICHI_DOP_PLUGIN_PREFIX", str(_PREFIX))
    monkeypatch.delenv("MICHI_GST_LAB_SINK", raising=False)
    source = tmp_path / "doop-alsa.dsf"
    source.write_bytes(
        build_dsf(sample_count=352_800 // 4, payload=bytes([0x69]) * 176_400)
    )
    recorder = SignalTruthRecorder()
    supervisor = GStreamerHostSupervisor(
        start_timeout_s=45.0,
        command_timeout_s=30.0,
        terminate_grace_s=8.0,
        term_grace_s=5.0,
        kill_grace_s=5.0,
    )
    port = GStreamerHostedAudioPort(
        supervisor, command_deadline_s=30.0, load_deadline_s=30.0
    )
    holder: dict[str, OutputSessionService] = {}

    def prepare(plan, path, _instance):
        prepared = DopOutputExecutor(port).prepare(plan, path)
        port.add_dop_eos_listener(holder["s"].notify_dop_eos)
        return DopSessionPrepared(
            plan=plan,
            execution_id=plan.execution_id,
            stable_device_id=plan.stable_device_id,
            runtime_identity=dict(prepared.identity),
            evidence_refs=(),
            handle=prepared,
        )

    def commit(prepared):
        DopOutputExecutor(port).commit(prepared.handle)

    def abort(prepared, reason):
        return DopOutputExecutor(port).abort(prepared.handle, reason)

    def stop(prepared, reason):
        return DopOutputExecutor(port).stop(prepared.handle, reason)

    session = OutputSessionService(
        OutputPlanner(),
        request_provider=_resolver(),
        async_submit=None,
        dop_prepare=prepare,
        dop_commit=commit,
        dop_abort=abort,
        dop_stop=stop,
        dop_plan_still_current=lambda _plan: True,
        truth_recorder=recorder,
    )
    holder["s"] = session
    playback = PlaybackService(port, volume_port=_Volume(), output_tx=session)
    try:
        port.activate()
        playback.load_and_play(source)
        execution_id = session.active_execution_id
        assert execution_id
        deadline = time.monotonic() + 8.0
        while time.monotonic() < deadline:
            port.dispatch_pending()
            if session._dop_terminal_execution == execution_id:
                break
            time.sleep(0.02)
        assert session._dop_terminal_execution == execution_id
        states = [event.state for event in recorder.output_family_events]
        assert OutputFamilyState.READY in states
        assert OutputFamilyState.RUNNING in states
        assert OutputFamilyState.UNAVAILABLE in states
        playback.stop()
        states = [event.state for event in recorder.output_family_events]
        assert OutputFamilyState.RELEASED in states
    finally:
        supervisor.close()
