"""AP2-F03 — family-neutral signal path projection over classified Signal Truth.

Contract anchors: R11-F03 (pure projection, Direct parity first), R11-G02
(authority map: SignalTruthRecorder owns runtime truth), §189 (acceptance:
missing evidence visible, Qt/MPD NOT_OBSERVABLE honest, provenance per node).

The projection must map every classified ``SignalTruthSnapshot`` 1:1: same
verdict, same ordered reason codes, no dropped reason, no invented positive
fact, and no node silently absent in a way that implies success.
"""

from __future__ import annotations

import ast
import dataclasses
import json
import sys
from pathlib import Path

import pytest

from michi.application.signal_path_service import SignalPathService
from michi.domain.audio_evidence import PcmTuple, RuntimeTransformEvidence
from michi.domain.signal_path import (
    SignalPathIdentity,
    SignalPathNodeKind,
    SignalPathNodeState,
    SignalPathProjectionError,
    SignalPathSnapshot,
)
from michi.domain.signal_truth import (
    AlsaRuntimeEvidence,
    DecodedRuntimeEvidence,
    EngineRuntimeEvidence,
    OutputPlanEvidence,
    RuntimeAnomalyEvidence,
    RuntimeAnomalyKind,
    SignalTruthIdentity,
    SignalTruthReason,
    SignalTruthSnapshot,
    SignalTruthVerdict,
    SourceFileFactsEvidence,
    classify_signal_truth,
)

DOMAIN_MODULE = Path(sys.modules["michi.domain.signal_path"].__file__)
SERVICE_MODULE = Path(sys.modules["michi.application.signal_path_service"].__file__)

_PLAN_ID = "plan:ap2f03"
_SINK_FACTORY = "alsasink"
_SINK_DEVICE = "hw:CARD=AP2F03,DEV=0"


def _identity(
    *, execution: int = 1, port: int = 1, binding: int = 1, plan_id: str = _PLAN_ID
):
    return SignalTruthIdentity(
        plan_id=plan_id,
        execution_generation=execution,
        port_generation=port,
        binding_generation=binding,
        stable_device_id="usb:152a:85dd:3-3.3.2",
        stable_endpoint_signature="usb-interface:1.0:pcm:0:sub:0",
    )


def _pcm(
    *, rate: int = 96000, fmt: str = "S32LE", channels: int = 2, bits: int | None = 24
):
    return PcmTuple(
        rate_hz=rate, transport_format=fmt, channels=channels, significant_bits=bits
    )


def _plan(identity, pcm) -> OutputPlanEvidence:
    return OutputPlanEvidence(
        identity=identity,
        requested_pcm=pcm,
        sink_factory=_SINK_FACTORY,
        sink_device=_SINK_DEVICE,
        fixed_gain_required=True,
    )


def _source(identity, pcm) -> SourceFileFactsEvidence:
    return SourceFileFactsEvidence(
        identity=identity, container="wav", codec="pcm_s24le", nominal_pcm=pcm
    )


def _decoded(identity, pcm) -> DecodedRuntimeEvidence:
    return DecodedRuntimeEvidence(identity=identity, pcm=pcm)


def _engine(
    identity,
    pcm,
    *,
    sink_factory: str = _SINK_FACTORY,
    sink_device: str = _SINK_DEVICE,
    graph_complete: bool = True,
    graph_factories: tuple[str, ...] = ("audioconvert",),
    software_gain: float | None = 1.0,
    muted: bool | None = False,
    sink_provides_clock: bool | None = True,
    sink_clock_is_pipeline_clock: bool | None = True,
    slave_method: str | None = "skew",
    resampling_observed: bool = False,
    remix_observed: bool = False,
    dsp_observed: bool = False,
    transforms: RuntimeTransformEvidence | None = None,
) -> EngineRuntimeEvidence:
    return EngineRuntimeEvidence(
        identity=identity,
        effective_pcm=pcm,
        sink_factory=sink_factory,
        sink_device=sink_device,
        graph_factories=graph_factories,
        graph_inspection_complete=graph_complete,
        software_gain=software_gain,
        muted=muted,
        sink_provides_clock=sink_provides_clock,
        sink_clock_is_pipeline_clock=sink_clock_is_pipeline_clock,
        slave_method=slave_method,
        resampling_observed=resampling_observed,
        remix_observed=remix_observed,
        dsp_observed=dsp_observed,
        transform_evidence=(
            transforms if transforms is not None else RuntimeTransformEvidence()
        ),
    )


def _alsa(identity, pcm, *, binding_matches: bool = True) -> AlsaRuntimeEvidence:
    return AlsaRuntimeEvidence(
        identity=identity,
        negotiated_pcm=pcm,
        access="rw",
        subformat="MSB",
        period_size=1024,
        buffer_size=4096,
        proc_path="/proc/asound/cardX/pcm0p/sub0/hw_params",
        binding_matches=binding_matches,
        locator="hw:CARD=AP2F03,DEV=0",
    )


def _classified(
    *,
    identity=None,
    plan=None,
    source=...,
    decoded=...,
    engine=...,
    alsa=...,
    anomalies=(),
):
    identity = identity or _identity()
    pcm = _pcm()
    plan = plan or _plan(identity, pcm)
    snapshot = SignalTruthSnapshot(
        identity=identity,
        plan=plan,
        source_file_facts=(_source(identity, pcm) if source is ... else source),
        decoded_runtime=_decoded(identity, pcm) if decoded is ... else decoded,
        engine_effective=_engine(identity, pcm) if engine is ... else engine,
        device_negotiated=_alsa(identity, pcm) if alsa is ... else alsa,
        anomalies=anomalies,
        verdict=SignalTruthVerdict.UNKNOWN,
        reasons=(),
    )
    return classify_signal_truth(snapshot)


# --------------------------------------------------------------------------- #
# verdict-family fixtures (built through the REAL classifier)
# --------------------------------------------------------------------------- #


def _direct() -> SignalTruthSnapshot:
    return _classified()


def _container_adapted() -> SignalTruthSnapshot:
    identity = _identity()
    decoded_pcm = _pcm(fmt="S24_3LE")
    carrier = _pcm(fmt="S32LE")
    return _classified(
        identity=identity,
        plan=_plan(identity, carrier),
        source=_source(identity, decoded_pcm),
        decoded=_decoded(identity, decoded_pcm),
        engine=_engine(
            identity,
            carrier,
            transforms=RuntimeTransformEvidence(
                converter_present=True,
                converter_transforming=True,
                converter_dithering_disabled=True,
                converter_noise_shaping_disabled=True,
                remix_transforming=False,
            ),
        ),
        alsa=_alsa(identity, carrier),
    )


def _dsp() -> SignalTruthSnapshot:
    identity = _identity()
    decoded_pcm = _pcm(fmt="S24_3LE")
    carrier = _pcm(fmt="S32LE")
    return _classified(
        identity=identity,
        plan=_plan(identity, carrier),
        source=_source(identity, decoded_pcm),
        decoded=_decoded(identity, decoded_pcm),
        engine=_engine(
            identity,
            carrier,
            transforms=RuntimeTransformEvidence(
                converter_present=True,
                converter_transforming=True,
                converter_dithering_disabled=False,
                converter_noise_shaping_disabled=False,
                remix_transforming=False,
            ),
        ),
        alsa=_alsa(identity, carrier),
    )


def _resampled() -> SignalTruthSnapshot:
    identity = _identity()
    decoded_pcm = _pcm(rate=44100, fmt="S32LE")
    engine_pcm = _pcm(rate=96000, fmt="S32LE")
    return _classified(
        identity=identity,
        plan=_plan(identity, engine_pcm),
        source=_source(identity, decoded_pcm),
        decoded=_decoded(identity, decoded_pcm),
        engine=_engine(identity, engine_pcm, resampling_observed=True),
        alsa=_alsa(identity, engine_pcm),
    )


def _remixed() -> SignalTruthSnapshot:
    identity = _identity()
    decoded_pcm = _pcm(channels=2, fmt="S32LE")
    engine_pcm = _pcm(channels=6, fmt="S32LE")
    return _classified(
        identity=identity,
        plan=_plan(identity, engine_pcm),
        source=_source(identity, decoded_pcm),
        decoded=_decoded(identity, decoded_pcm),
        engine=_engine(identity, engine_pcm, remix_observed=True),
        alsa=_alsa(identity, engine_pcm),
    )


def _contradicted() -> SignalTruthSnapshot:
    identity = _identity()
    return _classified(
        engine=_engine(identity, _pcm(), sink_device="hw:CARD=OTHER,DEV=0"),
    )


def _unknown() -> SignalTruthSnapshot:
    return _classified(
        source=None,
        decoded=None,
        engine=None,
        alsa=None,
    )


VERDICT_FIXTURES = (
    ("direct", _direct, SignalTruthVerdict.DIRECT),
    (
        "container_adapted",
        _container_adapted,
        SignalTruthVerdict.DIRECT_CONTAINER_ADAPTED,
    ),
    ("dsp", _dsp, SignalTruthVerdict.DSP),
    ("resampled", _resampled, SignalTruthVerdict.RESAMPLED),
    ("remixed", _remixed, SignalTruthVerdict.REMIXED),
    ("contradicted", _contradicted, SignalTruthVerdict.CONTRADICTED),
    ("unknown", _unknown, SignalTruthVerdict.UNKNOWN),
)


def _project(snapshot: SignalTruthSnapshot) -> SignalPathSnapshot:
    return SignalPathService().project(snapshot)


def _node(projection: SignalPathSnapshot, kind: str):
    node = projection.node(kind)
    assert node is not None, kind
    return node


def _imported_modules(source_path: Path) -> list[str]:
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            modules.append("." * node.level + (node.module or ""))
    return modules


# --------------------------------------------------------------------------- #
# structural projection
# --------------------------------------------------------------------------- #


def test_direct_projection_is_a_faithful_chain() -> None:
    snapshot = _direct()
    projection = _project(snapshot)
    assert [node.kind for node in projection.nodes] == [
        SignalPathNodeKind.SOURCE,
        SignalPathNodeKind.DECODE,
        SignalPathNodeKind.ENGINE,
        SignalPathNodeKind.DEVICE,
    ]
    assert [
        (edge.source_node_id, edge.target_node_id) for edge in projection.edges
    ] == [
        ("source", "decode"),
        ("decode", "engine"),
        ("engine", "device"),
    ]
    assert all(node.state is SignalPathNodeState.OBSERVED for node in projection.nodes)
    assert projection.verdict == "direct"
    assert projection.reasons == ()


def test_requested_and_effective_are_never_collapsed() -> None:
    snapshot = _resampled()
    projection = _project(snapshot)
    engine = _node(projection, "engine")
    requested = dict(engine.requested)
    effective = dict(engine.effective)
    assert requested["rate_hz"] == 96000
    assert effective["rate_hz"] == 96000
    decode = _node(projection, "decode")
    assert dict(decode.effective)["rate_hz"] == 44100


def test_rate_mismatch_without_resampler_is_contradicted() -> None:
    identity = _identity()
    decoded_pcm = _pcm(rate=44100, fmt="S32LE")
    engine_pcm = _pcm(rate=96000, fmt="S32LE")
    snapshot = _classified(
        identity=identity,
        plan=_plan(identity, engine_pcm),
        source=_source(identity, decoded_pcm),
        decoded=_decoded(identity, decoded_pcm),
        engine=_engine(identity, engine_pcm),
        alsa=_alsa(identity, engine_pcm),
    )
    assert snapshot.verdict is SignalTruthVerdict.CONTRADICTED
    projection = _project(snapshot)
    assert projection.verdict == "contradicted"
    engine = _node(projection, "engine")
    assert "ST_RATE_MISMATCH" in engine.reason_codes


def test_missing_evidence_nodes_stay_explicit() -> None:
    snapshot = _unknown()
    projection = _project(snapshot)
    assert len(projection.nodes) == 4
    states = {node.kind: node.state for node in projection.nodes}
    assert states[SignalPathNodeKind.SOURCE] is SignalPathNodeState.NOT_OBSERVED
    assert states[SignalPathNodeKind.DECODE] is SignalPathNodeState.NOT_OBSERVED
    assert states[SignalPathNodeKind.ENGINE] is SignalPathNodeState.NOT_OBSERVED
    assert states[SignalPathNodeKind.DEVICE] is SignalPathNodeState.NOT_OBSERVED
    assert projection.verdict == "unknown"
    assert "ST_MISSING_DECODED" in _node(projection, "decode").reason_codes
    assert "ST_MISSING_ALSA" in _node(projection, "device").reason_codes


def test_contradiction_marks_the_owning_node_conflicted() -> None:
    projection = _project(_contradicted())
    engine = _node(projection, "engine")
    assert engine.state is SignalPathNodeState.CONFLICTED
    assert "ST_DEVICE_MISMATCH" in engine.reason_codes


def test_xrun_conflicts_the_engine_node_with_anomaly_evidence() -> None:
    identity = _identity()
    snapshot = _classified(
        anomalies=(
            RuntimeAnomalyEvidence(
                identity=identity, kind=RuntimeAnomalyKind.XRUN, detail="snd_pcm"
            ),
        ),
    )
    projection = _project(snapshot)
    assert projection.verdict == "contradicted"
    engine = _node(projection, "engine")
    assert "ST_XRUN" in engine.reason_codes
    assert any(ref.endswith("#anomaly:xrun") for ref in engine.evidence_refs)


def test_binding_mismatch_conflicts_the_device_node() -> None:
    identity = _identity()
    snapshot = _classified(alsa=_alsa(identity, _pcm(), binding_matches=False))
    projection = _project(snapshot)
    device = _node(projection, "device")
    assert device.state is SignalPathNodeState.CONFLICTED
    assert "ST_BINDING_MISMATCH" in device.reason_codes


def test_significant_bits_unknown_is_explicit_on_decode() -> None:
    identity = _identity()
    snapshot = _classified(decoded=_decoded(identity, _pcm(bits=None)))
    assert snapshot.verdict is SignalTruthVerdict.UNKNOWN
    projection = _project(snapshot)
    assert "ST_SIGNIFICANT_BITS_UNKNOWN" in _node(projection, "decode").reason_codes


def test_dsp_present_is_projected() -> None:
    identity = _identity()
    snapshot = _classified(engine=_engine(identity, _pcm(), dsp_observed=True))
    assert snapshot.verdict is SignalTruthVerdict.DSP
    projection = _project(snapshot)
    assert projection.verdict == "dsp"
    assert "ST_DSP_PRESENT" in _node(projection, "engine").reason_codes


# --------------------------------------------------------------------------- #
# 1:1 parity for every verdict/reason family
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("name,builder,expected", VERDICT_FIXTURES)
def test_projection_maps_verdict_and_reasons_1to1(name, builder, expected) -> None:
    snapshot = builder()
    assert snapshot.verdict is expected, name
    projection = _project(snapshot)
    assert projection.verdict == snapshot.verdict.value
    assert projection.reasons == tuple(reason.value for reason in snapshot.reasons)


@pytest.mark.parametrize("name,builder,expected", VERDICT_FIXTURES)
def test_every_reason_lands_on_exactly_one_node_in_order(
    name, builder, expected
) -> None:
    snapshot = builder()
    projection = _project(snapshot)
    distributed: list[str] = []
    for node in projection.nodes:
        expected_codes = [
            reason.value
            for reason in snapshot.reasons
            if SignalPathService.PRIMARY_NODE_BY_REASON[reason] == node.kind
        ]
        assert node.reason_codes == tuple(expected_codes), (name, node.kind)
        distributed.extend(node.reason_codes)
    assert sorted(distributed) == sorted(reason.value for reason in snapshot.reasons)


def test_every_reason_has_a_primary_node() -> None:
    mapping = SignalPathService.PRIMARY_NODE_BY_REASON
    assert set(mapping) == set(SignalTruthReason)
    assert set(mapping.values()) == {
        SignalPathNodeKind.SOURCE,
        SignalPathNodeKind.DECODE,
        SignalPathNodeKind.ENGINE,
        SignalPathNodeKind.DEVICE,
    }


# --------------------------------------------------------------------------- #
# identity / generation safety
# --------------------------------------------------------------------------- #


def test_identity_mismatch_is_a_typed_refusal() -> None:
    identity = _identity()
    other = _identity(execution=2, plan_id="plan:other")
    snapshot = SignalTruthSnapshot(
        identity=identity,
        plan=_plan(identity, _pcm()),
        source_file_facts=_source(other, _pcm()),
        decoded_runtime=_decoded(identity, _pcm()),
        engine_effective=_engine(identity, _pcm()),
        device_negotiated=_alsa(identity, _pcm()),
        anomalies=(),
        verdict=SignalTruthVerdict.UNKNOWN,
        reasons=(),
    )
    with pytest.raises(SignalPathProjectionError):
        _project(snapshot)


def test_anomaly_identity_mismatch_is_a_typed_refusal() -> None:
    other = _identity(execution=3)
    snapshot = _classified(
        anomalies=(
            RuntimeAnomalyEvidence(identity=other, kind=RuntimeAnomalyKind.XRUN),
        ),
    )
    with pytest.raises(SignalPathProjectionError):
        _project(snapshot)


def test_projection_identity_mirrors_signal_truth_identity() -> None:
    snapshot = _direct()
    projection = _project(snapshot)
    assert projection.identity == SignalPathIdentity(
        plan_id=snapshot.identity.plan_id,
        execution_generation=snapshot.identity.execution_generation,
        port_generation=snapshot.identity.port_generation,
        binding_generation=snapshot.identity.binding_generation,
        stable_device_id=snapshot.identity.stable_device_id,
        stable_endpoint_signature=snapshot.identity.stable_endpoint_signature,
    )


# --------------------------------------------------------------------------- #
# determinism / immutability / serialization
# --------------------------------------------------------------------------- #


def test_projection_is_deterministic() -> None:
    builder = _direct
    first = _project(builder())
    second = _project(builder())
    assert first == second
    assert _project(builder()) == first


def test_nodes_and_snapshot_are_immutable() -> None:
    projection = _project(_direct())
    node = projection.nodes[0]
    with pytest.raises(dataclasses.FrozenInstanceError):
        node.label = "other"  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        projection.verdict = "other"  # type: ignore[misc]


def test_serialization_is_deterministic() -> None:
    first = json.dumps(_project(_direct()).to_dict(), sort_keys=True)
    second = json.dumps(_project(_direct()).to_dict(), sort_keys=True)
    assert first == second
    payload = json.loads(first)
    assert payload["verdict"] == "direct"
    assert [node["kind"] for node in payload["nodes"]] == [
        "source",
        "decode",
        "engine",
        "device",
    ]
    engine = next(node for node in payload["nodes"] if node["kind"] == "engine")
    assert engine["requested"]["rate_hz"] == 96000
    assert engine["effective"]["rate_hz"] == 96000


# --------------------------------------------------------------------------- #
# purity / execution-surface firewall
# --------------------------------------------------------------------------- #


def test_domain_module_imports_stay_pure() -> None:
    imports = _imported_modules(DOMAIN_MODULE)
    assert imports
    forbidden = (
        "PySide6",
        "gi",
        "Gst",
        "sqlite3",
        "ctypes",
        "michi.presentation",
        "michi.infrastructure",
        "michi.bootstrap",
        "michi.application",
    )
    for name in imports:
        assert not any(
            name == prefix or name.startswith(prefix + ".") for prefix in forbidden
        ), name
        top = name.split(".")[0]
        assert top in sys.stdlib_module_names or top == "michi", name
        if top == "michi":
            assert name == "michi.domain" or name.startswith("michi.domain."), name


def test_service_imports_no_presentation_or_execution_stack() -> None:
    imports = _imported_modules(SERVICE_MODULE)
    forbidden = (
        "PySide6",
        "gi",
        "Gst",
        "sqlite3",
        "michi.presentation",
        "michi.infrastructure",
        "michi.bootstrap",
    )
    for name in imports:
        assert not any(
            name == prefix or name.startswith(prefix + ".") for prefix in forbidden
        ), name
        if name.startswith("michi."):
            assert name.startswith("michi.domain"), name


def test_projection_has_no_execution_surface() -> None:
    service = SignalPathService()
    for name in (
        "play",
        "pause",
        "stop",
        "load",
        "set_state",
        "select_device",
        "apply",
    ):
        assert not hasattr(service, name), name
