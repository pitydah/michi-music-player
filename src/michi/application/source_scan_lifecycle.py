"""Owner-thread source scan lifecycle (M6-EXT-R4 FINAL SEAL P1-01).

UNA autoridad de lifecycle para TODOS los scans de sources productivos:

    QML intent
        ↓
    request_scan_all / request_scan_source / request_relocate
        ↓
    WORKER  (pipeline M6.4 existente — nunca el GUI thread):
        discover, fingerprints, metadata extraction, reconciliation compute
        ↓  (relay → owner thread)
    OWNER:
        generation gate → authoritative commit → caches → publication

Serialización source-a-source: el siguiente source arranca SOLO cuando el
anterior completó. Stale/cancelled generations NUNCA commitean.

El lifecycle es Qt-free: ``handle_done`` / ``handle_progress`` son los
puntos que la composición productiva conecta al relay (bootstrap), igual
que hace con el scan dispatcher legacy. Los tests pueden llamarlos
directamente con un pipeline determinista.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, replace

from michi.application.ports import ScanCancelled
from michi.application.source_scan_coordinator import SourceScanCoordinator

logger = logging.getLogger(__name__)

_IDLE = "IDLE"
_RUNNING = "RUNNING"
_FAILED = "FAILED"


@dataclass(frozen=True)
class SourceScanRunState:
    """Observable scan lifecycle state (owner-thread truth).

    CORRECTIVE SEAL §6: terminal results stay observable. ``status`` may
    return to IDLE for queue processing, but ``last_terminal_status`` /
    ``last_diagnostic`` / ``last_source_id`` persist until the NEXT scan
    request — a filesystem failure is never erased before presentation can
    show it."""

    generation: int = 0
    status: str = _IDLE
    current_source_id: str = ""
    phase: str = ""
    processed: int = 0
    total: int = 0
    current_path: str = ""
    diagnostic: str = ""
    last_terminal_status: str = ""
    last_diagnostic: str = ""
    last_source_id: str = ""
    failed_source_ids: tuple[str, ...] = ()

    @property
    def active(self) -> bool:
        return self.status == _RUNNING


class SourceScanLifecycle:
    """Serialized async source scan authority."""

    def __init__(
        self,
        coordinator: SourceScanCoordinator,
        pipeline,
        on_state: Callable[[SourceScanRunState], None] | None = None,
    ) -> None:
        self._coordinator = coordinator
        self._pipeline = pipeline
        self._queue: list[str] = []
        self._generation = 0
        self._active = False
        self._cancel_requested = False
        self._state = SourceScanRunState()
        self._subscribers: list[Callable[[SourceScanRunState], None]] = []
        if on_state is not None:
            self._subscribers.append(on_state)

    # ------------------------------------------------------------- intent API

    @property
    def state(self) -> SourceScanRunState:
        return self._state

    def subscribe_state(self, callback: Callable[[SourceScanRunState], None]) -> None:
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe_state(self, callback: Callable[[SourceScanRunState], None]) -> None:
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def _reset_terminal(self) -> None:
        """A NEW user scan request starts a fresh run: clears the previous
        terminal record and the cancel flag."""
        self._cancel_requested = False
        self._set_state(
            last_terminal_status="",
            last_diagnostic="",
            last_source_id="",
            failed_source_ids=(),
        )

    def request_scan_all(self) -> None:
        """Scan ALL active + enabled sources, serialized (Scan library)."""
        self._reset_terminal()
        self._enqueue(
            [
                s.library_source_id
                for s in self._coordinator.list_sources()
                if s.lifecycle.value == "active" and s.enabled
            ]
        )

    def request_scan_source(self, source_id: str) -> None:
        """Reconcile ONE source asynchronously (never the GUI thread)."""
        self._reset_terminal()
        self._enqueue([source_id])

    def request_relocate(self, source_id: str, new_root: str) -> str:
        """Locate Source… (P1-C): remap the root ONLY (cheap upsert), then
        reschedule EXACTLY ONE reconciliation against the NEW root — the
        old-root active generation is cancelled by reschedule."""
        if not self._active:
            self._reset_terminal()
        try:
            relocated = self._coordinator.relocate_source_root(source_id, new_root)
        except ValueError as exc:
            return str(exc)
        self.reschedule_source(relocated.library_source_id)
        return ""

    def cancel(self) -> None:
        """CANCEL THE WHOLE USER-REQUESTED RUN (P1-02): clears the remaining
        source queue and cancels the active generation — no further source
        ever starts after the acknowledgment."""
        self._queue.clear()
        if self._active:
            self._cancel_requested = True
            self._pipeline.cancel(self._generation)

    def _remove_queued_source(self, source_id: str) -> None:
        self._queue = [c for c in self._queue if c != source_id]

    def invalidate_source(self, source_id: str) -> None:
        """Invalidate queued/current work for a Source whose configuration
        changed. Does NOT cancel unrelated Sources and does NOT set
        ``_cancel_requested`` (that flag means whole-run cancel)."""
        self._remove_queued_source(source_id)
        if self._active and self._state.current_source_id == source_id:
            self._pipeline.cancel(self._generation)

    def reschedule_source(self, source_id: str) -> None:
        """Run this Source again using its CURRENT configuration: if it is
        active, cancel the stale generation and queue exactly ONE
        replacement; otherwise queue it next (never duplicated)."""
        self._remove_queued_source(source_id)
        self._queue.insert(0, source_id)
        if self._active and self._state.current_source_id == source_id:
            self._pipeline.cancel(self._generation)
            return
        self._start_next()

    # --------------------------------------------------------- relay handlers

    def handle_progress(self, generation: int, progress) -> None:
        """OWNER thread: forward progress for the CURRENT generation only."""
        if generation != self._generation:
            return
        self._set_state(
            phase=getattr(progress, "phase", self._state.phase),
            processed=getattr(progress, "processed", self._state.processed),
            total=getattr(progress, "total", self._state.total),
            current_path=getattr(progress, "current_path", self._state.current_path),
        )

    def handle_done(self, generation: int, plan, error: BaseException | None) -> None:
        """OWNER thread: generation gate BEFORE any commit. A stale or
        failed generation never touches the catalog."""
        source = self._current_source()
        if generation != self._generation or source is None:
            self._finish(generation, stale=True)
            return
        if error is not None or plan is None:
            # Worker failure (typed scan error / cancellation): no commit.
            # P1-05: the OWNER publishes the physical observation (never
            # the worker); ScanCancelled fabricates no observation.
            if error is not None and not isinstance(error, ScanCancelled):
                self._coordinator.record_source_scan_error(
                    source.library_source_id, error
                )
            self._finish(
                generation,
                failed=not isinstance(error, ScanCancelled),
                diagnostic=str(error) if error is not None else "cancelled",
            )
            return
        outcome = self._coordinator.commit_source_scan_if_current(
            generation, self._generation, source, plan, None
        )
        if outcome is None:
            self._finish(generation, stale=True)
            return
        self._finish(generation, outcome=outcome)

    # -------------------------------------------------------------- internals

    def _current_source(self):
        source_id = self._state.current_source_id
        if not source_id:
            return None
        return next(
            (
                s
                for s in self._coordinator.list_sources()
                if s.library_source_id == source_id
            ),
            None,
        )

    def _enqueue(self, source_ids: list[str]) -> None:
        for source_id in source_ids:
            if (
                source_id not in self._queue
                and source_id != self._state.current_source_id
            ):
                self._queue.append(source_id)
        self._start_next()

    def _start_next(self) -> None:
        if self._active:
            return  # serialization: one source at a time
        if not self._queue:
            if self._state.status != _IDLE or self._state.last_terminal_status == "":
                # P1-03: finalize the RUN-level terminal truth once.
                if self._state.failed_source_ids:
                    terminal = _FAILED
                elif self._cancel_requested:
                    terminal = "CANCELLED"
                else:
                    terminal = "COMPLETED"
                self._set_state(
                    status=_IDLE,
                    current_source_id="",
                    phase="",
                    processed=0,
                    total=0,
                    current_path="",
                    diagnostic="",
                    last_terminal_status=terminal,
                )
            return
        source_id = self._queue.pop(0)
        source = next(
            (
                s
                for s in self._coordinator.list_sources()
                if s.library_source_id == source_id
            ),
            None,
        )
        if source is None:
            self._start_next()
            return
        self._active = True
        self._generation += 1
        generation = self._generation
        self._set_state(
            generation=generation,
            status=_RUNNING,
            current_source_id=source_id,
            phase="PROBING",
            processed=0,
            total=0,
            current_path="",
            diagnostic="",
        )
        self._coordinator.submit_source_scan(
            source,
            self._pipeline,
            generation,
            on_progress=self.handle_progress,
            on_done=self.handle_done,
        )

    def _finish(
        self,
        generation: int,
        *,
        stale: bool = False,
        failed: bool = False,
        diagnostic: str = "",
        outcome=None,
    ) -> None:
        if generation != self._generation:
            return  # superseded: its completion is irrelevant
        self._active = False
        source_id = self._state.current_source_id
        if outcome is not None:
            status = _FAILED if outcome.failed else _IDLE
            diagnostic = outcome.diagnostic or ""
        elif failed:
            status = _FAILED
        else:
            status = _IDLE
        # P1-03: RUN-level failure aggregation — a later successful source
        # NEVER converts an already failed run into success.
        failed_ids = self._state.failed_source_ids
        if status == _FAILED and source_id not in failed_ids:
            failed_ids = failed_ids + (source_id,)
        # T3: last_source_id belongs to the PRESERVED first diagnostic —
        # a later successful source must never overwrite either.
        run_diagnostic = self._state.last_diagnostic
        diagnostic_source_id = self._state.last_source_id
        if diagnostic and not run_diagnostic:
            run_diagnostic = diagnostic
            diagnostic_source_id = source_id
        self._set_state(
            status=status,
            phase="",
            processed=0,
            total=0,
            current_path="",
            diagnostic=diagnostic,
            failed_source_ids=failed_ids,
            last_diagnostic=run_diagnostic,
            last_source_id=diagnostic_source_id,
        )
        self._start_next()

    def _set_state(self, **changes) -> None:
        self._state = replace(self._state, **changes)
        for cb in list(self._subscribers):
            cb(self._state)
