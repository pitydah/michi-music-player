"""PARENT-SAFE transport for AudioProcessingService (AP2-F05 Package A).

Resolves the CURRENT hosted GStreamer port (the same supervised host that
plays audio) and forwards the processing transaction. It never owns Gst
objects; if GStreamer is not the active/available engine, every operation
fails closed with a typed infrastructure error so the application authority
can keep requested intent while reporting effective runtime unavailable.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class ProcessingTransportError(RuntimeError):
    """Typed transport failure consumed by the application boundary."""

    def __init__(
        self, code: str, detail: str, payload: dict[str, Any] | None = None
    ) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.payload = dict(payload or {})


class HostedProcessingTransport:
    """Adapter over the hosted port provider (one host, one port)."""

    def __init__(self, port_provider: Callable[[], object | None]) -> None:
        self._port_provider = port_provider

    def _port(self):
        port = self._port_provider()
        if port is None:
            raise ProcessingTransportError(
                "DSP_TRANSPORT_UNAVAILABLE",
                "GStreamer is not the open active engine for processing",
            )
        return port

    # ── capability ────────────────────────────────────────────────────
    def query_capabilities(self) -> dict[str, Any]:
        return self._port().query_processing_capabilities()

    # ── transaction ───────────────────────────────────────────────────
    def prepare_candidate(
        self, plan: dict[str, Any], *, processing_generation: int = 0
    ) -> dict[str, Any]:
        return self._port().prepare_candidate(
            plan, processing_generation=processing_generation
        )

    def commit_candidate(
        self,
        *,
        plan_id: str,
        processing_generation: int,
        pipeline_generation: int,
        candidate_id: str = "",
    ) -> dict[str, Any]:
        return self._port().commit_candidate(
            plan_id=plan_id,
            processing_generation=processing_generation,
            pipeline_generation=pipeline_generation,
            candidate_id=candidate_id,
        )

    def abort_candidate(self) -> bool:
        return self._port().abort_candidate()

    def bypass_processing(self) -> dict[str, Any]:
        return self._port().bypass_processing()

    def host_generation(self) -> int:
        port = self._port_provider()
        supervisor = getattr(port, "supervisor_generation", None)
        if supervisor is None:
            return 0
        try:
            return int(supervisor())
        except Exception:  # noqa: BLE001 - diagnostics-grade value
            return 0
