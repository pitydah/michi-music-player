"""Subprocess-isolated decoded-source characterization.

The in-process characterizer shared the application's GStreamer runtime, and
a rare state-change deadlock inside a preroll pipeline could wedge the whole
process (evidence: diagnostics/wedge-2026-10-03, native stacks captured).
This adapter runs the same bounded probe in a disposable worker process; on
timeout the worker is terminated, so a stuck GStreamer state machine costs
one killed process instead of a frozen application and can never block the
Direct pipeline's own state changes.
"""

from __future__ import annotations

import contextlib
import json
import subprocess
import sys
import threading
from collections.abc import Callable
from pathlib import Path

from michi.application.audio_output_ports import SourceCharacterizationError
from michi.domain.audio_evidence import DecodedSourceSignal

MODULE = "michi.infrastructure.audio_engines.characterize_cli"
SCHEMA_VERSION = 1
DEFAULT_TIMEOUT_MS = 5_000
KILL_GRACE_S = 0.5
MAX_OUTPUT_BYTES = 64 * 1024


class SubprocessSourceCharacterizer:
    """Bounded, generation-safe decoded-source characterization facade."""

    def __init__(
        self,
        *,
        executable: str | None = None,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
        kill_grace_s: float = KILL_GRACE_S,
    ) -> None:
        self._executable = executable or sys.executable
        self._timeout_ms = max(1, int(timeout_ms))
        self._timeout_s = self._timeout_ms / 1000.0
        self._kill_grace_s = kill_grace_s
        self._lock = threading.Lock()
        self._generation = 0
        self._active: subprocess.Popen | None = None

    def characterize(self, path: Path) -> DecodedSourceSignal:
        with self._lock:
            self._generation += 1
            generation = self._generation
        source = Path(path)
        if not source.is_file():
            raise SourceCharacterizationError(
                "SOURCE_FILE_UNAVAILABLE", f"local source does not exist: {source}"
            )
        stdout, stderr, exit_code, timed_out = self._run(self._argv(source))
        with self._lock:
            stale = generation != self._generation
        if stale:
            raise SourceCharacterizationError(
                "SOURCE_CHARACTERIZATION_STALE",
                "decoded-source result belongs to a superseded generation",
            )
        if timed_out:
            raise SourceCharacterizationError(
                "SOURCE_CHARACTERIZATION_TIMEOUT",
                f"characterization worker exceeded {self._timeout_s:.3f}s "
                "and was terminated",
            )
        payload = self._parse(stdout)
        if payload is None:
            detail = (
                stderr.decode("utf-8", "replace").strip()[:500]
                or "stdout sin JSON válido"
            )
            raise SourceCharacterizationError("SOURCE_CHARACTERIZATION_FAILED", detail)
        if payload.get("schema_version") != SCHEMA_VERSION:
            raise SourceCharacterizationError(
                "SOURCE_CHARACTERIZATION_FAILED",
                f"schema_version inesperado: {payload.get('schema_version')!r}",
            )
        if exit_code != 0 or not payload.get("ok"):
            error = payload.get("error") or {}
            raise SourceCharacterizationError(
                str(error.get("code") or "SOURCE_CHARACTERIZATION_FAILED"),
                str(error.get("detail") or "characterization worker failed"),
            )
        return self._signal(payload.get("result") or {})

    def cancel(self) -> None:
        with self._lock:
            self._generation += 1
            active = self._active
        if active is not None:
            self._terminate(active)

    def _argv(self, source: Path) -> list[str]:
        return [
            self._executable,
            "-m",
            MODULE,
            "characterize",
            "--path",
            str(source),
            "--timeout-ms",
            str(self._timeout_ms),
            "--json",
        ]

    def _signal(self, result: dict) -> DecodedSourceSignal:
        try:
            encoding = str(result["encoding"])
            rate_hz = int(result["rate_hz"])
            channels = int(result["channels"])
            significant_bits = (
                int(result["significant_bits"])
                if result.get("significant_bits") is not None
                else None
            )
            positions = result.get("channel_positions")
            channel_positions = (
                tuple(str(position) for position in positions)
                if isinstance(positions, list)
                else None
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise SourceCharacterizationError(
                "SOURCE_CHARACTERIZATION_FAILED", f"resultado inválido: {exc}"
            ) from exc
        if encoding != "PCM" or rate_hz <= 0 or channels <= 0:
            raise SourceCharacterizationError(
                "SOURCE_CHARACTERIZATION_FAILED",
                "decoded PCM rate/channels are unavailable",
            )
        return DecodedSourceSignal(
            encoding=encoding,
            rate_hz=rate_hz,
            significant_bits=significant_bits,
            channels=channels,
            channel_positions=channel_positions,
        )

    def _run(self, argv: list[str]) -> tuple[bytes, bytes, int, bool]:
        try:
            proc = subprocess.Popen(
                argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
        except OSError as exc:
            return b"", str(exc).encode("utf-8"), -1, False
        with self._lock:
            self._active = proc
        try:
            stdout, stderr = proc.communicate(timeout=self._timeout_s)
            return (
                stdout[:MAX_OUTPUT_BYTES],
                stderr[:MAX_OUTPUT_BYTES],
                proc.returncode or 0,
                False,
            )
        except subprocess.TimeoutExpired:
            self._terminate(proc)
            try:
                stdout, stderr = proc.communicate(timeout=self._kill_grace_s)
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout, stderr = proc.communicate()
            return (
                stdout[:MAX_OUTPUT_BYTES],
                stderr[:MAX_OUTPUT_BYTES],
                proc.returncode or -1,
                True,
            )
        finally:
            with self._lock:
                if self._active is proc:
                    self._active = None

    @staticmethod
    def _terminate(proc: subprocess.Popen) -> None:
        try:
            proc.terminate()
        except OSError:
            return

    def _parse(self, stdout: bytes) -> dict | None:
        if not stdout:
            return None
        try:
            payload = json.loads(stdout.decode("utf-8", "replace"))
        except json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None


class PumpedSourceCharacterizer:
    """Owner-responsive wrapper around a (bounded) source characterizer.

    The inner ``characterize`` runs on a disposable worker thread; the
    CALLING thread waits in short slices and invokes ``pump`` between them.
    With a Qt pump, timers/input/paint keep running while the bounded
    characterization subprocess completes — the owner never freezes for the
    full characterization budget. Cancellation reaches the inner port so a
    superseded preparation aborts its worker instead of waiting it out.
    """

    def __init__(
        self,
        inner,
        *,
        pump: Callable[[], None] | None = None,
        slice_s: float = 0.01,
    ) -> None:
        self._inner = inner
        self._pump = pump
        self._slice_s = max(0.001, float(slice_s))

    def characterize(self, path: Path) -> DecodedSourceSignal:
        holder: dict[str, object] = {}

        def run() -> None:
            try:
                holder["value"] = self._inner.characterize(Path(path))
            except BaseException as exc:  # noqa: BLE001 - re-raised on caller
                holder["error"] = exc

        worker = threading.Thread(
            target=run, name="michi-characterize-wait", daemon=True
        )
        worker.start()
        while True:
            if self._pump is not None:
                with contextlib.suppress(Exception):  # pumping is best-effort
                    self._pump()
            worker.join(timeout=self._slice_s)
            if not worker.is_alive():
                break
        if "error" in holder:
            raise holder["error"]  # type: ignore[misc]
        return holder["value"]  # type: ignore[return-value]

    def cancel(self) -> None:
        cancel = getattr(self._inner, "cancel", None)
        if cancel is not None:
            cancel()
