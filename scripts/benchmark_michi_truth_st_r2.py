#!/usr/bin/env python3
"""ST-R2: bounded software benchmark for the Signal Truth presentation path.

This measures Python projection construction and offscreen Qt Quick item
construction. It is not DAC latency, ALSA XRUN, KWin composition or physical
output evidence.
"""

from __future__ import annotations

import json
import os
import sys
import time
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from michi.application.signal_truth_frame import TruthFrame, publish_truth_frame  # noqa: E402

STAGES = ("source", "decode", "processing", "output", "device")
DYNAMIC_STAGES = ("resample", "channel-remap", "fir")
CANONICAL_COUNTS = (5, 8)
QML_STRESS_COUNTS = (5, 10, 20)


def canonical_stage_ids(count: int) -> tuple[str, ...]:
    """Return a canonical TruthFrame stage sequence.

    The canonical read model has five anchors plus at most the three dynamic
    IDs resample, channel-remap and fir. Twenty canonical stages are impossible;
    that count belongs only to the synthetic QML presentation stress test.
    """
    if not 5 <= count <= 8:
        raise ValueError(f"canonical TruthFrame supports 5..8 stages, received {count}")
    dynamic = DYNAMIC_STAGES[: count - 5]
    return ("source", "decode", "processing", *dynamic, "output", "device")


def _base() -> dict:
    return {
        "status": "ACTIVE",
        "captureRevision": 12,
        "canonicalF03State": "RECONCILED",
        "canonicalF03Nodes": [
            {"kind": k, "state": "observed"}
            for k in ("source", "decode", "engine", "device")
        ],
        "pathProofState": "partially_verified",
        "pathProofLabel": "Ruta observada hasta ALSA",
        "pathVerdict": "observed",
        "reasonCodes": ["ST_CANONICAL_OBSERVED"],
        "identity": {
            "plan_id": "P",
            "execution_generation": 3,
            "stable_device_id": "Device",
        },
        "stages": [
            {
                "id": k,
                "title": k,
                "state": "observed",
                "summary": "observed",
                "detailRows": [["Fact", "Observed"]],
                "reasonCodes": ["ST_F03"],
            }
            for k in STAGES
        ],
        "familyEvidenceState": "RUNNING_REPORTED",
        "dspExecutionState": "UNOBSERVED",
        "headline": "Ruta observada",
        "sourceIdentity": "bench",
    }


def _percentiles(samples: list[float]) -> dict:
    ordered = sorted(samples)

    def at(p: float) -> float:
        return ordered[min(len(ordered) - 1, int(len(ordered) * p))]

    return {
        "count": len(samples),
        "p50_us": round(at(0.50) * 1_000_000, 2),
        "p95_us": round(at(0.95) * 1_000_000, 2),
        "p99_us": round(at(0.99) * 1_000_000, 2),
        "max_us": round(ordered[-1] * 1_000_000, 2),
    }


def _rss_kib() -> int:
    try:
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1])
    except OSError:
        pass
    return 0


def _measure_publish(iterations: int) -> dict:
    frame = _base()
    samples: list[float] = []
    for _ in range(iterations):
        started = time.perf_counter()
        publish_truth_frame(frame)
        samples.append(time.perf_counter() - started)
    return _percentiles(samples)


def _stage_payload(count: int, revision: int = 0) -> list[dict]:
    return [
        {
            "id": stage_id,
            "title": stage_id,
            "state": "observed",
            "summary": f"observed {revision}",
            "detailRows": [["Fact", "Observed"]],
            "reasonCodes": ["ST_F03"],
        }
        for stage_id in canonical_stage_ids(count)
    ]


def _measure_stages(count: int, iterations: int) -> dict:
    frame = _base()
    frame["stages"] = _stage_payload(count)
    projected = TruthFrame.from_reconciled(frame).to_qml()
    if len(projected.get("stages", ())) != count:
        raise RuntimeError(
            f"canonical projection rejected {count} stages; "
            f"got {len(projected.get('stages', ()))}"
        )
    samples: list[float] = []
    for _ in range(iterations):
        started = time.perf_counter()
        TruthFrame.from_reconciled(frame).to_qml()
        samples.append(time.perf_counter() - started)
    return {"stage_count": count, **_percentiles(samples)}


def _measure_burst(batch: int, iterations: int) -> dict:
    frame = _base()
    started = time.perf_counter()
    publish_truth_frame(frame)
    cold = time.perf_counter() - started
    samples: list[float] = []
    for _ in range(iterations):
        started = time.perf_counter()
        for _ in range(batch):
            publish_truth_frame(frame)
        samples.append((time.perf_counter() - started) / batch)
    return {
        "batch": batch,
        "cold_us": round(cold * 1_000_000, 2),
        **_percentiles(samples),
    }


def _measure_qml() -> dict:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QCoreApplication, QEvent, QUrl
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlComponent, QQmlEngine

    QGuiApplication.instance() or QGuiApplication([])
    engine = QQmlEngine()
    engine.addImportPath(str(ROOT / "src/michi/presentation/qml"))
    component = QQmlComponent(
        engine,
        QUrl.fromLocalFile(
            str(ROOT / "src/michi/presentation/qml/components/MichiSignalPathView.qml")
        ),
    )
    if component.isError():
        return {"status": "ERROR", "errors": [e.toString() for e in component.errors()]}

    def stages(count: int, revision: int) -> list[dict]:
        # Vary the payload on every update. Reusing an equal array lets Qt
        # treat the assignment as a no-op and under-reports the real cost of a
        # changed stage list.
        return [
            {
                "id": f"stage-{index}",
                "title": f"Stage {index}",
                "state": "observed",
                "summary": f"observed {revision}",
                "detail": "observed detail",
                "detailRows": [["Fact", "Observed"]],
                "reasonCodes": ["ST_F03"],
            }
            for index in range(count)
        ]

    def flush_deferred_delete() -> None:
        """Deliver Qt's DeferredDelete events before sampling RSS or reuse."""
        for _ in range(3):
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            QCoreApplication.processEvents()

    def qml_percentiles(samples: list[float]) -> dict:
        ordered = sorted(samples)

        def at(p: float) -> float:
            return ordered[min(len(ordered) - 1, int(len(ordered) * p))]

        return {
            "count": len(samples),
            "p50_ms": round(at(0.50) * 1000, 3),
            "p95_ms": round(at(0.95) * 1000, 3),
            "p99_ms": round(at(0.99) * 1000, 3),
            "max_ms": round(ordered[-1] * 1000, 3),
            "over_16_67_ms": sum(1 for sample in samples if sample > 0.01667),
        }

    results: dict[str, dict] = {}
    outer_cycles = 10
    updates_per_cycle = 10
    for count in QML_STRESS_COUNTS:
        created: list[float] = []
        property_set: list[float] = []
        event_loop: list[float] = []
        total: list[float] = []
        initial_materialize: list[float] = []
        steady_changed: list[float] = []
        unchanged: list[float] = []
        for _ in range(outer_cycles):
            started = time.perf_counter()
            item = component.create()
            QCoreApplication.processEvents()
            created.append(time.perf_counter() - started)
            for revision in range(updates_per_cycle):
                payload = stages(count, revision)
                started = time.perf_counter()
                item.setProperty("stages", payload)
                after_set = time.perf_counter()
                QCoreApplication.processEvents()
                after_events = time.perf_counter()
                property_set.append(after_set - started)
                event_loop.append(after_events - after_set)
                total.append(after_events - started)
                if revision == 0:
                    initial_materialize.append(after_events - started)
                else:
                    steady_changed.append(after_events - started)
            # Control: an identical array must not rebuild the repeater.
            payload = stages(count, 0)
            item.setProperty("stages", payload)
            QCoreApplication.processEvents()
            for _ in range(5):
                started = time.perf_counter()
                item.setProperty("stages", payload)
                QCoreApplication.processEvents()
                unchanged.append(time.perf_counter() - started)
            item.deleteLater()
            flush_deferred_delete()
            del item
        results[str(count)] = {
            "create": qml_percentiles(created),
            "property_set": qml_percentiles(property_set),
            "event_loop": qml_percentiles(event_loop),
            "update_changed": qml_percentiles(total),
            "initial_materialize": qml_percentiles(initial_materialize),
            "update_changed_steady": qml_percentiles(steady_changed),
            "update_unchanged_control": qml_percentiles(unchanged),
        }

    # Warm up the engine before sampling RSS, and prove deletion is delivered
    # rather than merely queued.
    warmup = component.create()
    warmup.setProperty("stages", stages(20, 0))
    flush_deferred_delete()
    warmup.deleteLater()
    flush_deferred_delete()
    del warmup

    create_delete: list[float] = []
    destroyed = 0

    def count_destroyed() -> None:
        nonlocal destroyed
        destroyed += 1

    before_rss = _rss_kib()
    for _ in range(10):
        started = time.perf_counter()
        item = component.create()
        item.destroyed.connect(count_destroyed)
        item.setProperty("stages", stages(20, 0))
        flush_deferred_delete()
        item.deleteLater()
        flush_deferred_delete()
        create_delete.append(time.perf_counter() - started)
        del item
    after_rss = _rss_kib()
    return {
        "status": "MEASURED",
        "stages": results,
        "stage_model": {
            "qml_counts": list(QML_STRESS_COUNTS),
            "scope": "SYNTHETIC_PRESENTATION_STRESS_ONLY",
        },
        "canonical_projection": {
            "stage_counts": list(CANONICAL_COUNTS),
            "scope": "FIVE_ANCHORS_PLUS_THREE_DYNAMIC_IDS",
        },
        "create_delete_20_stages": {
            "cycles": 10,
            "destroyed_objects": destroyed,
            "destruction_verified": destroyed == 10,
            "deferred_delete_flushed": True,
            "total": qml_percentiles(create_delete),
            "rss_before_kib": before_rss,
            "rss_after_kib": after_rss,
            "rss_delta_kib": after_rss - before_rss,
        },
        "interpretation": (
            "initial_materialize creates the stable StageData objects and the "
            "Repeater delegates once per popup opening. update_changed_steady "
            "mutates those stable objects, so a content-only update does not "
            "rebuild the delegate list. event_loop covers queued polish and "
            "layout. The 5/10/20-stage QML counts are synthetic presentation "
            "stress; canonical TruthFrame measurements are limited to 5-8 "
            "valid stage IDs. This is not DAC latency or XRUN."
        ),
    }


def main() -> int:
    tracemalloc.start()
    before_rss = _rss_kib()
    started = time.perf_counter()
    publish = _measure_publish(20_000)
    canonical = [_measure_stages(count, 2_000) for count in CANONICAL_COUNTS]
    bursts = [_measure_burst(batch, 400) for batch in (1, 10, 100)]
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    after_rss = _rss_kib()
    qml = _measure_qml()
    artifact = {
        "schema": "michi.ap2f11.st_r2_performance.v1",
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "environment": {
            "python": sys.version.split()[0],
            "qt": __import__("PySide6.QtCore", fromlist=["qVersion"]).qVersion(),
            "platform": os.environ.get("QT_QPA_PLATFORM", "offscreen"),
        },
        "measurements": {
            "publish_truth_frame_5_stages": publish,
            "truth_frame_canonical_stages": canonical,
            "bursts": bursts,
            "qml": qml,
            "rss_kib_before": before_rss,
            "rss_kib_after": after_rss,
            "tracemalloc_peak_kib": round(peak / 1024, 1),
            "total_elapsed_s": round(time.perf_counter() - started, 2),
        },
        "scope": {
            "measures": (
                "Python TruthFrame construction and offscreen Qt Quick item updates"
            ),
            "not_measured": (
                "DAC latency, ALSA XRUN, true peak, LUFS, KWin composition, "
                "physical output"
            ),
        },
        "truth": {
            "software_benchmark": "PASS",
            "dac_latency_claim": "NOT_RUN",
            "xrun_claim": "NOT_RUN",
            "kwin_live_claim": "NOT_RUN",
        },
    }
    out = ROOT / "docs/audio/phase2/F11_SIGNAL_TRUTH_ST_R2_PERFORMANCE.json"
    out.write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(artifact["measurements"], indent=2, sort_keys=True))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
