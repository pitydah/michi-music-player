"""AP2-F11 A48: bounded, non-RT evidence-aware Signal Truth metric projection.

All measurements originate from external owners; this module neither measures
PCM nor infers XRUN/clipping/true-peak from nominal formats. Producers MUST
call ingest on a non-audio worker. Results are read models, not evidence of DAC.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from math import ceil, isfinite
from typing import Literal

_ALLOWED = {
    "sample_peak_dbfs": ("dBFS", "pcm_meter", "gauge"),
    "true_peak_dbtp": ("dBTP", "true_peak_meter", "gauge"),
    "integrated_lufs": ("LUFS", "loudness_meter", "gauge"),
    "clipped_samples": ("samples", "pcm_meter", "counter"),
    "xrun_events": ("events", "alsa_observer", "counter"),
    "processing_speed": ("x", "processing_host", "gauge"),
    "owner_to_ui_ms": ("ms", "ui_observer", "latency"),
    "frame_dispatch_ms": ("ms", "ui_observer", "latency"),
}


@dataclass(frozen=True, slots=True)
class MetricObservation:
    execution_id: str
    epoch: int
    metric: str
    value: float
    producer: str
    sequence: int
    clock_domain: str = ""
    missing_before: int = 0

    def __post_init__(self) -> None:
        if (
            not isinstance(self.execution_id, str)
            or not self.execution_id.strip()
            or len(self.execution_id) > 128
        ):
            raise ValueError("execution scope required")
        if (
            type(self.epoch) is not int
            or self.epoch <= 0
            or type(self.sequence) is not int
            or self.sequence <= 0
        ):
            raise ValueError("positive epoch and sequence required")
        if self.metric not in _ALLOWED or self.producer != _ALLOWED[self.metric][1]:
            raise ValueError("metric and authorized producer mismatch")
        if type(self.value) not in (int, float) or not isfinite(self.value):
            raise ValueError("finite measurement required")
        if (
            type(self.missing_before) is not int
            or not 0 <= self.missing_before <= 1_000_000
        ):
            raise ValueError("invalid missing sample count")
        kind = _ALLOWED[self.metric][2]
        if kind == "counter" and (self.value < 0 or int(self.value) != self.value):
            raise ValueError("counter must be a nonnegative integer")
        if kind == "latency" and (
            self.value < 0 or self.clock_domain != "MONOTONIC_SAME_DOMAIN"
        ):
            raise ValueError("cannot mix clock domains for latency")
        if self.metric == "processing_speed" and self.value < 0:
            raise ValueError("processing speed cannot be negative")
        if self.metric == "integrated_lufs" and self.value > 10:
            raise ValueError("implausible loudness reading")


@dataclass(frozen=True, slots=True)
class MetricResult:
    name: str
    state: Literal["OBSERVED", "PARTIAL", "UNOBSERVED"]
    value: float | None
    unit: str
    producer: str
    count: int
    missing: int
    p95: float | None = None
    p99: float | None = None

    def to_json(self) -> dict[str, object]:
        return {
            "name": self.name,
            "state": self.state,
            "value": self.value,
            "unit": self.unit,
            "producer": self.producer,
            "count": self.count,
            "missing": self.missing,
            "p95": self.p95,
            "p99": self.p99,
        }


class MetricLedger:
    """Bounded, worker-only projector; never called from audio callback.

    Sequence gaps prevent a `COMPLETE` interpretation. For a cumulative counter
    never sum snapshots; newest value is the absolute owner count for its epoch.
    """

    def __init__(self, *, max_samples: int = 256) -> None:
        if type(max_samples) is not int or not 16 <= max_samples <= 2048:
            raise ValueError("max_samples outside approved range")
        self._max = max_samples
        self._scope: tuple[str, int] | None = None
        self._values: dict[str, deque[MetricObservation]] = {}
        self._last_sequences: dict[str, int] = {}
        self._missing: dict[str, int] = {}

    def begin_execution(self, execution_id: str, epoch: int) -> None:
        if (
            not isinstance(execution_id, str)
            or not execution_id.strip()
            or len(execution_id) > 128
        ):
            raise ValueError("bad execution identity")
        if type(epoch) is not int or epoch <= 0:
            raise ValueError("bad execution epoch")
        self._scope = (execution_id, epoch)
        self._values.clear()
        self._last_sequences.clear()
        self._missing.clear()

    def retire(self) -> None:
        self._scope = None
        self._values.clear()
        self._last_sequences.clear()
        self._missing.clear()

    def ingest(self, event: MetricObservation) -> bool:
        """Return False for stale or duplicate events; never adopt cross-route data."""
        if self._scope != (event.execution_id, event.epoch):
            return False
        last = self._last_sequences.get(event.metric)
        if last is not None and event.sequence <= last:
            return False
        self._missing[event.metric] = (
            self._missing.get(event.metric, 0) + event.missing_before
        )
        if last is None and event.sequence > 1:
            self._missing[event.metric] += event.sequence - 1
        if last is not None and event.sequence > last + 1:
            self._missing[event.metric] += event.sequence - last - 1
        self._last_sequences[event.metric] = event.sequence
        self._values.setdefault(event.metric, deque(maxlen=self._max)).append(event)
        return True

    @staticmethod
    def _quantile(values: list[float], percentile: float) -> float:
        ordered = sorted(values)
        return ordered[max(0, ceil(percentile * len(ordered)) - 1)]

    def snapshot(self) -> dict[str, MetricResult]:
        """Separate sample peak, true peak and integrated loudness explicitly."""
        out: dict[str, MetricResult] = {}
        for name, (unit, owner, kind) in _ALLOWED.items():
            events = self._values.get(name, ())
            missing = self._missing.get(name, 0)
            if not events:
                out[name] = MetricResult(
                    name, "UNOBSERVED", None, unit, owner, 0, missing
                )
                continue
            nums = [float(event.value) for event in events]
            value = nums[-1]  # owner count or latest observation, not a signal claim
            out[name] = MetricResult(
                name,
                "PARTIAL" if missing else "OBSERVED",
                value,
                unit,
                owner,
                len(nums),
                missing,
                self._quantile(nums, 0.95) if kind == "latency" else None,
                self._quantile(nums, 0.99) if kind == "latency" else None,
            )
        return out
