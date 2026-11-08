"""A48 isolated P1 contract falsifiers; NOT product Qt/ALSA/physical tests."""

from __future__ import annotations

import json

import pytest

from michi.application.signal_truth_p1_capabilities import project_capabilities
from michi.application.signal_truth_p1_diagnostics import build_diagnostic_report
from michi.application.signal_truth_p1_metrics import MetricLedger, MetricObservation
from michi.application.signal_truth_p1_remote_receipts import (
    RemoteReceiptWindow,
    RemoteReport,
)
from michi.application.signal_truth_p1_scheduler import UiNotice, UiNoticeCoalescer
from michi.application.signal_truth_p1_ui import inspector_labels


def obs(
    metric="processing_speed",
    *,
    value=1.2,
    execution_id="exec-A",
    epoch=1,
    sequence=1,
    producer="processing_host",
    clock_domain="",
    missing_before=0,
):
    return MetricObservation(
        execution_id,
        epoch,
        metric,
        value,
        producer,
        sequence,
        clock_domain,
        missing_before,
    )


def test_metrics_unknown_without_producer():
    result = MetricLedger().snapshot()
    assert len(result) == 8
    assert all(x.state == "UNOBSERVED" and x.value is None for x in result.values())
    assert result["true_peak_dbtp"].producer == "true_peak_meter"
    assert result["sample_peak_dbfs"].producer == "pcm_meter"


def test_metrics_scope_and_epoch_revoke_history():
    ledger = MetricLedger()
    ledger.begin_execution("exec-A", 1)
    assert ledger.ingest(obs())
    assert not ledger.ingest(obs(execution_id="exec-B"))
    assert not ledger.ingest(obs(epoch=2))
    assert ledger.snapshot()["processing_speed"].state == "OBSERVED"
    ledger.begin_execution("exec-B", 2)
    assert ledger.snapshot()["processing_speed"].value is None
    ledger.retire()
    assert not ledger.ingest(obs(execution_id="exec-B", epoch=2))


@pytest.mark.parametrize(
    "bad",
    [
        {"epoch": 0},
        {"epoch": True},
        {"sequence": 0},
        {"sequence": True},
        {"value": float("nan")},
        {"value": float("inf")},
        {"metric": "clipped_samples", "value": 1.2, "producer": "pcm_meter"},
        {"metric": "xrun_events", "value": -1, "producer": "alsa_observer"},
        {"metric": "owner_to_ui_ms", "value": 1.2, "producer": "ui_observer"},
        {
            "metric": "frame_dispatch_ms",
            "value": -1,
            "producer": "ui_observer",
            "clock_domain": "MONOTONIC_SAME_DOMAIN",
        },
        {"metric": "true_peak_dbtp", "producer": "pcm_meter"},
        {"metric": "unknown"},
        {"metric": "processing_speed", "value": -1},
        {"missing_before": -1},
        {"execution_id": ""},
    ],
)
def test_metrics_negative_values(bad):
    with pytest.raises(ValueError):
        obs(**bad)


def test_metrics_continuity_and_dedup():
    led = MetricLedger()
    led.begin_execution("exec-A", 1)
    assert led.ingest(obs(sequence=1))
    assert not led.ingest(obs(sequence=1))
    assert led.ingest(obs(sequence=3, value=1.3, missing_before=2))
    row = led.snapshot()["processing_speed"]
    assert (
        row.state == "PARTIAL"
        and row.missing == 3
        and row.value == 1.3
        and row.count == 2
    )


def test_metrics_first_nonzero_sequence_is_not_claimed_complete():
    led = MetricLedger()
    led.begin_execution("exec-A", 1)
    led.ingest(obs(sequence=12))
    assert led.snapshot()["processing_speed"].missing == 11


def test_metrics_latency_percentiles_and_counter_not_summed():
    led = MetricLedger(max_samples=16)
    led.begin_execution("exec-A", 1)
    for i in range(1, 11):
        led.ingest(
            obs(
                metric="owner_to_ui_ms",
                producer="ui_observer",
                value=i,
                sequence=i,
                clock_domain="MONOTONIC_SAME_DOMAIN",
            )
        )
        led.ingest(
            obs(metric="xrun_events", producer="alsa_observer", value=i, sequence=i)
        )
    r = led.snapshot()
    assert r["owner_to_ui_ms"].p95 == 10 and r["owner_to_ui_ms"].p99 == 10
    assert r["xrun_events"].value == 10
    assert r["xrun_events"].p95 is None


@pytest.mark.parametrize("n", [0, 8, 2049, True])
def test_metrics_budget_refusal(n):
    with pytest.raises(ValueError):
        MetricLedger(max_samples=n)


def test_diagnostics_requires_explicit_consent():
    with pytest.raises(PermissionError):
        build_diagnostic_report(frame={}, consent=False)
    with pytest.raises(PermissionError):
        build_diagnostic_report(frame={}, consent=1)


def test_diagnostics_no_leaks_and_bounded_allowlist():
    private = "/home/persona/Música/secret/Álbum.flac"
    frame = {
        "status": "ACTIVE",
        "audioFamily": "dop",
        "fidelityClaim": "MATCHED_COMPLETE",
        "lastProvenBoundary": "USB_SUBMITTED",
        "reasonCodes": [
            "ST_DSP_PRESENT",
            "garbage",
            "ST_AUTH_password=secret",
            private,
            "F11_FAMILY_UNOBSERVED",
        ],
        "filename": private,
        "title": "secret pista",
        "token": "sk-proj-xxxxx",
        "device_id": "ABCD:SERIAL",
        "ip": "10.8.0.3",
        "operationCount": 4,
        "stageCount": 8,
    }
    metrics = {
        "xrun_events": {
            "state": "OBSERVED",
            "value": 2,
            "count": 1,
            "missing": 0,
            "path": private,
        }
    }
    output = build_diagnostic_report(
        frame=frame, metrics=metrics, consent=True, include_metric_samples=True
    )
    raw = json.dumps(output, ensure_ascii=False)
    for forbidden in (
        private,
        "Música",
        "secret pista",
        "sk-proj",
        "ABCD:SERIAL",
        "10.8.0.3",
        "garbage",
    ):
        assert forbidden not in raw
    assert output["physical_dac_verified"] is False
    assert output["fidelity_claim"] == "UNPROVEN"
    assert output["observed_boundary"] == "USB_SUBMITTED"
    assert len(raw.encode()) < 32768
    assert output["measurements"][0]["metric"] == "xrun_events"
    assert output["reasons"] == ["ST_DSP_PRESENT", "F11_FAMILY_UNOBSERVED"]


def test_diagnostics_no_pcm_or_out_of_range_metrics():
    raw = build_diagnostic_report(
        frame={"status": "HISTORICAL", "reasonCodes": "bad"},
        metrics={
            "sample_peak_dbfs": {"state": "OBSERVED", "value": float("nan")},
            "clipped_samples": {"state": "OBSERVED", "value": 1e50},
        },
        consent=True,
        include_metric_samples=True,
    )
    assert raw["scope"] == "HISTORICAL"
    assert raw["measurements"] == []  # historical metrics require separate owner proof
    assert raw["reasons"] == []


def test_diagnostics_nonjson_payload_ignored():
    class Trap:
        def __str__(self):
            raise RuntimeError("must not touch arbitrary values")

    output = build_diagnostic_report(
        frame={"source": Trap(), "rawPCM": Trap()}, consent=True
    )
    assert output["scope"] == "NOT_ACTIVE" and output["measurements"] == []


def remote(**change):
    fields = dict(
        schema_version=1,
        endpoint_id="opaque-endpoint",
        producer="michi_stream",
        route_epoch=3,
        sequence=4,
        issued_ms=1000,
        ttl_ms=2000,
        family="native_dsd",
        state="RUNNING",
    )
    fields.update(change)
    return RemoteReport(**fields)


def test_remote_absent_auth_not_adopted():
    r = RemoteReceiptWindow().consider(remote(), now_ms=1200)
    assert r.status == "UNOBSERVED" and r.boundary == "NONE"


def test_remote_report_never_physical_even_authenticated():
    led = RemoteReceiptWindow()
    r = led.consider(remote(), now_ms=1200, owner_authenticated=True)
    assert r.status == "REMOTE_REPORTED" and r.boundary == "REMOTE_REPORTED"
    assert r.reason == "ST_P1_REMOTE_SELF_REPORT_ONLY"
    assert (
        led.consider(remote(), now_ms=1200, owner_authenticated=True).reason
        == "ST_P1_REMOTE_REPLAY_OR_STALE"
    )
    assert (
        led.consider(remote(sequence=5), now_ms=1200, owner_authenticated=True).status
        == "REMOTE_REPORTED"
    )
    assert (
        led.consider(
            remote(route_epoch=4, sequence=1), now_ms=1200, owner_authenticated=True
        ).status
        == "REMOTE_REPORTED"
    )
    assert (
        led.consider(
            remote(route_epoch=3, sequence=100), now_ms=1200, owner_authenticated=True
        ).status
        == "UNOBSERVED"
    )


def test_remote_expiry_and_future_skew_and_owner_cap():
    led = RemoteReceiptWindow(max_endpoints=1)
    assert (
        led.consider(remote(), now_ms=3001, owner_authenticated=True).reason
        == "ST_P1_REMOTE_EXPIRED"
    )
    assert (
        led.consider(
            remote(issued_ms=3000), now_ms=1000, owner_authenticated=True
        ).reason
        == "ST_P1_REMOTE_FUTURE_CLOCK"
    )
    assert (
        led.consider(remote(), now_ms=1000, owner_authenticated=True).status
        == "REMOTE_REPORTED"
    )
    assert (
        led.consider(
            remote(endpoint_id="second", sequence=1),
            now_ms=1000,
            owner_authenticated=True,
        ).reason
        == "ST_P1_REMOTE_ENDPOINT_BUDGET"
    )


@pytest.mark.parametrize(
    "bad",
    [
        {"schema_version": 2},
        {"producer": "fake_server"},
        {"endpoint_id": ""},
        {"endpoint_id": "x\nsecret"},
        {"sequence": True},
        {"sequence": 0},
        {"route_epoch": -1},
        {"ttl_ms": 40000},
        {"family": "mp4"},
        {"state": "DAC_VERIFIED"},
    ],
)
def test_remote_rejects_malformed_or_forbidden(bad):
    with pytest.raises(ValueError):
        remote(**bad)


def test_remote_terminal_is_remote_only():
    r = RemoteReceiptWindow().consider(
        remote(state="RELEASED"), now_ms=1200, owner_authenticated=True
    )
    assert r.status == "REMOTE_TERMINATED" and r.boundary == "REMOTE_REPORTED"


def test_ui_temporal_and_fidelity_do_not_elevate():
    for status in ("PENDING", "HISTORICAL", "NOT_ACTIVE", "NONE"):
        labels = inspector_labels(
            {
                "status": status,
                "pathProofState": "verified",
                "fidelityClaim": "MATCHED_COMPLETE",
            }
        )
        assert labels.path_description == "Sin verificación de ejecución activa"
    live = inspector_labels(
        {
            "status": "ACTIVE",
            "pathProofState": "verified",
            "fidelityClaim": "MATCHED_COMPLETE",
            "lastProvenBoundary": "ALSA",
            "operationOrderVerified": True,
        }
    )
    assert "frontera" in live.path_description
    assert "revisar frontera" in live.fidelity_description
    assert live.operations_description.endswith("no acreditado")
    assert len(live.to_qml()) == 6


def test_ui_requires_owner_provenance_for_order():
    labels = inspector_labels(
        {
            "status": "ACTIVE",
            "operationOrderVerified": True,
            "operationOrderProof": "OWNER_ATTESTED",
        }
    )
    assert labels.operations_description == "Orden causal confirmado por recibo"
    assert inspector_labels(
        {
            "status": "HISTORICAL",
            "operationOrderVerified": True,
            "operationOrderProof": "OWNER_ATTESTED",
        }
    ).operations_description.endswith("no acreditado")


def test_capabilities_unknown_and_selected_not_effective():
    result = project_capabilities(None, execution_id="exec-A")
    assert len(result) == 7 and all(c.state == "UNOBSERVED" for c in result)
    r = project_capabilities(
        {
            "fir_convolution": {
                "supported": True,
                "wired": True,
                "owner": "F05",
                "state": "DRAFT",
                "effective_execution_id": "exec-A",
                "readback_proven": True,
            }
        },
        execution_id="exec-A",
    )
    fir = next(c for c in r if c.capability == "fir_convolution")
    assert fir.state == "AVAILABLE" and not fir.applied


@pytest.mark.parametrize(
    "fields,expected",
    [
        ({"supported": False, "wired": True, "owner": "F05"}, "UNAVAILABLE"),
        ({"supported": True, "wired": False, "owner": "F05"}, "DISABLED"),
        ({"supported": True, "wired": True, "owner": "UI"}, "DISABLED"),
    ],
)
def test_capabilities_not_wired_is_disabled(fields, expected):
    got = project_capabilities({"advanced_peq": fields})
    assert next(c for c in got if c.capability == "advanced_peq").state == expected


def test_capabilities_effective_requires_matching_execution():
    fields = {
        "supported": True,
        "wired": True,
        "owner": "F05",
        "state": "EFFECTIVE",
        "readback_proven": True,
        "effective_execution_id": "exec-A",
    }
    r = project_capabilities(
        {"parametric_eq": fields},
        execution_id="exec-A",
        owner_execution_correlated=True,
    )
    a = next(x for x in r if x.capability == "parametric_eq")
    assert a.applied and a.action == "OPEN_PROCESSING"
    unlinked = project_capabilities({"parametric_eq": fields}, execution_id="exec-A")
    assert not next(x for x in unlinked if x.capability == "parametric_eq").applied
    r = project_capabilities({"parametric_eq": fields}, execution_id="exec-B")
    assert not next(x for x in r if x.capability == "parametric_eq").applied


def test_coalescer_retains_critical_events_and_latest_ui():
    led = UiNoticeCoalescer(capacity=8)
    led.begin("exec-A", 1)
    assert led.submit(UiNotice("exec-A", 1, 1, "METRIC_UPDATE"))
    assert led.submit(UiNotice("exec-A", 1, 2, "RETIRE"))
    assert led.submit(UiNotice("exec-A", 1, 3, "FRAME_UPDATE"))
    assert led.submit(UiNotice("exec-A", 1, 4, "METRIC_UPDATE"))
    assert [x.kind for x in led.drain()] == ["RETIRE", "METRIC_UPDATE"]


def test_coalescer_overflow_forces_full_resnapshot():
    led = UiNoticeCoalescer(capacity=8)
    led.begin("exec-A", 1)
    for n in range(1, 9):
        assert led.submit(UiNotice("exec-A", 1, n, "HOST_LOSS"))
    assert not led.submit(UiNotice("exec-A", 1, 9, "RELEASE"))
    assert led.resync_required
    with pytest.raises(RuntimeError, match="FULL_RESNAPSHOT"):
        led.drain()
    led.begin("exec-B", 2)
    assert not led.resync_required and led.drain() == ()


def test_coalescer_cross_epoch_and_stale_denied():
    led = UiNoticeCoalescer()
    led.begin("exec-A", 1)
    assert not led.submit(UiNotice("exec-B", 1, 1, "METRIC_UPDATE"))
    assert not led.submit(UiNotice("exec-A", 2, 1, "METRIC_UPDATE"))
    assert led.submit(UiNotice("exec-A", 1, 1, "FRAME_UPDATE"))
    assert not led.submit(UiNotice("exec-A", 1, 1, "RETIRE"))


@pytest.mark.parametrize(
    "bad",
    [
        {"epoch": 0},
        {"epoch": True},
        {"sequence": 0},
        {"kind": "DAC_OK"},
        {"execution_id": ""},
    ],
)
def test_coalescer_rejects_malformed(bad):
    good = {"execution_id": "exec-A", "epoch": 1, "sequence": 1, "kind": "FRAME_UPDATE"}
    good.update(bad)
    with pytest.raises(ValueError):
        UiNotice(**good)


def test_ui_verified_without_observation_boundary_fails_closed():
    labels = inspector_labels({"status": "ACTIVE", "pathProofState": "verified"})
    assert labels.path_description == "Verificación de ruta sin frontera certificada"


def test_diagnostic_cannot_promote_matched_or_partial_from_ui():
    for claim in ("MATCHED_COMPLETE", "MATCHED_PARTIAL", "PARTIAL"):
        report = build_diagnostic_report(frame={"fidelityClaim": claim}, consent=True)
        assert report["fidelity_claim"] == "UNPROVEN"


def test_capabilities_meter_wrong_owner_cannot_activate():
    wrong = {
        "supported": True,
        "wired": True,
        "owner": "F05",
        "state": "EFFECTIVE",
        "readback_proven": True,
        "effective_execution_id": "exec-A",
    }
    result = project_capabilities({"true_peak_meter": wrong}, execution_id="exec-A")
    x = next(v for v in result if v.capability == "true_peak_meter")
    assert x.state == "DISABLED" and not x.applied


def test_capabilities_profile_library_is_not_dsp_effective():
    fields = {
        "supported": True,
        "wired": True,
        "owner": "SETTINGS",
        "state": "EFFECTIVE",
        "readback_proven": True,
        "effective_execution_id": "exec-A",
    }
    row = next(
        v
        for v in project_capabilities(
            {"profile_library": fields}, execution_id="exec-A"
        )
        if v.capability == "profile_library"
    )
    assert row.state == "AVAILABLE" and not row.applied


def test_high_frequency_ui_observations_coalesce_to_one_noncritical():
    led = UiNoticeCoalescer(capacity=8)
    led.begin("exec-A", 1)
    for sequence in range(1, 1001):
        assert led.submit(UiNotice("exec-A", 1, sequence, "METRIC_UPDATE"))
    assert len(led.drain()) == 1
    assert not led.resync_required


def test_high_frequency_metric_samples_remain_bounded():
    led = MetricLedger(max_samples=16)
    led.begin_execution("exec-A", 1)
    for sequence in range(1, 1001):
        assert led.ingest(obs(sequence=sequence))
    metric = led.snapshot()["processing_speed"]
    assert metric.count == 16 and metric.value == 1.2
    assert metric.state == "OBSERVED"  # newest bounded window only


def test_large_foreign_diagnostic_fields_are_not_exported():
    source = {f"private_{i}": f"/home/owner/{i}/secret_music.flac" for i in range(1000)}
    source.update({"status": "ACTIVE", "reasonCodes": ["ST_DSP_PRESENT"]})
    output = build_diagnostic_report(frame=source, consent=True)
    text = json.dumps(output)
    assert len(text) < 1000
    assert "secret_music" not in text


def test_remote_replay_stress_never_changes_boundary_to_dac():
    w = RemoteReceiptWindow()
    first = w.consider(remote(), now_ms=1000, owner_authenticated=True)
    assert first.boundary == "REMOTE_REPORTED"
    for _i in range(1000):
        out = w.consider(remote(), now_ms=1000, owner_authenticated=True)
        assert out.status == "UNOBSERVED"
    assert (
        w.consider(remote(sequence=5), now_ms=1000, owner_authenticated=True).boundary
        == "REMOTE_REPORTED"
    )
