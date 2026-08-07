"""Job handler ports — explicit dependencies for durable job handlers.

Every handler registered on the DurableJobService receives the ports it
needs as constructor-injected instances (composition closes over composed
services). Handlers NEVER resolve services themselves: no ``ServiceClass(...)``,
no ``container.get(...)``, no fallback instantiation (ADR-004, Fase Jobs).

Ports are Protocols: any object exposing the required surface qualifies
(the real service, a composed adapter, or a test double).
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LibraryScanPort(Protocol):
    """Port for library_scan / library_scan_all handlers."""

    def scan(self, ctx: Any, folder_path: str) -> dict[str, Any]:
        """Scan *folder_path*, reporting progress and cancellation via ctx."""
        ...

    def list_sources(self) -> list[dict[str, Any]]:
        """Return enabled + available library sources to scan."""
        ...


@runtime_checkable
class MetadataBatchPort(Protocol):
    """Port for metadata_scan / metadata_batch handlers."""

    def scan_missing(self, ctx: Any | None = None) -> dict[str, Any]:
        """Detect tracks with missing metadata."""
        ...

    def build_proposal(
        self, track_refs: list[dict[str, Any]], fields: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Build an editable metadata proposal for *track_refs*."""
        ...

    def apply_batch(
        self, requests: list[dict[str, Any]], ctx: Any | None = None
    ) -> dict[str, Any]:
        """Apply a batch of confirmed metadata edits."""
        ...


@runtime_checkable
class HistoryExportPort(Protocol):
    """Port for the history_export handler."""

    def export_history(
        self,
        output_path: str,
        fmt: str = "json",
        filters: dict[str, Any] | None = None,
        ctx: Any | None = None,
    ) -> dict[str, Any]:
        """Export play history to *output_path* in the requested format."""
        ...


@runtime_checkable
class DoctorRepairPort(Protocol):
    """Port for doctor_scan / doctor_repair handlers."""

    def scan(self, ctx: Any | None = None) -> dict[str, Any]:
        """Run a library health scan."""
        ...

    def repair(
        self,
        issue: dict[str, Any],
        confirmation_token: str = "",
        ctx: Any | None = None,
    ) -> dict[str, Any]:
        """Execute a repair for one issue (approved token required)."""
        ...


@runtime_checkable
class DeviceSyncPort(Protocol):
    """Port for device sync jobs (Fase Sync).

    Implemented by the composed DeviceSyncService facade (see
    ``core.composition.jobs``); the handler receives the port instance
    instead of resolving device_sync_service itself.
    """

    def sync_device(
        self,
        device_id: str,
        track_ids: list[str],
        playlist_name: str = "",
        ctx: Any | None = None,
    ) -> dict[str, Any]:
        """Run the full pipeline: plan → transfer → verify → playlist → history."""
        ...

    def transfer_file(
        self,
        source_path: str,
        dest_path: str,
        ctx: Any | None = None,
    ) -> dict[str, Any]:
        """Transfer a single file (copy + verification)."""
        ...


@runtime_checkable
class AudioLabPort(Protocol):
    """Port for Audio Lab jobs (reserved — Fase Audio Lab).

    No handler is registered in this phase; Audio Lab currently submits
    durable jobs through AudioLabJobAdapter. The port documents the surface
    a future handler will receive.
    """

    def probe(self, filepath: str, ctx: Any | None = None) -> dict[str, Any]:
        """Probe an audio file."""
        ...

    def analyze(self, filepath: str, ctx: Any | None = None) -> dict[str, Any]:
        """Run a technical analysis on an audio file."""
        ...


@runtime_checkable
class MixGenerationPort(Protocol):
    """Port for the mix_generate handler.

    ``generate`` returns the canonical MixService outcome dict
    ({ok, status, tracks, ...}); the handler surfaces it as the job result
    verbatim so the bridge can adapt it to the QML shape (Fase Mix).
    """

    def generate(
        self,
        strategy: str,
        seed: dict[str, Any] | None = None,
        limit: int = 30,
        ctx: Any | None = None,
    ) -> dict[str, Any]:
        """Generate a mix with an explicit MixGenerationStatus outcome."""
        ...
