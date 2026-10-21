"""AP2-F06 — Managed PCM plan + planner (specific DAC, processed route).

Pure contract tests: no Gst, no devices. The planner must refuse with typed
codes instead of silently downgrading device/rate/channels/terminal format.
"""

from __future__ import annotations

import dataclasses

import pytest

from michi.application.effective_processing_graph import (
    EffectiveProcessingGraphResolver,
)
from michi.application.managed_pcm_output_planner import (
    ManagedPcmOutputPlanner,
    ManagedPcmPlannerFacts,
)
from michi.application.processing_graph_compiler import (
    ProcessingBackendCapabilities,
    ProcessingGraphCompiler,
)
from michi.domain.audio_device import AudioDeviceBinding, BindingKind
from michi.domain.audio_evidence import PcmTuple
from michi.domain.audio_processing import (
    PreampNode,
    ProcessingGraph,
    ProcessingStrategy,
)
from michi.domain.audio_signal import ChannelLayout, PcmSignalFormat
from michi.domain.managed_pcm_output import (
    MANAGED_PCM_PATH,
    ManagedPcmOutputPlan,
    ManagedPcmPlanError,
    ManagedPcmRefusal,
)


def _binding(
    *, kind=BindingKind.ALSA_PCM, locator="hw:2,0", available=True, generation=4
) -> AudioDeviceBinding:
    return AudioDeviceBinding(
        kind=kind,
        locator=locator,
        generation=generation,
        currently_available=available,
    )


def _signal(rate=44100, channels=2):
    return PcmSignalFormat(
        rate_hz=rate,
        transport_format="S16LE",
        significant_bits=16,
        layout=ChannelLayout(
            positions=tuple(f"CH{index}" for index in range(channels))
        ),
    )


def _compiled_plan(rate=44100, channels=2, gain_db=-3.0):
    graph = ProcessingGraph(
        graph_id="graph:managed",
        revision=7,
        nodes=(PreampNode(node_id="pre", gain_db=gain_db),),
    )
    effective = EffectiveProcessingGraphResolver().resolve(
        graph, input_signal=_signal(rate, channels), assets=()
    )
    return ProcessingGraphCompiler().compile(
        effective,
        backend=ProcessingBackendCapabilities(
            backend_id="test", strategies=frozenset(ProcessingStrategy)
        ),
        assets=(),
    )


def _facts(**overrides) -> ManagedPcmPlannerFacts:
    source = PcmTuple(
        rate_hz=44100, transport_format="S16LE", channels=2, significant_bits=16
    )
    base = dict(
        selected_device_id="dev:smsl",
        binding=_binding(),
        binding_device_id="dev:smsl",
        source_pcm=source,
        compiled_plan=_compiled_plan(),
        terminal_formats=frozenset({"S16LE", "S32LE"}),
        volume_policy="software",
        selection_revision=3,
        current_selection_revision=3,
    )
    base.update(overrides)
    return ManagedPcmPlannerFacts(**base)


def test_managed_plan_is_a_distinct_specific_dac_processed_route() -> None:
    planner = ManagedPcmOutputPlanner()
    result = planner.plan(_facts())
    assert isinstance(result, ManagedPcmOutputPlan), result
    assert result.path == MANAGED_PCM_PATH
    assert result.path != "direct"
    assert result.stable_device_id == "dev:smsl"
    assert result.device_locator == "hw:2,0"
    assert result.binding_generation == 4
    assert result.output_rate_hz == 44100
    assert result.output_channels == 2
    assert result.terminal_format == "S16LE"
    assert result.volume_policy == "software"
    assert result.processing_plan_id is not None
    assert "dsp" in result.transform_policy
    assert "representation_conversion" in result.transform_policy
    assert result.execution_id
    # No Direct OutputPlan attribute exists on the managed plan.
    assert not hasattr(result, "allow_processing")


def test_managed_plan_is_deterministic_for_identical_facts() -> None:
    planner = ManagedPcmOutputPlanner()
    first = planner.plan(_facts())
    second = planner.plan(_facts())
    assert first == second
    third = planner.plan(_facts(selection_revision=4, current_selection_revision=4))
    assert third.execution_id != first.execution_id


def test_identity_managed_route_requires_a_proven_terminal_format() -> None:
    result = ManagedPcmOutputPlanner().plan(
        _facts(compiled_plan=None, terminal_formats=frozenset({"S16LE"}))
    )
    assert isinstance(result, ManagedPcmOutputPlan), result
    assert result.processing_plan_id is None
    assert result.transform_policy == ("identity",)
    assert result.output_rate_hz == 44100


@pytest.mark.parametrize(
    ("overrides", "code"),
    [
        ({"selected_device_id": None}, "SELECTED_DEVICE_MISSING"),
        ({"binding": None}, "BINDING_UNAVAILABLE"),
        (
            {"binding": _binding(kind=BindingKind.PIPEWIRE_NODE)},
            "BINDING_NOT_ALSA",
        ),
        ({"binding": _binding(available=False)}, "DEVICE_UNAVAILABLE"),
        ({"binding": _binding(locator="")}, "BINDING_UNAVAILABLE"),
        ({"binding_device_id": "dev:other"}, "BINDING_SELECTION_MISMATCH"),
        ({"current_selection_revision": 9}, "SELECTION_STALE"),
        ({"volume_policy": "auto"}, "VOLUME_POLICY_INVALID"),
        ({"terminal_formats": frozenset()}, "TERMINAL_FORMAT_UNPROVEN"),
    ],
)
def test_managed_refusals_are_typed_and_never_fallback(overrides, code) -> None:
    result = ManagedPcmOutputPlanner().plan(_facts(**overrides))
    assert isinstance(result, ManagedPcmRefusal), result
    assert result.code == code


def test_rate_change_without_resample_node_is_refused() -> None:
    plan = _compiled_plan()
    forged = dataclasses.replace(
        plan,
        sample_contract=dataclasses.replace(plan.sample_contract, output_rate_hz=48000),
        changes_rate=False,
    )
    result = ManagedPcmOutputPlanner().plan(_facts(compiled_plan=forged))
    assert isinstance(result, ManagedPcmRefusal)
    assert result.code == "RATE_POLICY_VIOLATION"


def test_channel_change_without_channel_map_node_is_refused() -> None:
    plan = _compiled_plan()
    forged = dataclasses.replace(
        plan,
        sample_contract=dataclasses.replace(plan.sample_contract, channels_out=1),
        changes_channels=False,
    )
    result = ManagedPcmOutputPlanner().plan(_facts(compiled_plan=forged))
    assert isinstance(result, ManagedPcmRefusal)
    assert result.code == "CHANNEL_POLICY_VIOLATION"


def test_compiled_plan_for_a_different_source_is_refused() -> None:
    result = ManagedPcmOutputPlanner().plan(
        _facts(compiled_plan=_compiled_plan(rate=48000))
    )
    assert isinstance(result, ManagedPcmRefusal)
    assert result.code == "PROCESSING_PLAN_MISMATCH"


def test_plan_rejects_a_direct_or_empty_path_at_construction() -> None:
    with pytest.raises(ManagedPcmPlanError):
        ManagedPcmOutputPlan(
            plan_id="m",
            stable_device_id="dev",
            device_locator="hw:0,0",
            binding_generation=1,
            source_pcm=PcmTuple(44100, "S16LE", 2, 16),
            processing_plan_id=None,
            processing_graph_revision=0,
            processing_revision=0,
            working_format="S16LE",
            output_rate_hz=44100,
            output_channels=2,
            terminal_format="S16LE",
            volume_policy="software",
            selection_revision=1,
            execution_id="x",
            transform_policy=("identity",),
            path="direct",
        )


# ── executor (unit) ────────────────────────────────────────────────────
from pathlib import Path  # noqa: E402

from michi.infrastructure.audio_output.managed_pcm_executor import (  # noqa: E402
    ManagedPcmExecutionError,
    ManagedPcmExecutor,
)


class _FakeManagedPort:
    def __init__(self, identity: dict | None = None) -> None:
        self.identity = identity or {}
        self.calls: list[tuple[str, object]] = []

    def stage_managed_execution(self, recipe: dict) -> None:
        self.calls.append(("stage", dict(recipe)))

    def load(self, path) -> None:
        self.calls.append(("load", str(path)))

    def query_managed_identity(self) -> dict:
        return dict(self.identity)

    def stop(self) -> None:
        self.calls.append(("stop", None))


def _identity_for(plan, execution_id: str | None = None) -> dict:
    return {
        "managed": True,
        "loaded": True,
        "execution_id": execution_id or plan.execution_id,
        "plan_id": plan.plan_id,
        "device": plan.device_locator,
        "format": plan.terminal_format,
        "rate_hz": plan.output_rate_hz,
        "channels": plan.output_channels,
        "lab_sink": False,
    }


def _managed_plan() -> ManagedPcmOutputPlan:
    result = ManagedPcmOutputPlanner().plan(_facts())
    assert isinstance(result, ManagedPcmOutputPlan), result
    return result


def test_executor_stages_loads_and_verifies_the_selected_binding() -> None:
    plan = _managed_plan()
    port = _FakeManagedPort(_identity_for(plan))
    executor = ManagedPcmExecutor(
        lambda: port, install_processing=lambda _plan: {"revision": 9}
    )
    receipt = executor.execute(plan, Path("/media/song.flac"))
    assert [call[0] for call in port.calls] == ["stage", "load"]
    staged = port.calls[0][1]
    assert staged["device"] == "hw:2,0"
    assert staged["gst_format"] == plan.terminal_format
    assert receipt.path == "managed_pcm"
    assert receipt.device_locator == "hw:2,0"
    assert receipt.processing_revision == 9
    assert receipt.runtime_identity["managed"] is True


def test_executor_requires_a_transport() -> None:
    with pytest.raises(ManagedPcmExecutionError) as info:
        ManagedPcmExecutor(lambda: None).execute(_managed_plan(), "/media/a.flac")
    assert info.value.code == "MANAGED_PCM_TRANSPORT_UNAVAILABLE"


def test_executor_contains_an_identity_mismatch() -> None:
    plan = _managed_plan()
    identity = _identity_for(plan)
    identity["device"] = "hw:9,0"  # a different DAC answered
    port = _FakeManagedPort(identity)
    executor = ManagedPcmExecutor(
        lambda: port, install_processing=lambda _plan: {"revision": 1}
    )
    with pytest.raises(ManagedPcmExecutionError) as info:
        executor.execute(plan, "/media/a.flac")
    assert info.value.code == "MANAGED_PCM_IDENTITY_MISMATCH"
    assert ("stop", None) in port.calls


def test_executor_contains_processing_install_failure() -> None:
    plan = _managed_plan()
    port = _FakeManagedPort(_identity_for(plan))

    def failing(_plan):
        raise RuntimeError("DSP install exploded")

    with pytest.raises(ManagedPcmExecutionError) as info:
        ManagedPcmExecutor(lambda: port, install_processing=failing).execute(
            plan, "/media/a.flac"
        )
    assert info.value.code == "MANAGED_PCM_PROCESSING_FAILED"
    assert ("stop", None) in port.calls


def test_executor_refuses_processing_without_an_authority() -> None:
    plan = _managed_plan()
    port = _FakeManagedPort(_identity_for(plan))
    with pytest.raises(ManagedPcmExecutionError) as info:
        ManagedPcmExecutor(lambda: port).execute(plan, "/media/a.flac")
    assert info.value.code == "MANAGED_PCM_PROCESSING_UNAVAILABLE"
    assert ("stop", None) in port.calls


class _TwoPhasePort(_FakeManagedPort):
    def __init__(self, identity: dict) -> None:
        super().__init__(identity)
        self.identity_queries = 0

    def query_managed_identity(self) -> dict:
        self.identity_queries += 1
        if self.identity_queries >= 2:
            raise RuntimeError("readback lost after install")
        return super().query_managed_identity()


class _GenerationPort(_FakeManagedPort):
    def supervisor_generation(self) -> int:
        return 5


def test_executor_fails_closed_when_post_install_identity_is_unavailable() -> None:
    plan = _managed_plan()
    port = _TwoPhasePort(_identity_for(plan))
    executor = ManagedPcmExecutor(
        lambda: port, install_processing=lambda _plan: {"revision": 1}
    )
    with pytest.raises(ManagedPcmExecutionError) as info:
        executor.execute(plan, "/media/a.flac")
    assert info.value.code == "MANAGED_PCM_POST_INSTALL_IDENTITY_UNAVAILABLE"
    assert ("stop", None) in port.calls


def test_executor_accepts_a_supervisor_generation_method() -> None:
    plan = _managed_plan()
    port = _GenerationPort(_identity_for(plan))
    executor = ManagedPcmExecutor(
        lambda: port, install_processing=lambda _plan: {"revision": 1}
    )
    receipt = executor.execute(plan, "/media/a.flac")
    assert receipt.runtime_identity["host_generation"] == 5
    assert isinstance(receipt.runtime_identity["host_generation"], int)


def test_executor_rejects_a_different_execution_instance() -> None:
    plan = _managed_plan()
    port = _FakeManagedPort(_identity_for(plan, execution_id="exec:other"))
    executor = ManagedPcmExecutor(
        lambda: port, install_processing=lambda _plan: {"revision": 1}
    )
    with pytest.raises(ManagedPcmExecutionError) as info:
        executor.execute(plan, "/media/a.flac", execution_instance_id="exec:expected")
    assert info.value.code == "MANAGED_PCM_IDENTITY_MISMATCH"
    assert ("stop", None) in port.calls
