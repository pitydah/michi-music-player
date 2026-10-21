"""AP2-F06 — DEFINITIVE productive Managed PCM flow.

The whole chain is exercised through `_build_services`: fake Linux/ALSA
topology -> qualification evidence -> selection coordinator -> persisted
profile -> ProductiveOutputRequestResolver -> OutputSessionService ->
ManagedPcmExecutor -> AudioProcessingService -> real GStreamer host ->
selected binding (lab sink) -> runtime readback -> Signal Truth.
"""

from __future__ import annotations

import importlib.util
import time
from pathlib import Path

import pytest

_HAS_GI = importlib.util.find_spec("gi") is not None

pytestmark = pytest.mark.skipif(
    not _HAS_GI, reason="PyGObject/GStreamer not available on this host"
)

FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "evidence/dac-v35-110/2026-09-25-smsl-152a85dd-operator-run"
    / "fixtures/pcm16_44100.wav"
)
DEVICE_ID = "usb:2622:0105:DX5ABC123"


class _InlineExecutor:
    def submit(self, work, completed) -> None:
        try:
            value = work()
        except Exception as exc:  # noqa: BLE001 - typed boundary
            completed(None, exc)
        else:
            completed(value, None)


class _Metadata:
    def extract(self, path):
        from michi.domain.library import TrackMetadata

        return TrackMetadata(
            title=Path(path).stem,
            sample_rate_hz=44_100,
            bit_depth=16,
            channels=2,
        )


class _ExactOpeningProbe:
    def probe_exact(self, **kwargs):
        from michi.domain.audio_evidence import ExactProbeResult, PcmTuple

        significant_bits = 24 if kwargs["transport_format"] == "S32_LE" else 16
        requested = PcmTuple(
            kwargs["rate_hz"],
            kwargs["transport_format"],
            kwargs["channels"],
            significant_bits,
        )
        return ExactProbeResult(
            requested, requested, "OPENED", None, None, "probe:test-exact-open"
        )


def _build_graph(tmp_path, **service_kwargs):
    from michi.application.audio_output_selection_coordinator import (
        AudioOutputSelectionCoordinator,
    )
    from michi.bootstrap import _build_services
    from michi.domain.audio_engine import AudioEngineId
    from michi.domain.audio_evidence import (
        CapabilityEvidence,
        EvidenceStrength,
        PcmTuple,
    )
    from tests.dac._fixtures import (
        AlsaCard,
        UsbDevice,
        build_linux_sysfs,
        make_roots,
    )

    topology = tmp_path / "topology"
    topology.mkdir()
    sysfs = make_roots(topology)
    build_linux_sysfs(
        sysfs,
        usb_devices=(
            UsbDevice("2-1", "2622", "0105", serial="DX5ABC123", bcd_device="0100"),
        ),
        cards=(AlsaCard(1, "DX5", usb_devpath="2-1", playback_pcms=(0,)),),
    )
    proc = topology / "proc" / "asound"
    card_root = proc / "card1"
    card_root.mkdir(parents=True)
    (card_root / "id").write_text("DX5\n", encoding="utf-8")
    sub = card_root / "pcm0p" / "sub0"
    sub.mkdir(parents=True)
    (sub / "hw_params").write_text("closed\n", encoding="utf-8")

    graph = _build_services(
        tmp_path / "michi.db",
        startup_selected_engine=AudioEngineId.GSTREAMER,
        metadata_extractor=_Metadata(),
        artwork_provider=None,
        artwork_cache=None,
        audio_sysfs_root=sysfs,
        alsa_proc_root=proc,
        qualification_adapter=_ExactOpeningProbe(),
        output_preparation_executor=_InlineExecutor(),
        **service_kwargs,
    )
    graph.dac_qualification.cache_evidence(
        DEVICE_ID,
        (
            CapabilityEvidence(
                stable_device_id=DEVICE_ID,
                tuple=PcmTuple(44_100, "S16_LE", 2, 16),
                supported=True,
                strength=EvidenceStrength.OPENED,
                source="michi-alsa-probe",
                observed_at_ns=1,
                environment_fingerprint=(
                    graph.dac_qualification.current_environment_fingerprint(DEVICE_ID)
                ),
                evidence_refs=("probe:productive",),
            ),
        ),
    )
    coordinator = AudioOutputSelectionCoordinator(
        profiles=graph.audio_output_profiles,
        devices=graph.audio_device_registry,
        output_session=graph.output_session,
        engines=graph.audio_engine_service,
    )
    graph.audio_engine_convergence.converge_startup()
    assert graph.audio_engine_service.state.active_engine_id is not None
    return graph, coordinator


def _close(graph) -> None:
    graph.output_session.release_active("test")
    graph.audio_engine_convergence.shutdown()
    if graph.audio_router.bound_engine_id is not None:
        graph.audio_router.unbind()
    provider = graph.gstreamer_engine_provider
    if provider.current_port is not None:
        provider.close()


def _prepare(graph):
    tokens: list[str] = []
    failures: list[Exception] = []
    graph.output_session.prepare_for_media_async(
        FIXTURE, tokens.append, failures.append
    )
    return tokens, failures


def _binding_locator(graph) -> str:
    from michi.domain.audio_device import BindingKind

    (binding,) = graph.audio_device_registry.bindings_for(
        DEVICE_ID, BindingKind.ALSA_PCM
    )
    return binding.locator


def _select_managed(coordinator) -> None:
    coordinator.select_device(DEVICE_ID)
    coordinator.select_path_mode("managed")
    profile = next(
        item
        for item in coordinator._profiles.load_profiles()
        if item.profile_id == coordinator._profiles.load_selection().selected_profile_id
    )
    assert profile.path.value == "managed"
    assert profile.stable_device_id == DEVICE_ID


def test_managed_identity_route_through_the_productive_composition(
    tmp_path, monkeypatch
) -> None:
    if not FIXTURE.is_file():
        pytest.skip("PCM fixture unavailable")
    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    graph, coordinator = _build_graph(tmp_path)
    try:
        _select_managed(coordinator)
        graph.set_processing_profile(None)
        tokens, failures = _prepare(graph)
        assert failures == [], failures
        assert tokens, "production preparation produced no token"
        assert graph.output_session.mode == "managed"
        assert graph.output_session.state.value == "ready"

        graph.output_session.commit_media(tokens[0], FIXTURE)
        assert graph.output_session.state.value == "running"

        port = graph.gstreamer_engine_provider.current_port
        identity = port.query_managed_identity()
        assert identity["managed"] is True
        assert identity["loaded"] is True
        assert identity["device"] == _binding_locator(graph)
        assert identity["execution_id"]
        assert identity["evidence_level"] == "gstreamer_negotiated"
        assert identity["negotiated"]["rate_hz"] == 44_100
        # Real Gst.Query path: a VALID numeric answer with provenance.
        latency = identity["pipeline_latency"]
        assert latency is not None, "the Gst.Query latency path returned nothing"
        assert latency["source"] == "gstreamer_runtime"
        assert latency["measurement_type"] == "pipeline_reported"
        assert isinstance(latency["min_ns"], int) and latency["min_ns"] >= 0
        assert latency["max_ns"] is None or (
            isinstance(latency["max_ns"], int) and latency["max_ns"] >= 0
        )
        value_ns = latency["min_ns"]
        if value_ns is None:
            value_ns = latency["max_ns"]
        assert identity["pipeline_latency_ns"] == value_ns
        assert identity["pipeline_latency_samples"] == round(value_ns * 44_100 / 1e9)
        # Identity route: no processing filter exists, so the DSP capture
        # diagnostic is not applicable (it must never fake one).
        assert graph.audio_processing.effective_state.value != "effective"

        truth = graph.signal_truth.output_family_events
        assert truth and truth[-1].state.value == "running"
        assert all(event.bit_perfect is None for event in truth)

        graph.output_session.release_active("stop")
        assert graph.output_session.state.value == "idle"
    finally:
        _close(graph)


def test_managed_dsp_preset_runs_through_the_productive_provider(
    tmp_path, monkeypatch
) -> None:
    if not FIXTURE.is_file():
        pytest.skip("PCM fixture unavailable")
    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    from michi.domain.audio_processing import (
        PreampNode,
        ProcessingGraph,
        ProcessingProfile,
    )

    graph, coordinator = _build_graph(tmp_path)
    try:
        _select_managed(coordinator)
        graph.set_processing_profile(
            ProcessingProfile(
                profile_id="dsp:preamp",
                display_name="Preamp",
                graph=ProcessingGraph(
                    graph_id="graph:managed-preamp",
                    revision=1,
                    nodes=(PreampNode(node_id="pre", gain_db=-6.0),),
                ),
            )
        )
        tokens, failures = _prepare(graph)
        assert failures == [], failures
        graph.output_session.commit_media(tokens[0], FIXTURE)
        assert graph.output_session.state.value == "running"
        assert graph.audio_processing.effective_state.value == "effective"
        truth = graph.audio_processing.processing_truth()
        assert truth["bit_perfect"] is False
        effective_plan = truth["effective_plan_id"]

        # A NEW preset must be installed by a new managed preparation and
        # never reuse the previous graph identity.
        graph.set_processing_profile(
            ProcessingProfile(
                profile_id="dsp:preamp2",
                display_name="Preamp 2",
                graph=ProcessingGraph(
                    graph_id="graph:managed-preamp",
                    revision=2,
                    nodes=(PreampNode(node_id="pre", gain_db=-3.0),),
                ),
            )
        )
        tokens2, failures2 = _prepare(graph)
        assert failures2 == [], failures2
        graph.output_session.commit_media(tokens2[0], FIXTURE)
        assert graph.audio_processing.effective_state.value == "effective"
        assert graph.audio_processing.processing_truth()["effective_plan_id"] != (
            effective_plan
        )
        port = graph.gstreamer_engine_provider.current_port
        identity = port.query_managed_identity()
        assert identity["managed"] is True
        # Component-level lab capture (the session-level capture is isolated:
        # it races PlaybackService convergence; see WU3 in the evidence).
        metrics = port.capture_processing_output(0.4)
        assert metrics["rms"] > 0.0
    finally:
        _close(graph)


def test_managed_device_loss_retires_the_route_and_the_scope(
    tmp_path, monkeypatch
) -> None:
    if not FIXTURE.is_file():
        pytest.skip("PCM fixture unavailable")
    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    graph, coordinator = _build_graph(tmp_path)
    try:
        _select_managed(coordinator)
        tokens, failures = _prepare(graph)
        assert failures == []
        graph.output_session.commit_media(tokens[0], FIXTURE)
        assert graph.output_session.state.value == "running"

        graph.output_session.device_lost(DEVICE_ID, 9)
        assert graph.output_session.state.value == "lost"
        assert graph.output_session.mode == "lost"
        port = graph.gstreamer_engine_provider.current_port
        if port is not None:
            identity = port.query_managed_identity()
            assert identity.get("managed") is False
        assert graph.audio_processing.effective_state.value != "effective"
        events = graph.signal_truth.output_family_events
        assert events[-1].state.value == "unavailable"
    finally:
        _close(graph)


def test_stop_managed_is_identity_bound(tmp_path, monkeypatch) -> None:
    """An older completion can never stop a newer managed execution."""
    if not FIXTURE.is_file():
        pytest.skip("PCM fixture unavailable")
    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    graph, coordinator = _build_graph(tmp_path)
    try:
        _select_managed(coordinator)
        tokens, failures = _prepare(graph)
        assert failures == []
        graph.output_session.commit_media(tokens[0], FIXTURE)
        port = graph.gstreamer_engine_provider.current_port
        identity = port.query_managed_identity()
        locator = _binding_locator(graph)

        stale = port.stop_managed_execution(
            {
                "plan_id": "managed:other",
                "execution_id": "execution:other",
                "device": locator,
            }
        )
        assert stale["stopped"] is False and stale["stale"] is True
        still = port.query_managed_identity()
        assert still["managed"] is True and still["loaded"] is True

        current = port.stop_managed_execution(
            {
                "plan_id": identity["plan_id"],
                "execution_id": identity["execution_id"],
                "device": identity["device"],
            }
        )
        assert current["stopped"] is True
        stopped = port.query_managed_identity()
        assert stopped.get("managed") is False
    finally:
        _close(graph)


@pytest.mark.parametrize(
    ("supported", "tuple_override"),
    [
        (None, None),  # UNKNOWN is not SUPPORTED
        (True, (96_000, "S16_LE", 2, 16)),  # another rate does not qualify
    ],
)
def test_managed_requires_exact_positive_terminal_evidence(
    tmp_path, monkeypatch, supported, tuple_override
) -> None:
    if not FIXTURE.is_file():
        pytest.skip("PCM fixture unavailable")
    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    from michi.domain.audio_evidence import (
        CapabilityEvidence,
        EvidenceStrength,
        PcmTuple,
    )

    graph, coordinator = _build_graph(tmp_path)
    try:
        _select_managed(coordinator)
        pcm = (
            PcmTuple(*tuple_override)
            if tuple_override is not None
            else PcmTuple(44_100, "S16_LE", 2, 16)
        )
        graph.dac_qualification.cache_evidence(
            DEVICE_ID,
            (
                CapabilityEvidence(
                    stable_device_id=DEVICE_ID,
                    tuple=pcm,
                    supported=supported,
                    strength=EvidenceStrength.DECLARED,
                    source="test-inconclusive",
                    observed_at_ns=1,
                    environment_fingerprint=(
                        graph.dac_qualification.current_environment_fingerprint(
                            DEVICE_ID
                        )
                    ),
                    evidence_refs=("test",),
                ),
            ),
        )
        tokens, failures = _prepare(graph)
        assert tokens == []
        assert failures, "inconclusive evidence must never prepare Managed"
        assert failures[0].code == "MANAGED_TERMINAL_EVIDENCE_UNAVAILABLE"
        assert graph.output_session.mode != "managed"
        assert graph.output_session.state.value != "running"
    finally:
        _close(graph)


def test_host_sigkill_retires_managed_truth(tmp_path, monkeypatch) -> None:
    if not FIXTURE.is_file():
        pytest.skip("PCM fixture unavailable")
    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    import os
    import signal

    from michi.domain.audio_processing import (
        PreampNode,
        ProcessingGraph,
        ProcessingProfile,
    )

    graph, coordinator = _build_graph(tmp_path)
    try:
        _select_managed(coordinator)
        graph.set_processing_profile(
            ProcessingProfile(
                profile_id="dsp:host-kill",
                display_name="Preamp",
                graph=ProcessingGraph(
                    graph_id="graph:host-kill",
                    revision=1,
                    nodes=(PreampNode(node_id="pre", gain_db=-6.0),),
                ),
            )
        )
        tokens, failures = _prepare(graph)
        assert failures == []
        graph.output_session.commit_media(tokens[0], FIXTURE)
        assert graph.output_session.state.value == "running"
        assert graph.audio_processing.effective_state.value == "effective"

        supervisor = graph.gstreamer_engine_provider.current_supervisor
        pid = supervisor.pid
        assert pid, "the supervised host has no pid"
        os.kill(pid, signal.SIGKILL)

        port = graph.gstreamer_engine_provider.current_port
        deadline = time.monotonic() + 20.0
        while time.monotonic() < deadline:
            # The hosted port commits host-loss on its owner queue.
            port.dispatch_pending()
            if (
                graph.audio_processing.processing_truth()["effective_state"]
                != "effective"
            ):
                break
            time.sleep(0.05)
        truth = graph.audio_processing.processing_truth()
        assert truth["effective_state"] != "effective"
        assert truth["capability_state"] == "unavailable"
        assert truth["host_lost_reason"] is not None
        # F06 audit: the Signal Path truth retires via the host-loss listener
        # BEFORE any session release can happen.
        active_execution = graph.output_session.active_execution_id
        family_events = graph.signal_truth.output_family_events
        unavailable = [
            event
            for event in family_events
            if event.state.value == "unavailable"
            and event.execution_id == active_execution
        ]
        assert unavailable, family_events
        assert unavailable[-1].detail is not None

        # A stale session command cannot resurrect the route or crash the
        # owner: the port is gone, so cleanup is diagnostic-only.
        graph.output_session.release_active("host_lost")
        assert graph.output_session.state.value == "idle"
        assert graph.output_session.mode == "shared"
    finally:
        _close(graph)


def test_identical_plans_get_distinct_instances_and_old_stop_is_stale(
    tmp_path, monkeypatch
) -> None:
    """A→B with the SAME plan/file/DAC: the old instance can never stop B."""
    if not FIXTURE.is_file():
        pytest.skip("PCM fixture unavailable")
    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    from michi.domain.audio_processing import (
        PreampNode,
        ProcessingGraph,
        ProcessingProfile,
    )

    graph, coordinator = _build_graph(tmp_path)
    try:
        _select_managed(coordinator)
        graph.set_processing_profile(
            ProcessingProfile(
                profile_id="dsp:same",
                display_name="Same plan",
                graph=ProcessingGraph(
                    graph_id="graph:same-plan",
                    revision=1,
                    nodes=(PreampNode(node_id="pre", gain_db=-6.0),),
                ),
            )
        )
        locator = _binding_locator(graph)
        tokens_a, failures_a = _prepare(graph)
        assert failures_a == []
        graph.output_session.commit_media(tokens_a[0], FIXTURE)
        port = graph.gstreamer_engine_provider.current_port
        identity_a = port.query_managed_identity()
        assert identity_a["execution_id"].startswith("exec-instance:")
        plan_id = identity_a["plan_id"]

        graph.output_session.release_active("stop")
        tokens_b, failures_b = _prepare(graph)
        assert failures_b == []
        graph.output_session.commit_media(tokens_b[0], FIXTURE)
        identity_b = port.query_managed_identity()
        assert identity_b["plan_id"] == plan_id, "the plan identity must stay stable"
        assert identity_b["execution_id"] != identity_a["execution_id"]
        assert graph.audio_processing.effective_state.value == "effective"

        stale = port.stop_managed_execution(
            {
                "plan_id": plan_id,
                "execution_id": identity_a["execution_id"],
                "device": locator,
            }
        )
        assert stale["stopped"] is False and stale["stale"] is True
        still_b = port.query_managed_identity()
        assert still_b["managed"] is True and still_b["loaded"] is True
        assert graph.audio_processing.effective_state.value == "effective"

        stopped = port.stop_managed_execution(
            {
                "plan_id": plan_id,
                "execution_id": identity_b["execution_id"],
                "device": locator,
            }
        )
        assert stopped["stopped"] is True
        assert port.query_managed_identity().get("managed") is False
        duplicate = port.stop_managed_execution(
            {
                "plan_id": plan_id,
                "execution_id": identity_b["execution_id"],
                "device": locator,
            }
        )
        assert duplicate["stopped"] is False and duplicate["stale"] is True
    finally:
        _close(graph)


def test_dynamic_peq_reconfiguration_through_the_productive_session(
    tmp_path, monkeypatch
) -> None:
    """PEQ A -> PEQ B -> bypass on the SAME managed session: new plan
    identities, fresh execution instances, no stale EFFECTIVE."""
    if not FIXTURE.is_file():
        pytest.skip("PCM fixture unavailable")
    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    from michi.domain.audio_processing import (
        BiquadType,
        ParametricEqNode,
        PeqBand,
        ProcessingGraph,
        ProcessingProfile,
    )

    graph, coordinator = _build_graph(tmp_path)
    try:
        _select_managed(coordinator)

        def peq_profile(gain_db: float, revision: int) -> ProcessingProfile:
            return ProcessingProfile(
                profile_id=f"dsp:peq-{revision}",
                display_name="PEQ",
                graph=ProcessingGraph(
                    graph_id="graph:dynamic-peq",
                    revision=revision,
                    nodes=(
                        ParametricEqNode(
                            node_id="peq",
                            bands=(
                                PeqBand(
                                    "b1",
                                    BiquadType.PEAK,
                                    1000.0,
                                    1.4,
                                    gain_db,
                                    True,
                                ),
                            ),
                        ),
                    ),
                ),
            )

        def prepare_and_commit(path) -> None:
            tokens: list[str] = []
            failures: list[Exception] = []
            graph.output_session.prepare_for_media_async(
                path, tokens.append, failures.append
            )
            assert failures == [], failures
            graph.output_session.commit_media(tokens[0], path)
            assert graph.output_session.state.value == "running"

        plan_ids: list[str] = []
        instances: list[str] = []
        for gain, revision in ((0.0, 1), (6.0, 2), (-6.0, 3)):
            graph.set_processing_profile(peq_profile(gain, revision))
            prepare_and_commit(FIXTURE)
            truth = graph.audio_processing.processing_truth()
            assert truth["effective_state"] == "effective"
            assert truth["readback_proven"] is True
            plan_ids.append(truth["effective_plan_id"])
            instances.append(
                graph.gstreamer_engine_provider.current_port.query_managed_identity()[
                    "execution_id"
                ]
            )
        assert len(set(plan_ids)) == 3, plan_ids
        assert len(set(instances)) == 3, instances
        assert plan_ids[0] != plan_ids[1] != plan_ids[2]

        # DSP disabled: identity route, stale EFFECTIVE retired.
        graph.set_processing_profile(None)
        prepare_and_commit(FIXTURE)
        truth = graph.audio_processing.processing_truth()
        assert truth["effective_state"] != "effective"
        assert truth["readback_proven"] is False
        assert truth["latency"]["expected_samples"] is None
        identity = graph.gstreamer_engine_provider.current_port.query_managed_identity()
        assert identity["managed"] is True and identity["loaded"] is True
    finally:
        _close(graph)


def test_host_unavailable_before_managed_prepare_fails_typed(
    tmp_path, monkeypatch
) -> None:
    """Managed requires a live host. A controlled host close (the supported
    'not open' state) must fail typed, never prepare.

    SIGKILL during an ACTIVE managed session is covered separately
    (test_host_sigkill_retires_managed_truth), where fallback is forbidden.
    """
    if not FIXTURE.is_file():
        pytest.skip("PCM fixture unavailable")
    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")

    graph, coordinator = _build_graph(tmp_path)
    try:
        _select_managed(coordinator)
        graph.gstreamer_engine_provider.close()

        tokens, failures = _prepare(graph)
        assert tokens == []
        assert failures, "an unavailable host must never prepare successfully"
        assert graph.output_session.state.value != "running"
        assert graph.audio_processing.processing_truth()["effective_state"] != (
            "effective"
        )
        # Cleanup after a dead host is diagnostic-only and never raises.
        graph.output_session.release_active("host_lost")
        assert graph.output_session.state.value == "idle"
    finally:
        _close(graph)


def test_managed_44k_source_resampled_to_96k_with_exact_evidence(
    tmp_path, monkeypatch
) -> None:
    """44.1k SOURCE -> explicit 96k resample -> Managed sink; evidence must be
    for 96k (44.1 evidence alone is refused)."""
    if not FIXTURE.is_file():
        pytest.skip("PCM fixture unavailable")
    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    from michi.domain.audio_evidence import (
        CapabilityEvidence,
        EvidenceStrength,
        PcmTuple,
    )
    from michi.domain.audio_processing import (
        PreampNode,
        ProcessingGraph,
        ProcessingProfile,
        ResampleNode,
        ResampleQuality,
    )

    graph, coordinator = _build_graph(tmp_path)
    try:
        _select_managed(coordinator)
        graph.set_processing_profile(
            ProcessingProfile(
                profile_id="dsp:resample-96k",
                display_name="Resample 96k",
                graph=ProcessingGraph(
                    graph_id="graph:managed-resample",
                    revision=1,
                    nodes=(
                        PreampNode(node_id="pre", gain_db=0.0),
                        ResampleNode(
                            node_id="rs",
                            target_rate_hz=96000,
                            quality=ResampleQuality.HIGH,
                        ),
                    ),
                ),
            )
        )
        # Only 44.1k evidence: the 96k terminal format is NOT proven.
        tokens, failures = _prepare(graph)
        assert tokens == []
        assert failures and (
            failures[0].code == "MANAGED_TERMINAL_EVIDENCE_UNAVAILABLE"
        ), failures
        assert graph.output_session.state.value != "running"

        # Positive evidence for the OUTPUT rate (96k) is required.
        fingerprint = graph.dac_qualification.current_environment_fingerprint(DEVICE_ID)
        graph.dac_qualification.cache_evidence(
            DEVICE_ID,
            (
                CapabilityEvidence(
                    stable_device_id=DEVICE_ID,
                    tuple=PcmTuple(44_100, "S16_LE", 2, 16),
                    supported=True,
                    strength=EvidenceStrength.OPENED,
                    source="test",
                    observed_at_ns=1,
                    environment_fingerprint=fingerprint,
                    evidence_refs=("test",),
                ),
                CapabilityEvidence(
                    stable_device_id=DEVICE_ID,
                    tuple=PcmTuple(96_000, "S16_LE", 2, 16),
                    supported=True,
                    strength=EvidenceStrength.OPENED,
                    source="test",
                    observed_at_ns=2,
                    environment_fingerprint=fingerprint,
                    evidence_refs=("test",),
                ),
            ),
        )
        tokens, failures = _prepare(graph)
        assert failures == [], failures
        graph.output_session.commit_media(tokens[0], FIXTURE)
        assert graph.output_session.state.value == "running"
        port = graph.gstreamer_engine_provider.current_port
        identity = port.query_managed_identity()
        assert identity["managed"] is True and identity["loaded"] is True
        assert identity["negotiated"]["rate_hz"] == 96000
        assert graph.audio_processing.effective_state.value == "effective"
    finally:
        _close(graph)


def test_flat_vs_resample_pipeline_latency_is_measured(tmp_path, monkeypatch) -> None:
    """WU6: report the measured pipeline latency per execution (never inferred
    from the resample preset)."""
    if not FIXTURE.is_file():
        pytest.skip("PCM fixture unavailable")
    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    from michi.domain.audio_evidence import (
        CapabilityEvidence,
        EvidenceStrength,
        PcmTuple,
    )
    from michi.domain.audio_processing import (
        PreampNode,
        ProcessingGraph,
        ProcessingProfile,
        ResampleNode,
        ResampleQuality,
    )

    graph, coordinator = _build_graph(tmp_path)
    try:
        _select_managed(coordinator)
        fingerprint = graph.dac_qualification.current_environment_fingerprint(DEVICE_ID)
        graph.dac_qualification.cache_evidence(
            DEVICE_ID,
            tuple(
                CapabilityEvidence(
                    stable_device_id=DEVICE_ID,
                    tuple=PcmTuple(rate, "S16_LE", 2, 16),
                    supported=True,
                    strength=EvidenceStrength.OPENED,
                    source="test",
                    observed_at_ns=index,
                    environment_fingerprint=fingerprint,
                    evidence_refs=("test",),
                )
                for index, rate in enumerate((44_100, 48_000), start=1)
            ),
        )

        def run(profile):
            graph.set_processing_profile(profile)
            tokens, failures = _prepare(graph)
            assert failures == [], failures
            graph.output_session.commit_media(tokens[0], FIXTURE)
            identity = (
                graph.gstreamer_engine_provider.current_port.query_managed_identity()
            )
            latency = identity["pipeline_latency"]
            assert latency is not None
            assert isinstance(latency["min_ns"], int)
            return latency

        flat = run(
            ProcessingProfile(
                profile_id="dsp:lat-flat",
                display_name="Flat",
                graph=ProcessingGraph(
                    graph_id="graph:lat",
                    revision=1,
                    nodes=(PreampNode(node_id="pre", gain_db=0.0),),
                ),
            )
        )
        resampled = run(
            ProcessingProfile(
                profile_id="dsp:lat-rs",
                display_name="Resample",
                graph=ProcessingGraph(
                    graph_id="graph:lat",
                    revision=2,
                    nodes=(
                        PreampNode(node_id="pre", gain_db=0.0),
                        ResampleNode(
                            node_id="rs",
                            target_rate_hz=48000,
                            quality=ResampleQuality.HIGH,
                        ),
                    ),
                ),
            )
        )
        # Real measured values; the difference is reported, not modeled.
        assert flat["source"] == "gstreamer_runtime"
        assert resampled["source"] == "gstreamer_runtime"
        delta_ns = resampled["min_ns"] - flat["min_ns"]
        assert isinstance(delta_ns, int)
        assert delta_ns >= 0
        graph.output_session.release_active("stop")
    finally:
        _close(graph)


def test_repeated_managed_transitions_do_not_leak_or_publish_stale_state(
    tmp_path, monkeypatch
) -> None:
    """WU9: repeated preset transitions keep identities, memory and truth
    bounded."""
    if not FIXTURE.is_file():
        pytest.skip("PCM fixture unavailable")
    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    from michi.domain.audio_processing import (
        BiquadType,
        ParametricEqNode,
        PeqBand,
        PreampNode,
        ProcessingGraph,
        ProcessingProfile,
    )

    graph, coordinator = _build_graph(tmp_path)
    try:
        _select_managed(coordinator)

        def profile(index: int) -> ProcessingProfile:
            if index % 2 == 0:
                nodes = (PreampNode(node_id="pre", gain_db=0.0),)
            else:
                nodes = (
                    ParametricEqNode(
                        node_id="peq",
                        bands=(PeqBand("b", BiquadType.PEAK, 1000.0, 1.4, 3.0, True),),
                    ),
                )
            return ProcessingProfile(
                profile_id=f"dsp:repeat-{index}",
                display_name="Repeat",
                graph=ProcessingGraph(
                    graph_id="graph:repeat",
                    revision=index + 1,
                    nodes=nodes,
                ),
            )

        instances: list[str] = []
        for index in range(8):
            graph.set_processing_profile(profile(index))
            tokens: list[str] = []
            failures: list[Exception] = []
            graph.output_session.prepare_for_media_async(
                FIXTURE, tokens.append, failures.append
            )
            assert failures == [], failures
            graph.output_session.commit_media(tokens[0], FIXTURE)
            assert graph.output_session.state.value == "running"
            assert graph.audio_processing.effective_state.value == "effective"
            instances.append(
                graph.gstreamer_engine_provider.current_port.query_managed_identity()[
                    "execution_id"
                ]
            )
        assert len(set(instances)) == 8
        assert graph.audio_processing._prepared_plans == {}
        assert graph.signal_truth.processing_measurements == ()
        graph.output_session.release_active("stop")
        assert graph.output_session.state.value == "idle"
        assert graph.output_session._managed_prepared is None
        assert graph.signal_truth.processing_measurements == ()
    finally:
        _close(graph)
