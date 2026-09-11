"""DAC-V35-020 — MichiAlsaProbeAdapter (spec §13, subprocess contract).

Invoca `<sys.executable> -m michi.infrastructure.audio_devices.alsa_probe_cli`
para provenance determinística (venv/wheel). El alias instalado
`michi-alsa-probe` es solo para humanos/CI.

Contrato: timeout 1500 ms, kill grace 250 ms, stdout/stderr acotados a
64 KiB, schema mismatch -> protocol_error, non-zero + JSON válido ->
el JSON tipado gana, non-zero + sin JSON -> protocol_error.
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
import time

from michi.domain.audio_evidence import ExactProbeResult, PcmTuple

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_S = 1.5
KILL_GRACE_S = 0.25
MAX_STDOUT_BYTES = 64 * 1024
MAX_STDERR_BYTES = 64 * 1024
SCHEMA_VERSION = 1
MODULE = "michi.infrastructure.audio_devices.alsa_probe_cli"


class MichiAlsaProbeAdapter:
    def __init__(
        self,
        *,
        executable: str | None = None,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        kill_grace_s: float = KILL_GRACE_S,
    ) -> None:
        self._executable = executable or sys.executable
        self._timeout_s = timeout_s
        self._kill_grace_s = kill_grace_s

    def probe_exact(
        self,
        *,
        locator: str,
        rate_hz: int,
        transport_format: str,
        channels: int,
    ) -> ExactProbeResult:
        requested = PcmTuple(
            rate_hz=rate_hz,
            transport_format=transport_format,
            channels=channels,
            significant_bits=None,
        )
        started_ns = time.monotonic_ns()
        evidence_ref = f"michi-alsa-probe:{started_ns}:{locator}"
        argv = [
            self._executable,
            "-m",
            MODULE,
            "probe",
            "--device",
            locator,
            "--rate",
            str(rate_hz),
            "--format",
            transport_format,
            "--channels",
            str(channels),
            "--json",
        ]
        stdout, stderr, exit_code, timed_out = self._run(argv)
        if timed_out:
            return ExactProbeResult(
                requested=requested,
                negotiated=None,
                disposition="timeout",
                alsa_error_code=None,
                detail=f"probe excedió {self._timeout_s:.3f}s",
                evidence_ref=evidence_ref,
            )
        payload = self._parse(stdout)
        if payload is None:
            detail = (
                stderr.decode("utf-8", "replace").strip()[:500]
                or "stdout sin JSON válido"
            )
            return ExactProbeResult(
                requested=requested,
                negotiated=None,
                disposition="protocol_error",
                alsa_error_code=None,
                detail=detail,
                evidence_ref=evidence_ref,
            )
        if payload.get("schema_version") != SCHEMA_VERSION:
            return ExactProbeResult(
                requested=requested,
                negotiated=None,
                disposition="protocol_error",
                alsa_error_code=None,
                detail=f"schema_version inesperado: {payload.get('schema_version')!r}",
                evidence_ref=evidence_ref,
            )
        if exit_code != 0 or not payload.get("ok"):
            error = payload.get("error") or {}
            return ExactProbeResult(
                requested=requested,
                negotiated=None,
                disposition=str(error.get("category") or "unknown"),
                alsa_error_code=error.get("alsa_error_code"),
                detail=error.get("detail"),
                evidence_ref=evidence_ref,
            )
        result = payload.get("result") or {}
        negotiated_payload = result.get("negotiated") or {}
        try:
            negotiated = PcmTuple(
                rate_hz=int(negotiated_payload["rate_hz"]),
                transport_format=str(negotiated_payload["format"]),
                channels=int(negotiated_payload["channels"]),
                significant_bits=(
                    int(negotiated_payload["significant_bits"])
                    if negotiated_payload.get("significant_bits") is not None
                    else None
                ),
            )
        except (KeyError, TypeError, ValueError) as exc:
            return ExactProbeResult(
                requested=requested,
                negotiated=None,
                disposition="protocol_error",
                alsa_error_code=None,
                detail=f"negotiated inválido: {exc}",
                evidence_ref=evidence_ref,
            )
        return ExactProbeResult(
            requested=requested,
            negotiated=negotiated,
            disposition="OPENED",
            alsa_error_code=None,
            detail=None,
            evidence_ref=evidence_ref,
        )

    def _run(self, argv: list[str]) -> tuple[bytes, bytes, int, bool]:
        try:
            proc = subprocess.Popen(
                argv,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except OSError as exc:
            logger.error("no se pudo lanzar el probe: %s", exc)
            return b"", str(exc).encode("utf-8"), -1, False
        try:
            stdout, stderr = proc.communicate(timeout=self._timeout_s)
            return stdout, stderr, proc.returncode or 0, False
        except subprocess.TimeoutExpired:
            proc.terminate()
            try:
                stdout, stderr = proc.communicate(timeout=self._kill_grace_s)
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout, stderr = proc.communicate()
            return (
                stdout[:MAX_STDOUT_BYTES],
                stderr[:MAX_STDERR_BYTES],
                proc.returncode or -1,
                True,
            )

    def _parse(self, stdout: bytes) -> dict | None:
        if not stdout:
            return None
        try:
            payload = json.loads(stdout[:MAX_STDOUT_BYTES].decode("utf-8", "replace"))
        except json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None
