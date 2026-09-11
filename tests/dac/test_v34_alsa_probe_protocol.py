"""DAC-V35-020 — contrato de protocolo del worker alsa-probe (§13).

- stdout: exactamente un JSON versionado; stderr: diagnóstico;
- device ausente -> error tipado, NUNCA "unsupported";
- locator no-hw: -> protocol_error;
- adapter: schema mismatch / garbage / non-zero+JSON / timeout.
"""

from __future__ import annotations

import json
import subprocess
import sys

from michi.domain.audio_evidence import PcmTuple
from michi.infrastructure.audio_devices.alsa_probe_adapter import (
    MODULE,
    MichiAlsaProbeAdapter,
)

OK_ENVELOPE = {
    "schema_version": 1,
    "tool": "michi-alsa-probe",
    "implementation": "python-ctypes-libasound",
    "operation": "probe",
    "ok": True,
    "result": {
        "requested": {
            "device": "hw:CARD=DX5,DEV=0",
            "rate_hz": 96000,
            "format": "S32_LE",
            "channels": 2,
        },
        "negotiated": {
            "rate_hz": 96000,
            "format": "S32_LE",
            "channels": 2,
            "significant_bits": 24,
        },
    },
    "error": None,
}


def _cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", MODULE, *args, "--json"],
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_version_emits_single_json_envelope() -> None:
    proc = _cli("version")
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == 1
    assert payload["tool"] == "michi-alsa-probe"
    assert payload["implementation"] == "python-ctypes-libasound"
    assert payload["operation"] == "version"
    if proc.returncode == 0:
        assert payload["ok"] is True
        assert payload["error"] is None
        assert isinstance(payload["result"]["version"], str)
    else:
        # sin libasound en el entorno: error tipado, nunca crash
        assert payload["ok"] is False
        assert payload["error"]["category"] == "alsa_runtime_missing"


def test_missing_device_is_typed_error_never_unsupported() -> None:
    proc = _cli(
        "probe",
        "--device",
        "hw:CARD=NoSuchDac,DEV=0",
        "--rate",
        "96000",
        "--format",
        "S32_LE",
        "--channels",
        "2",
    )
    assert proc.returncode != 0
    payload = json.loads(proc.stdout)
    assert payload["ok"] is False
    category = payload["error"]["category"]
    assert category == "device_removed", (
        f"device ausente debe ser removed/typed, no {category}"
    )
    assert category != "unsupported_format"


def test_non_hw_locator_is_protocol_error() -> None:
    proc = _cli(
        "probe",
        "--device",
        "default",
        "--rate",
        "48000",
        "--format",
        "S16_LE",
        "--channels",
        "2",
    )
    assert proc.returncode != 0
    payload = json.loads(proc.stdout)
    assert payload["error"]["category"] == "protocol_error"


def test_adapter_parses_ok_envelope() -> None:
    adapter = MichiAlsaProbeAdapter()
    adapter._run = lambda argv: (json.dumps(OK_ENVELOPE).encode(), b"", 0, False)
    result = adapter.probe_exact(
        locator="hw:CARD=DX5,DEV=0",
        rate_hz=96000,
        transport_format="S32_LE",
        channels=2,
    )
    assert result.disposition == "OPENED"
    assert result.negotiated == PcmTuple(96000, "S32_LE", 2, 24)
    assert result.requested == PcmTuple(96000, "S32_LE", 2, None)


def test_adapter_schema_mismatch_is_protocol_error() -> None:
    bad = dict(OK_ENVELOPE, schema_version=2)
    adapter = MichiAlsaProbeAdapter()
    adapter._run = lambda argv: (json.dumps(bad).encode(), b"", 0, False)
    result = adapter.probe_exact(
        locator="hw:CARD=DX5,DEV=0",
        rate_hz=96000,
        transport_format="S32_LE",
        channels=2,
    )
    assert result.disposition == "protocol_error"
    assert result.negotiated is None


def test_adapter_nonzero_exit_with_valid_json_wins() -> None:
    err = {
        "schema_version": 1,
        "tool": "michi-alsa-probe",
        "implementation": "python-ctypes-libasound",
        "operation": "probe",
        "ok": False,
        "result": None,
        "error": {"category": "device_busy", "alsa_error_code": 16, "detail": "busy"},
    }
    adapter = MichiAlsaProbeAdapter()
    adapter._run = lambda argv: (json.dumps(err).encode(), b"", 1, False)
    result = adapter.probe_exact(
        locator="hw:CARD=DX5,DEV=0",
        rate_hz=96000,
        transport_format="S32_LE",
        channels=2,
    )
    assert result.disposition == "device_busy"
    assert result.alsa_error_code == 16


def test_adapter_garbage_stdout_is_protocol_error() -> None:
    adapter = MichiAlsaProbeAdapter()
    adapter._run = lambda argv: (b"no soy json", b"stderr text", 0, False)
    result = adapter.probe_exact(
        locator="hw:CARD=DX5,DEV=0",
        rate_hz=96000,
        transport_format="S32_LE",
        channels=2,
    )
    assert result.disposition == "protocol_error"
    assert "stderr" in (result.detail or "")


def test_adapter_timeout_kills_and_reports_timeout() -> None:
    adapter = MichiAlsaProbeAdapter(timeout_s=0.001, kill_grace_s=0.05)
    result = adapter.probe_exact(
        locator="hw:CARD=DX5,DEV=0",
        rate_hz=96000,
        transport_format="S32_LE",
        channels=2,
    )
    assert result.disposition == "timeout"
    assert result.negotiated is None


def test_adapter_oversized_stdout_is_bounded() -> None:
    adapter = MichiAlsaProbeAdapter()
    blob = b"x" * (200 * 1024)
    adapter._run = lambda argv: (blob, b"", 0, False)
    result = adapter.probe_exact(
        locator="hw:CARD=DX5,DEV=0",
        rate_hz=96000,
        transport_format="S32_LE",
        channels=2,
    )
    assert result.disposition == "protocol_error"
