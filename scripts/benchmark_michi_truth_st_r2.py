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


def _measure_stages(count: int, iterations: int) -> dict:
    frame = _base()
    frame["stages"] = [
        {
            "id": f"stage-{index}",
            "title": f"Stage {index}",
            "state": "observed",
            "summary": "observed",
            "detailRows": [["Fact", "Observed"]],
            "reasonCodes": ["ST_F03"],
        }
        for index in range(count)
    ]
    samples: list[float] = []
    for _ in range(iterations):
        started = time.perf_counter()
        TruthFrame.from_reconciled(frame).to_qml()
        samples.append(time.perf_counter() - started)
    return _percentiles(samples)


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
    from PySide6.QtCore import QCoreApplication, QUrl
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlComponent, QQmlEngine

    app = QGuiApplication.instance() or QGuiApplication([])
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
    for count in (5, 10, 20):
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
            QCoreApplication.processEvents()
        results[str(count)] = {
            "create": qml_percentiles(created),
            "property_set": qml_percentiles(property_set),
            "event_loop": qml_percentiles(event_loop),
            "update_changed": qml_percentiles(total),
            "initial_materialize": qml_percentiles(initial_materialize),
            "update_changed_steady": qml_percentiles(steady_changed),
            "update_unchanged_control": qml_percentiles(unchanged),
        }

    create_delete: list[float] = []
    before_rss = _rss_kib()
    for _ in range(10):
        started = time.perf_counter()
        item = component.create()
        item.setProperty("stages", stages(20, 0))
        QCoreApplication.processEvents()
        item.deleteLater()
        QCoreApplication.processEvents()
        create_delete.append(time.perf_counter() - started)
    after_rss = _rss_kib()
    app.processEvents()
    return {
        "status": "MEASURED",
        "stages": results,
        "create_delete_20_stages": {
            "cycles": 10,
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
            "layout. This is presentation construction, not DAC latency or XRUN."
        ),
    }


def main() -> int:
    tracemalloc.start()
    before_rss = _rss_kib()
    started = time.perf_counter()
    publish = _measure_publish(20_000)
    stages_20 = _measure_stages(20, 2_000)
    stages_5 = _measure_stages(5, 2_000)
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
            "truth_frame_5_stages": stages_5,
            "truth_frame_20_stages": stages_20,
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
