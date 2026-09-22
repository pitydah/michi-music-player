"""DAC-V35-100R1.3 — playback compatibility, output-mode separation, lifecycle.

Phase gates are prefixed with the R1.3 phase they seal:

- ``pc13_02_*`` Shared playback baseline (explicit Shared never plans Direct)
- ``pc13_03_*`` device identity vs output-path policy separation
- ``pc13_04_*`` bounded candidate carrier resolution
- ``pc13_05_*`` compatible Direct (container-width adaptation only)
- ``pc13_06_*`` output failure presentation and recovery intents
- ``pc13_07_*`` native lifecycle hardening (command fence, close atomicity)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from michi.application.audio_output_selection_coordinator import (
    AudioOutputSelectionCoordinator,
)
from michi.application.carrier_resolution import (
    CandidateCarrierResolver,
    CarrierAdaptationKind,
)
from michi.domain.audio_evidence import DecodedSourceSignal, ExactProbeResult, PcmTuple
from michi.domain.audio_output import OutputPathPreference
from tests.dac.test_v35_productive_direct_composition import (
    _close_graph,
    _direct_graph,
)


def _plan_with_adaptation(adaptation: str):
    from michi.domain.audio_device import AudioDeviceBinding, BindingKind
    from michi.domain.audio_output import (
        FallbackKind,
        GstSinkSpec,
        OutputPlan,
        PathSemantics,
        VolumePolicy,
    )

    return OutputPlan(
        plan_id=f"plan:{adaptation}",
        stable_device_id="usb:2622:0105:DX5ABC123",
        binding=AudioDeviceBinding(
            kind=BindingKind.ALSA_PCM,
            locator="hw:CARD=X,DEV=0",
            generation=1,
            currently_available=True,
            card_index=1,
            pcm_device=0,
        ),
        path_semantics=PathSemantics.HARDWARE_RAW,
        requested_pcm=PcmTuple(44_100, "S32_LE", 2, 16),
        engine_id="gstreamer",
        volume_policy=VolumePolicy.FIXED,
        allow_resample=False,
        allow_remix=False,
        allow_processing=False,
        fallback=FallbackKind.STOP,
        sink=GstSinkSpec("alsasink", "hw:CARD=X,DEV=0"),
        resync_delay_ms=0,
        preconditions=(),
        evidence_refs=(),
        decision_codes=(),
        carrier_adaptation=adaptation,
    )


def _coordinator(graph) -> AudioOutputSelectionCoordinator:
    return AudioOutputSelectionCoordinator(
        profiles=graph.audio_output_profiles,
        devices=graph.audio_device_registry,
        output_session=graph.output_session,
        engines=graph.audio_engine_service,
    )


def _shared_graph(tmp_path: Path, probe_calls: list[dict]):
    """Graph whose qualification adapter refuses to be called."""

    class _ForbiddenProbe:
        def probe_exact(self, **kwargs):
            probe_calls.append(kwargs)
            raise AssertionError("Shared output must never run an exact ALSA probe")

    return _direct_graph(
        tmp_path,
        qualification_adapter=_ForbiddenProbe(),
        preseed_qualification=False,
    )


# ── Phase 2 — Shared playback ──────────────────────────────────────────────


def test_pc13_02_01_shared_selection_persists_without_direct_profile(
    qapp, tmp_path: Path
) -> None:
    probe_calls: list[dict] = []
    graph, _bindings = _shared_graph(tmp_path, probe_calls)
    coordinator = _coordinator(graph)
    try:
        coordinator.select_shared_output()

        selection = graph.audio_output_profiles.load_selection()
        assert selection.selected_profile_id is None
        assert selection.selected_device_id is None
        session_state = graph.output_session.selection_state()
        assert session_state.selected_device_id is None
        assert session_state.selected_profile_id is None
        assert graph.output_session.mode == "shared"
        assert probe_calls == []
    finally:
        _close_graph(graph)


def test_pc13_02_02_shared_playback_bypasses_direct_planner_and_probe(
    qapp, tmp_path: Path
) -> None:
    probe_calls: list[dict] = []
    graph, bindings = _shared_graph(tmp_path, probe_calls)
    coordinator = _coordinator(graph)
    media = tmp_path / "shared.flac"
    try:
        coordinator.select_shared_output()
        graph.playback.load_and_play(media)

        assert graph.output_session.mode == "shared"
        assert graph.output_session.plan is None
        assert graph.direct_output_executor.handle is None
        # Shared playback never installs a Strict Direct sink on the engine.
        assert bindings.pipelines[-1].audio_sink is None
        assert probe_calls == []
    finally:
        _close_graph(graph)


def test_pc13_02_03_shared_playback_uses_shared_transaction(
    qapp, tmp_path: Path
) -> None:
    probe_calls: list[dict] = []
    graph, _bindings = _shared_graph(tmp_path, probe_calls)
    coordinator = _coordinator(graph)
    media = tmp_path / "shared.flac"
    try:
        coordinator.select_shared_output()
        token = graph.output_session.prepare_for_media(media)

        assert token.startswith("output-tx:shared:")
        assert graph.output_session.mode == "shared"
        assert graph.output_session._shared_receipt is not None
        assert graph.output_session._executor is None
        assert probe_calls == []
    finally:
        _close_graph(graph)


# ── Phase 3 — device identity vs output-path policy ────────────────────────


def test_pc13_03_01_device_selection_never_implies_strict_direct(
    qapp, tmp_path: Path
) -> None:
    probe_calls: list[dict] = []
    graph, _bindings = _shared_graph(tmp_path, probe_calls)
    coordinator = _coordinator(graph)
    try:
        coordinator.select_shared_output()
        coordinator.select_device("usb:2622:0105:DX5ABC123")

        selection = graph.audio_output_profiles.load_selection()
        assert selection.selected_device_id == "usb:2622:0105:DX5ABC123"
        assert selection.selected_profile_id is None
        assert graph.output_session.mode == "shared"
        assert probe_calls == []
    finally:
        _close_graph(graph)


def test_pc13_03_02_path_mode_selection_never_changes_device_identity(
    qapp, tmp_path: Path
) -> None:
    probe_calls: list[dict] = []
    graph, _bindings = _shared_graph(tmp_path, probe_calls)
    coordinator = _coordinator(graph)
    device_id = "usb:2622:0105:DX5ABC123"
    try:
        coordinator.select_shared_output()
        coordinator.select_device(device_id)
        coordinator.select_path_mode("strict")

        selection = graph.audio_output_profiles.load_selection()
        assert selection.selected_device_id == device_id
        profile = next(
            item
            for item in graph.audio_output_profiles.load_profiles()
            if item.profile_id == selection.selected_profile_id
        )
        assert profile.stable_device_id == device_id
        assert profile.path is OutputPathPreference.HARDWARE_DIRECT
        assert graph.output_session.mode == "shared"  # no playback started yet
    finally:
        _close_graph(graph)


def test_pc13_03_03_strict_and_compatible_are_distinct_persisted_policies(
    qapp, tmp_path: Path
) -> None:
    probe_calls: list[dict] = []
    graph, _bindings = _shared_graph(tmp_path, probe_calls)
    coordinator = _coordinator(graph)
    device_id = "usb:2622:0105:DX5ABC123"
    try:
        coordinator.select_shared_output()
        coordinator.select_device(device_id)
        coordinator.select_path_mode("strict")
        strict_id = graph.audio_output_profiles.load_selection().selected_profile_id

        coordinator.select_path_mode("compatible")
        compatible_id = graph.audio_output_profiles.load_selection().selected_profile_id

        assert strict_id != compatible_id
        profiles = {
            item.profile_id: item
            for item in graph.audio_output_profiles.load_profiles()
        }
        assert profiles[strict_id].path is OutputPathPreference.HARDWARE_DIRECT
        assert (
            profiles[compatible_id].path
            is OutputPathPreference.HARDWARE_DIRECT_COMPATIBLE
        )
        # Switching policy never changes the selected hardware identity.
        assert (
            graph.audio_output_profiles.load_selection().selected_device_id == device_id
        )
    finally:
        _close_graph(graph)


def test_pc13_03_04_restart_restores_device_and_policy_truth(
    qapp, tmp_path: Path
) -> None:
    probe_calls: list[dict] = []
    graph, _bindings = _shared_graph(tmp_path, probe_calls)
    coordinator = _coordinator(graph)
    device_id = "usb:2622:0105:DX5ABC123"
    try:
        coordinator.select_shared_output()
        coordinator.select_device(device_id)
        coordinator.select_path_mode("compatible")

        # A fresh coordinator over the same persisted authorities == restart.
        restarted = _coordinator(graph)
        selection = graph.audio_output_profiles.load_selection()
        assert selection.selected_device_id == device_id
        profile = next(
            item
            for item in graph.audio_output_profiles.load_profiles()
            if item.profile_id == selection.selected_profile_id
        )
        assert profile.path is OutputPathPreference.HARDWARE_DIRECT_COMPATIBLE

        # Device identity survives a policy re-selection after restart.
        restarted.select_path_mode("strict")
        after = graph.audio_output_profiles.load_selection()
        assert after.selected_device_id == device_id
        assert after.selected_profile_id != selection.selected_profile_id
    finally:
        _close_graph(graph)


# ── Phase 4 — bounded candidate carrier resolution ─────────────────────────


def _decoded_source(bits: int | None, *, rate: int = 44_100, channels: int = 2):
    return DecodedSourceSignal("PCM", rate, bits, channels, None)


def test_pc13_04_01_sixteen_bit_exact_candidate_is_the_narrow_container() -> None:
    resolved = CandidateCarrierResolver().candidates(
        _decoded_source(16), allow_adaptation=False
    )
    assert [item.tuple.transport_format for item in resolved] == ["S16_LE"]
    assert resolved[0].adaptation_kind is CarrierAdaptationKind.EXACT
    assert resolved[0].tuple.significant_bits == 16
    assert resolved[0].tuple.rate_hz == 44_100
    assert resolved[0].tuple.channels == 2


def test_pc13_04_02_compatible_adds_bounded_wide_container_candidate() -> None:
    resolved = CandidateCarrierResolver().candidates(
        _decoded_source(16), allow_adaptation=True
    )
    assert [item.tuple.transport_format for item in resolved] == ["S16_LE", "S32_LE"]
    adapted = resolved[1]
    assert adapted.adaptation_kind is CarrierAdaptationKind.CONTAINER_WIDTH
    # Container width never fabricates precision.
    assert adapted.tuple.significant_bits == 16
    assert adapted.tuple.rate_hz == 44_100
    assert adapted.tuple.channels == 2


def test_pc13_04_03_strict_excludes_every_adaptation_candidate() -> None:
    strict = CandidateCarrierResolver().candidates(
        _decoded_source(16), allow_adaptation=False
    )
    assert all(item.is_exact for item in strict)
    assert all(
        item.adaptation_kind is not CarrierAdaptationKind.CONTAINER_WIDTH
        for item in strict
    )


def test_pc13_04_04_unknown_significant_bits_never_candidates_or_adapts() -> None:
    for allow_adaptation in (False, True):
        assert (
            CandidateCarrierResolver().candidates(
                _decoded_source(None), allow_adaptation=allow_adaptation
            )
            == ()
        )


def test_pc13_04_05_invalid_source_geometry_yields_no_candidates() -> None:
    resolver = CandidateCarrierResolver()
    assert resolver.candidates(_decoded_source(16, rate=0), allow_adaptation=True) == ()
    assert (
        resolver.candidates(_decoded_source(16, channels=0), allow_adaptation=True)
        == ()
    )


def test_pc13_04_06_twenty_four_bit_candidates_are_deterministic() -> None:
    resolver = CandidateCarrierResolver()
    first = resolver.candidates(_decoded_source(24), allow_adaptation=True)
    second = resolver.candidates(_decoded_source(24), allow_adaptation=True)
    assert first == second
    assert [item.tuple.transport_format for item in first] == ["S32_LE"]
    assert first[0].tuple.significant_bits == 24


def test_pc13_04_07_candidate_set_is_bounded_and_priority_ordered() -> None:
    resolver = CandidateCarrierResolver()
    resolved = resolver.candidates(_decoded_source(16), allow_adaptation=True)
    assert len(resolved) <= resolver.MAX_CANDIDATES
    assert [item.priority for item in resolved] == sorted(
        item.priority for item in resolved
    )
    assert resolved[0].is_exact


def test_pc13_04_08_carrier_tuple_returns_the_exact_candidate_only() -> None:
    from michi.application.audio_output_planner import carrier_tuple

    source = _decoded_source(16)
    assert (
        carrier_tuple(source)
        == CandidateCarrierResolver()
        .candidates(source, allow_adaptation=False)[0]
        .tuple
    )
    assert carrier_tuple(_decoded_source(None)) is None


# ── Phase 5 — compatible Direct (bounded container adaptation) ─────────────


class _SplitProbe:
    """Exact-open adapter that rejects S16_LE and opens S32_LE."""

    def __init__(self, rejected=("S16_LE",)) -> None:
        self.rejected = tuple(rejected)
        self.calls: list[tuple[int, str, int]] = []

    def probe_exact(self, **kwargs):
        rate_hz = kwargs["rate_hz"]
        transport_format = kwargs["transport_format"]
        channels = kwargs["channels"]
        self.calls.append((rate_hz, transport_format, channels))
        requested = PcmTuple(rate_hz, transport_format, channels, 16)
        if transport_format in self.rejected:
            return ExactProbeResult(
                requested,
                None,
                "unsupported_format",
                22,
                "ALSA rechazó exactamente",
                f"probe:reject:{transport_format}",
            )
        negotiated = PcmTuple(rate_hz, transport_format, channels, 32)
        return ExactProbeResult(
            requested,
            negotiated,
            "OPENED",
            None,
            None,
            f"probe:open:{transport_format}",
        )


def _s16_graph(tmp_path: Path, probe, *, preseed: bool = False):
    from michi.domain.library import TrackMetadata

    graph, bindings = _direct_graph(
        tmp_path,
        qualification_adapter=probe,
        preseed_qualification=preseed,
        source_metadata=TrackMetadata(
            title="S16 source",
            sample_rate_hz=44_100,
            bit_depth=16,
            channels=2,
        ),
    )
    bindings.source_characterization_overrides = {
        "format": "S16LE",
        "rate": 44_100,
        "significant_bits": 16,
        "channels": 2,
    }
    return graph, bindings


def _wait_until(predicate, *, timeout_s: float = 3.0) -> bool:
    import time

    from PySide6.QtCore import QCoreApplication

    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if predicate():
            return True
        QCoreApplication.processEvents()
        time.sleep(0.01)
    return bool(predicate())


def _wait_for_pipeline(bindings, graph, timeout_s: float = 3.0) -> None:
    import time

    from PySide6.QtCore import QCoreApplication

    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline and not bindings.pipelines:
        QCoreApplication.processEvents()
        time.sleep(0.01)
    assert bindings.pipelines, graph.playback.state.error_message


def test_pc13_05_01_strict_direct_refuses_when_exact_carrier_is_rejected(
    qapp, tmp_path: Path
) -> None:
    probe = _SplitProbe()
    graph, bindings = _s16_graph(tmp_path, probe)
    try:
        graph.playback.load_and_play(tmp_path / "strict16.flac")
        assert _wait_until(lambda: bool(probe.calls)), "no exact probe happened"
        assert _wait_until(lambda: bool(graph.playback.state.error_message)), (
            "the strict refusal was never contained"
        )

        assert probe.calls == [(44_100, "S16_LE", 2)]
        assert graph.output_session.mode == "shared"
        assert graph.playback.state.file_path is None
        assert "Format unsupported" in graph.playback.state.error_message
        assert bindings.pipelines == []
    finally:
        _close_graph(graph)


def test_pc13_05_02_compatible_selects_the_wider_lossless_carrier(
    qapp, tmp_path: Path
) -> None:
    probe = _SplitProbe()
    graph, bindings = _s16_graph(tmp_path, probe)
    try:
        _coordinator(graph).select_path_mode("compatible")
        graph.playback.load_and_play(tmp_path / "compatible16.flac")
        _wait_for_pipeline(bindings, graph)

        assert probe.calls == [(44_100, "S16_LE", 2), (44_100, "S32_LE", 2)]
        plan = graph.output_session.plan
        assert plan is not None
        assert plan.requested_pcm.transport_format == "S32_LE"
        assert plan.requested_pcm.significant_bits == 16
        assert plan.carrier_adaptation == "container_width"
        assert "CONTAINER_WIDTH_ADAPTED" in plan.decision_codes
        recipe = bindings.built_recipes[-1]
        assert recipe.container_conversion is True
        assert recipe.gst_format == "S32LE"
    finally:
        _close_graph(graph)


def test_pc13_05_03_compatible_prefers_the_exact_carrier_when_proven(
    qapp, tmp_path: Path
) -> None:
    probe = _SplitProbe(rejected=())
    graph, bindings = _s16_graph(tmp_path, probe)
    try:
        _coordinator(graph).select_path_mode("compatible")
        graph.playback.load_and_play(tmp_path / "exact16.flac")
        _wait_for_pipeline(bindings, graph)

        # The exact carrier opens first: no adaptation is attempted.
        assert probe.calls == [(44_100, "S16_LE", 2)]
        plan = graph.output_session.plan
        assert plan is not None
        assert plan.requested_pcm.transport_format == "S16_LE"
        assert plan.carrier_adaptation == "exact"
        assert bindings.built_recipes[-1].container_conversion is False
    finally:
        _close_graph(graph)


def test_pc13_05_04_all_carriers_rejected_is_not_a_device_claim(
    qapp, tmp_path: Path
) -> None:
    probe = _SplitProbe(rejected=("S16_LE", "S32_LE"))
    graph, bindings = _s16_graph(tmp_path, probe)
    try:
        _coordinator(graph).select_path_mode("compatible")
        graph.playback.load_and_play(tmp_path / "incompatible16.flac")
        assert _wait_until(lambda: len(probe.calls) == 2), (
            "the compatible carrier sweep did not complete"
        )
        assert _wait_until(lambda: bool(graph.playback.state.error_message)), (
            "the compatible refusal was never contained"
        )

        assert probe.calls == [(44_100, "S16_LE", 2), (44_100, "S32_LE", 2)]
        assert graph.output_session.mode == "shared"
        assert graph.playback.state.file_path is None
        assert bindings.pipelines == []
        # A tuple-scoped refusal must never be presented as a dead device.
        assert "not available" not in graph.playback.state.error_message
        assert graph.playback.state.error_message.startswith(
            ("No compatible Direct format", "Format unsupported")
        )
        assert graph.playback.state.error_code == "NO_COMPATIBLE_CARRIER"
    finally:
        _close_graph(graph)


def test_pc13_05_05_strict_never_probes_an_adaptation_candidate(
    qapp, tmp_path: Path
) -> None:
    probe = _SplitProbe(rejected=("S16_LE", "S32_LE"))
    graph, bindings = _s16_graph(tmp_path, probe)
    try:
        graph.playback.load_and_play(tmp_path / "strict-only.flac")
        assert _wait_until(lambda: bool(probe.calls))

        assert [call[1] for call in probe.calls] == ["S16_LE"]
        assert bindings.built_recipes == []
    finally:
        _close_graph(graph)


def test_pc13_05_06_recipe_authorizes_conversion_only_from_the_plan() -> None:
    from michi.infrastructure.audio_output.strict_sink import (
        StrictSinkError,
        recipe_from_plan,
    )

    graph_plan = _plan_with_adaptation("container_width")
    recipe = recipe_from_plan(graph_plan)
    assert recipe.container_conversion is True

    exact_recipe = recipe_from_plan(_plan_with_adaptation("exact"))
    assert exact_recipe.container_conversion is False

    invalid = _plan_with_adaptation("dsp")
    with pytest.raises(StrictSinkError) as exc_info:
        recipe_from_plan(invalid)
    assert exc_info.value.code == "DIRECT_PLAN_INVALID"


def test_pc13_05_07_signal_truth_reports_16_bit_container_adaptation() -> None:
    from michi.domain.signal_truth import (
        AlsaRuntimeEvidence,
        DecodedRuntimeEvidence,
        EngineRuntimeEvidence,
        OutputPlanEvidence,
        SignalTruthIdentity,
        SignalTruthReason,
        SignalTruthRecorder,
        SignalTruthVerdict,
    )

    identity = SignalTruthIdentity("plan:16", 1, 1, 1, "usb:dac", "ep:0")
    decoded = PcmTuple(44_100, "S16_LE", 2, 16)
    carrier = PcmTuple(44_100, "S32_LE", 2, 16)
    recorder = SignalTruthRecorder()
    recorder.begin_candidate(
        OutputPlanEvidence(identity, carrier, "alsasink", "hw:CARD=X,DEV=0", True)
    )
    recorder.observe(DecodedRuntimeEvidence(identity, decoded))
    recorder.observe(
        EngineRuntimeEvidence(
            identity=identity,
            effective_pcm=carrier,
            sink_factory="alsasink",
            sink_device="hw:CARD=X,DEV=0",
            graph_factories=("flacdec", "audioconvert", "capsfilter", "alsasink"),
            graph_inspection_complete=True,
            software_gain=1.0,
            muted=False,
            sink_provides_clock=True,
            sink_clock_is_pipeline_clock=True,
            slave_method="none",
        )
    )
    recorder.observe(
        AlsaRuntimeEvidence(
            identity=identity,
            negotiated_pcm=carrier,
            access="RW_INTERLEAVED",
            subformat="STD",
            period_size=1024,
            buffer_size=4096,
            proc_path="/proc/asound/card1/pcm0p/sub0/hw_params",
            locator="hw:CARD=X,DEV=0",
        )
    )
    assert recorder.commit_candidate(identity)
    snapshot = recorder.active_snapshot
    assert snapshot is not None
    assert snapshot.verdict is SignalTruthVerdict.DIRECT_CONTAINER_ADAPTED
    assert snapshot.reasons == (SignalTruthReason.ST_CONTAINER_ADAPTED,)


def test_pc13_05_08_unauthorized_format_change_is_never_adapted() -> None:
    from michi.domain.signal_truth import (
        AlsaRuntimeEvidence,
        DecodedRuntimeEvidence,
        EngineRuntimeEvidence,
        OutputPlanEvidence,
        SignalTruthIdentity,
        SignalTruthRecorder,
        SignalTruthVerdict,
    )

    identity = SignalTruthIdentity("plan:bad", 1, 1, 1, "usb:dac", "ep:0")
    decoded = PcmTuple(44_100, "S16_LE", 2, 16)
    # The plan itself requested the narrow carrier: a wider negotiated format
    # is then an unauthorized transform, never a container adaptation.
    recorder = SignalTruthRecorder()
    recorder.begin_candidate(
        OutputPlanEvidence(identity, decoded, "alsasink", "hw:CARD=X,DEV=0", True)
    )
    recorder.observe(DecodedRuntimeEvidence(identity, decoded))
    recorder.observe(
        EngineRuntimeEvidence(
            identity=identity,
            effective_pcm=PcmTuple(44_100, "S32_LE", 2, 16),
            sink_factory="alsasink",
            sink_device="hw:CARD=X,DEV=0",
            graph_factories=("flacdec", "audioconvert", "capsfilter", "alsasink"),
            graph_inspection_complete=True,
            software_gain=1.0,
            muted=False,
            sink_provides_clock=True,
            sink_clock_is_pipeline_clock=True,
            slave_method="none",
        )
    )
    recorder.observe(
        AlsaRuntimeEvidence(
            identity=identity,
            negotiated_pcm=PcmTuple(44_100, "S32_LE", 2, 16),
            access="RW_INTERLEAVED",
            subformat="STD",
            period_size=1024,
            buffer_size=4096,
            proc_path="/proc/asound/card1/pcm0p/sub0/hw_params",
            locator="hw:CARD=X,DEV=0",
        )
    )
    assert recorder.candidate_snapshot.verdict is SignalTruthVerdict.DSP


def test_pc13_05_09_single_flight_coalesces_concurrent_equivalent_probes() -> None:
    import threading

    from michi.application.dac_qualification_service import DacQualificationService

    calls: list[dict] = []
    release = threading.Event()

    class _SlowProbe:
        def probe_exact(self, **kwargs):
            calls.append(kwargs)
            release.wait(timeout=10)
            requested = PcmTuple(
                kwargs["rate_hz"], kwargs["transport_format"], kwargs["channels"], 16
            )
            return ExactProbeResult(
                requested, requested, "OPENED", None, None, "probe:single"
            )

    service = DacQualificationService(_SlowProbe(), environment_fingerprint=lambda: "e")
    results: list[object] = []
    lock = threading.Lock()

    def worker() -> None:
        outcome = service.probe_for_play(
            stable_device_id="usb:dac",
            locator="hw:CARD=X,DEV=0",
            rate_hz=44_100,
            transport_format="S16_LE",
            channels=2,
        )
        with lock:
            results.append(outcome)

    threads = [threading.Thread(target=worker) for _ in range(100)]
    for thread in threads:
        thread.start()
    import time

    time.sleep(0.3)
    release.set()
    for thread in threads:
        thread.join(timeout=15)

    assert len(calls) == 1
    assert len(results) == 100
    assert all(item is not None for item in results)


def test_pc13_05_10_real_converter_preserves_sixteen_bit_values_exactly() -> None:
    """The production converter contract is proven sample-level on real Gst."""
    import random
    import struct

    import gi

    gi.require_version("Gst", "1.0")
    gi.require_version("GstApp", "1.0")
    from gi.repository import Gst, GstApp  # noqa: F401 — registers appsrc surface

    from michi.infrastructure.audio_engines.gstreamer import GStreamerBindings

    Gst.init(None)
    bindings = GStreamerBindings()
    pipeline = Gst.Pipeline.new("r13-container-adaptation")
    appsrc = Gst.ElementFactory.make("appsrc", "src")
    converter = bindings._build_container_converter(Gst)
    capsfilter = Gst.ElementFactory.make("capsfilter", "caps")
    capsfilter.set_property(
        "caps",
        Gst.Caps.from_string(
            "audio/x-raw,format=S32LE,rate=44100,channels=2,layout=interleaved"
        ),
    )
    sink = Gst.ElementFactory.make("appsink", "sink")
    for element in (appsrc, converter, capsfilter, sink):
        pipeline.add(element)
    assert appsrc.link(converter)
    assert converter.link(capsfilter)
    assert capsfilter.link(sink)
    appsrc.set_property(
        "caps",
        Gst.Caps.from_string(
            "audio/x-raw,format=S16LE,rate=44100,channels=2,layout=interleaved"
        ),
    )

    random.seed(13)
    vectors = [0, 1, -1, 32767, -32768]
    vectors += [32767 if index % 2 else -32768 for index in range(8)]
    vectors += [random.randint(-32768, 32767) for _ in range(64)]
    frames = b"".join(struct.pack("<hh", value, value) for value in vectors)

    pipeline.set_state(Gst.State.PLAYING)
    assert appsrc.push_buffer(Gst.Buffer.new_wrapped(frames)) == Gst.FlowReturn.OK
    appsrc.end_of_stream()
    sample = sink.try_pull_sample(Gst.SECOND * 10)
    pipeline.set_state(Gst.State.NULL)
    assert sample is not None

    buffer = sample.get_buffer()
    ok, info = buffer.map(Gst.MapFlags.READ)
    assert ok
    data = bytes(info.data)
    buffer.unmap(info)
    observed = struct.unpack(f"<{len(data) // 4}i", data)
    expected = tuple(value << 16 for value in vectors for _ in range(2))
    assert observed == expected
    # The original significant value is exactly recoverable.
    assert tuple(value >> 16 for value in observed[::2]) == tuple(vectors)


# ── Phase 6 — output failure presentation and recovery intents ─────────────


def _bridge_graph():
    from tests.test_v35_090_audio_output_bridge import _graph, _select_direct

    return _graph(), _select_direct


def _publish_playback_failure(graph, code: str) -> None:
    graph.playback.state.error_message = "raw playback copy"
    graph.playback.state.error_code = code
    graph.playback.publish()


def test_pc13_06_01_playback_refusal_reaches_the_output_ui() -> None:
    graph, _select = _bridge_graph()

    _publish_playback_failure(graph, "EXACT_TUPLE_UNSUPPORTED")

    assert graph.bridge.lastFailureCode == "EXACT_TUPLE_UNSUPPORTED"
    assert graph.bridge.lastFailureTitle == "Format unsupported"
    assert graph.bridge.lastFailureDisplay.startswith(
        "The selected DAC rejected this exact format"
    )
    # Never the raw internal code as the primary copy.
    assert "EXACT_TUPLE_UNSUPPORTED" not in graph.bridge.lastFailureDisplay
    assert "EXACT_TUPLE_UNSUPPORTED" not in graph.bridge.lastFailureTitle


def test_pc13_06_02_strict_incompatibility_offers_explicit_recovery() -> None:
    graph, _select = _bridge_graph()

    _publish_playback_failure(graph, "EXACT_TUPLE_UNSUPPORTED")

    actions = [row["action"] for row in graph.bridge.outputRecoveryActions]
    labels = [row["label"] for row in graph.bridge.outputRecoveryActions]
    assert actions == ["try_compatible_direct", "use_shared", "cancel"]
    assert labels == ["Try Compatible Direct", "Use Shared", "Cancel"]


def test_pc13_06_03_no_compatible_carrier_offers_shared_or_cancel() -> None:
    graph, _select = _bridge_graph()

    _publish_playback_failure(graph, "NO_COMPATIBLE_CARRIER")

    assert graph.bridge.lastFailureTitle == "No compatible Direct format"
    assert [row["action"] for row in graph.bridge.outputRecoveryActions] == [
        "use_shared",
        "cancel",
    ]


def test_pc13_06_04_busy_and_disconnected_never_claim_unsupported_format() -> None:
    for code, expected_title in (
        ("ALSA_DEVICE_BUSY", "Device busy"),
        ("OUTPUT_DEVICE_LOST", "Device disconnected"),
        ("ENGINE_UNSUPPORTED_FOR_DIRECT", "Direct requires GStreamer"),
        ("EXACT_QUALIFICATION_TIMEOUT", "Format check timed out"),
        ("EXACT_QUALIFICATION_INCONCLUSIVE", "Format check inconclusive"),
        ("EXACT_QUALIFICATION_STALE", "DAC connection changed"),
    ):
        graph, _select = _bridge_graph()
        _publish_playback_failure(graph, code)
        assert graph.bridge.lastFailureTitle == expected_title, code
        actions = [row["action"] for row in graph.bridge.outputRecoveryActions]
        assert actions == ["use_shared", "cancel"], code


def test_pc13_06_05_refusal_never_switches_policy_automatically() -> None:
    graph, select_direct = _bridge_graph()
    select_direct(graph)
    before = graph.repository.selection

    _publish_playback_failure(graph, "EXACT_TUPLE_UNSUPPORTED")

    assert graph.repository.selection == before
    assert graph.bridge.selectedPathMode == "strict"


def test_pc13_06_06_try_compatible_direct_is_explicit_and_user_driven() -> None:
    graph, select_direct = _bridge_graph()
    select_direct(graph)

    graph.bridge.try_compatible_direct()

    assert graph.bridge.selectedPathMode == "compatible"
    assert graph.bridge.lastFailureTitle == ""


def test_pc13_06_07_dismiss_clears_the_presented_failure() -> None:
    graph, _select = _bridge_graph()
    graph.bridge.select_device("unknown-device")
    assert graph.bridge.lastFailureTitle != ""

    graph.bridge.dismiss_output_failure()

    assert graph.bridge.lastFailureCode == ""
    assert graph.bridge.lastFailureTitle == ""


def test_pc13_06_08_one_intent_prepares_output_exactly_once(
    qapp, tmp_path: Path
) -> None:
    probe = _SplitProbe()
    graph, bindings = _s16_graph(tmp_path, probe)
    calls: list[str] = []
    original = graph.output_session.prepare_for_media_async

    def counted(path, on_prepared, on_failed):
        calls.append(str(path))
        return original(path, on_prepared, on_failed)

    graph.output_session.prepare_for_media_async = counted
    try:
        from michi.domain.playback_session import PlaybackSequenceEntry

        graph.playback_session.play_single(
            PlaybackSequenceEntry(tmp_path / "one-intent.flac", "One intent")
        )
        assert _wait_until(lambda: bool(probe.calls)), "no probe happened"

        assert len(calls) == 1
        # One physical probe per authorized candidate — never a brute-force sweep.
        assert probe.calls == [(44_100, "S16_LE", 2)]
        assert bindings.pipelines == []
    finally:
        _close_graph(graph)


# ── Phase 7 — native lifecycle hardening ───────────────────────────────────


class _ManualContext:
    """GLib-like context whose queued callbacks dispatch only on demand.

    ``immediate`` models a healthy pump; ``False`` models a wedged one whose
    queued callbacks only run when the pump finally recovers.
    """

    def __init__(self, *, immediate: bool = False) -> None:
        self.immediate = immediate
        self.queued: list = []

    def invoke_full(self, _priority, callback, _user_data) -> None:
        if self.immediate:
            callback(None)
            return
        self.queued.append(callback)

    def dispatch_all(self) -> None:
        pending, self.queued = self.queued, []
        for callback in pending:
            callback(None)


def _bindings():
    from michi.infrastructure.audio_engines.gstreamer import GStreamerBindings

    return GStreamerBindings()


def test_pc13_07_01_context_command_dispatch_success() -> None:
    from michi.infrastructure.audio_engines.gstreamer import (
        ContextCommand,
        ContextCommandState,
    )

    bindings = _bindings()
    context = _ManualContext(immediate=True)
    command = ContextCommand("c-success", 1)

    value = bindings.invoke_context_sync(
        context, lambda: 42, timeout_s=2.0, command=command
    )

    assert value == 42
    assert command.state is ContextCommandState.COMPLETED


def test_pc13_07_02_context_command_returns_the_callback_failure() -> None:
    from michi.infrastructure.audio_engines.gstreamer import ContextCommand

    bindings = _bindings()
    context = _ManualContext(immediate=True)

    def failing():
        raise ValueError("synthetic command failure")

    with pytest.raises(ValueError, match="synthetic command failure"):
        bindings.invoke_context_sync(
            context, failing, timeout_s=2.0, command=ContextCommand("c-fail", 1)
        )


def test_pc13_07_03_timeout_abandons_the_queued_command() -> None:
    from michi.infrastructure.audio_engines.gstreamer import (
        ContextCommand,
        ContextCommandState,
        ContextCommandTimeoutError,
    )

    bindings = _bindings()
    context = _ManualContext()
    command = ContextCommand("c-timeout", 3)
    mutations: list[str] = []

    with pytest.raises(ContextCommandTimeoutError):
        bindings.invoke_context_sync(
            context,
            lambda: mutations.append("stale mutation"),
            timeout_s=0.05,
            command=command,
        )

    assert command.state is ContextCommandState.ABANDONED
    # The wedged pump finally recovers and dispatches the queued callback.
    context.dispatch_all()
    assert mutations == []
    assert command.state is ContextCommandState.ABANDONED


def test_pc13_07_04_delayed_pump_recovery_then_new_command_succeeds() -> None:
    from michi.infrastructure.audio_engines.gstreamer import (
        ContextCommand,
        ContextCommandTimeoutError,
    )

    bindings = _bindings()
    context = _ManualContext()
    stale: list[str] = []

    with pytest.raises(ContextCommandTimeoutError):
        bindings.invoke_context_sync(
            context,
            lambda: stale.append("stale"),
            timeout_s=0.05,
            command=ContextCommand("c-stale", 4),
        )

    # The pump recovers, drains the abandoned callback, then serves a fresh one.
    context.dispatch_all()
    assert stale == []
    context.immediate = True

    value = bindings.invoke_context_sync(
        context,
        lambda: "fresh",
        timeout_s=2.0,
        command=ContextCommand("c-fresh", 5),
    )
    assert value == "fresh"


def test_pc13_07_05_started_command_is_never_abandoned() -> None:
    from michi.infrastructure.audio_engines.gstreamer import (
        ContextCommand,
        ContextCommandState,
    )

    command = ContextCommand("c-running", 6)
    assert command.claim() is True
    assert command.state is ContextCommandState.RUNNING
    # A command that already started owns its mutation: it cannot be abandoned.
    assert command.abandon() is False
    assert command.state is ContextCommandState.RUNNING
    command.complete()
    assert command.state is ContextCommandState.COMPLETED


def test_pc13_07_06_close_release_failure_is_not_a_faked_closure() -> None:
    from michi.infrastructure.audio_engines.gstreamer import GStreamerAudioPort
    from tests.test_gstreamer_audio_port import FakeBindings

    class _FailingExecutor:
        handle = None

        def __init__(self) -> None:
            self.releases: list[str] = []
            self.fail = True

        def release(self, reason: str) -> None:
            self.releases.append(reason)
            if self.fail:
                raise RuntimeError("synthetic release failure")

    bindings = FakeBindings()
    executor = _FailingExecutor()
    port = GStreamerAudioPort(bindings=bindings, direct_executor=executor)
    try:
        with pytest.raises(RuntimeError, match="synthetic release failure"):
            port.close()
        assert port._closed is False
        assert executor.releases == ["gstreamer_close"]

        executor.fail = False
        port.close()
        assert port._closed is True
        assert executor.releases == ["gstreamer_close", "gstreamer_close"]
    finally:
        if not port._closed:
            executor.fail = False
            port.close()


def test_pc13_07_07_close_keeps_the_first_error_when_release_also_fails() -> None:
    from michi.infrastructure.audio_engines.gstreamer import GStreamerAudioPort
    from tests.test_gstreamer_audio_port import FakeBindings

    class _FailingExecutor:
        handle = None

        def release(self, _reason: str) -> None:
            raise RuntimeError("secondary release failure")

        def mark_previous_source_released(self) -> None:
            return None

        def abort(self, *_args, **_kwargs):
            return None

        def record_runtime_anomaly(self, *_args, **_kwargs) -> None:
            return None

        def discard_staged_load(self, *_args, **_kwargs) -> None:
            return None

    bindings = FakeBindings()
    port = GStreamerAudioPort(bindings=bindings, direct_executor=_FailingExecutor())
    port.load(Path("/tmp/r13-first-error.flac"))
    # Primary failure: the pump never terminates (pump + direct-release combo).
    bindings.ignore_quit = True
    try:
        with pytest.raises(Exception) as exc_info:  # noqa: PT011 — typed below
            port.close()
        # The first chronological failure wins; the release error is secondary.
        assert str(exc_info.value) != "secondary release failure"
        assert port._closed is False
    finally:
        import contextlib

        bindings.ignore_quit = False
        if not port._closed:
            with contextlib.suppress(Exception):
                port.close()


def test_pc13_07_08_nested_drain_requires_explicit_harness_lifecycle(
    qapp, tmp_path: Path
) -> None:
    from michi.bootstrap import ApplicationContainer, ContainerLifecycle

    class _Signal:
        def connect(self, _callback) -> None:
            return None

    class _Engine:
        def __init__(self) -> None:
            self.deleted = 0
            self.destroyed = _Signal()

        def deleteLater(self):  # noqa: N802 — Qt API name
            self.deleted += 1

    container = ApplicationContainer()
    container._engine = _Engine()
    container._lifecycle = ContainerLifecycle.MAIN_LOOP_RUNNING

    scheduled: list[str] = []
    container._schedule_qml_teardown()
    assert container._engine is None  # teardown is still scheduled

    # The bounded drain is only authorized before the main loop ever ran.
    assert container._lifecycle is not ContainerLifecycle.INITIALIZED, (
        "a running GUI loop must never be treated as harness mode"
    )
    scheduled.clear()


def test_pc13_07_09_every_context_property_is_retained_for_teardown() -> None:
    """R1.3 §18 parity: registered context properties stay alive until Qt ends."""
    from michi.bootstrap import ApplicationContainer

    container = ApplicationContainer()

    class _Obj:
        def __init__(self) -> None:
            self.deleted = 0

        def deleteLater(self):  # noqa: N802 — Qt API name
            self.deleted += 1

    class _Engine(_Obj):
        pass

    engine = _Engine()
    container._engine = engine
    for name in (
        "_pb",
        "_qb",
        "_psb",
        "_lb",
        "_plb",
        "_nb",
        "_sb",
        "_aeb",
        "_aob",
        "_eb",
        "_library_enrichment",
    ):
        setattr(container, name, _Obj())

    container._schedule_qml_teardown()

    retained = container._qml_teardown_keepalive
    assert engine in retained
    for name in (
        "_pb",
        "_qb",
        "_psb",
        "_lb",
        "_plb",
        "_nb",
        "_sb",
        "_aeb",
        "_aob",
        "_eb",
        "_library_enrichment",
    ):
        assert getattr(container, name) in retained, name


# ── Phase 8 — qualification evidence matrix ────────────────────────────────


class _TimeoutProbe:
    def probe_exact(self, **kwargs):
        requested = PcmTuple(
            kwargs["rate_hz"], kwargs["transport_format"], kwargs["channels"], 16
        )
        return ExactProbeResult(
            requested, None, "timeout", None, "probe timed out", "probe:timeout"
        )


def test_pc13_08_01_qualification_timeout_is_typed_and_never_cached(
    qapp, tmp_path: Path
) -> None:
    probe = _TimeoutProbe()
    graph, bindings = _s16_graph(tmp_path, probe)
    try:
        graph.playback.load_and_play(tmp_path / "timeout16.flac")
        assert _wait_until(lambda: bool(graph.playback.state.error_message)), (
            "the timeout refusal was never contained"
        )

        assert graph.playback.state.error_code == "EXACT_QUALIFICATION_TIMEOUT"
        assert graph.playback.state.error_message.startswith("Format check timed out")
        # TIMEOUT is ambiguity, never a capability claim.
        assert (
            graph.dac_qualification.cached_evidence_current("usb:2622:0105:DX5ABC123")
            == ()
        )
        assert graph.output_session.mode == "shared"
        assert bindings.pipelines == []
    finally:
        _close_graph(graph)


def test_pc13_08_02_owner_revalidation_rejects_a_stale_environment(
    qapp, tmp_path: Path
) -> None:
    from michi.application.dac_qualification_service import ExactQualificationOutcome
    from michi.application.output_session_service import OutputSessionError
    from michi.domain.audio_evidence import CapabilityEvidence, EvidenceStrength

    probe = _SplitProbe(rejected=())
    graph, _bindings = _s16_graph(tmp_path, probe)
    try:
        resolver = graph.output_session._request_provider
        request = resolver(tmp_path / "stale.flac")
        stale_outcome = ExactQualificationOutcome(
            CapabilityEvidence(
                stable_device_id="usb:2622:0105:DX5ABC123",
                tuple=PcmTuple(44_100, "S16_LE", 2, 16),
                supported=True,
                strength=EvidenceStrength.OPENED,
                source="michi-alsa-probe",
                observed_at_ns=1,
                environment_fingerprint="qenv:v2:sha256:stale",
                evidence_refs=("probe:stale",),
            ),
            "OPENED",
            None,
        )

        with pytest.raises(OutputSessionError) as exc_info:
            resolver.apply_qualification(request, stale_outcome)

        assert exc_info.value.code == "EXACT_QUALIFICATION_STALE"
        assert (
            graph.dac_qualification.cached_evidence_current("usb:2622:0105:DX5ABC123")
            == ()
        )
    finally:
        _close_graph(graph)
