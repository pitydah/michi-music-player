"""A49: measured Qt owner projection CPU cost, no audio callback operations.

Boundary: time spent building Signal Truth's Qt read model. The number is NOT
actual QML frame time, audio render callback time, DSP speed, XRUN, or DAC proof.
No timer, audio tap, network access or publisher is installed by this module.
"""

from __future__ import annotations

import hashlib
from collections import deque
from collections.abc import Mapping
from math import ceil


class OwnerProjectionMeter:
    """Local, bounded, F03-scoped owner-thread performance read model."""

    def __init__(self, *, samples: int = 256) -> None:
        if type(samples) is not int or not 16 <= samples <= 2048:
            raise ValueError("bounded sample capacity required")
        self._max = samples
        self._scope: tuple[str, int] | None = None
        self._values: deque[float] = deque(maxlen=samples)

    @staticmethod
    def _scope_of(frame: Mapping[str, object]) -> tuple[str, int] | None:
        if frame.get("status") != "ACTIVE":
            return None
        identity = frame.get("identity")
        if not isinstance(identity, Mapping):
            return None
        plan_id = identity.get("plan_id")
        execution_generation = identity.get("execution_generation")
        port_generation = identity.get("port_generation")
        binding_generation = identity.get("binding_generation")
        if (
            not isinstance(plan_id, str)
            or not plan_id
            or type(execution_generation) is not int
            or execution_generation <= 0
            or type(port_generation) is not int
            or port_generation <= 0
            or type(binding_generation) is not int
            or binding_generation <= 0
        ):
            return None
        # Presentation-only F03 scope, NEVER an OutputSession DSP adoption ID.
        scope = (
            f"{plan_id}\0{execution_generation}\0"
            f"{port_generation}\0{binding_generation}"
        )
        return (
            "ui-f03-" + hashlib.sha256(scope.encode("utf-8")).hexdigest()[:32],
            execution_generation,
        )

    def observe(self, *, frame: Mapping[str, object], elapsed_ns: int) -> bool:
        """Record duration measured by perf_counter_ns on the Qt owner only."""
        if type(elapsed_ns) is not int or elapsed_ns < 0:
            raise ValueError("nonnegative measured duration required")
        scope = self._scope_of(frame)
        if scope is None:
            self.retire()
            return False
        if self._scope != scope:
            self._scope = scope
            self._values.clear()
        self._values.append(elapsed_ns / 1_000_000.0)
        return True

    @staticmethod
    def _quantile(values: deque[float], p: float) -> float:
        ordered = sorted(values)
        return ordered[max(0, ceil(p * len(ordered)) - 1)]

    def items(self, *, temporal_status: str) -> list[dict[str, object]]:
        if temporal_status != "ACTIVE" or self._scope is None or not self._values:
            return []
        return [
            {
                "name": "projection_build_ms",
                "state": "OBSERVED",
                "value": self._values[-1],
                "unit": "ms",
                "producer": "ui_observer",
                "count": len(self._values),
                "missing": 0,
                "p95": self._quantile(self._values, 0.95),
                "p99": self._quantile(self._values, 0.99),
            }
        ]

    def retire(self) -> None:
        self._scope = None
        self._values.clear()
