"""DAC-V35-020 — `michi-alsa-probe` CLI worker (spec §13).

`sys.executable -m michi.infrastructure.audio_devices.alsa_probe_cli`
con subcomandos version/enumerate/probe. stdout: exactamente UN objeto
JSON acotado; stderr: diagnóstico. Los samples nunca viajan por JSON.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys

from michi.infrastructure.audio_devices import alsa_ctypes
from michi.infrastructure.audio_devices.alsa_ctypes import (
    FORMAT_IDS,
    AlsaProbeError,
    AlsaRuntimeMissingError,
)

SCHEMA_VERSION = 1
TOOL = "michi-alsa-probe"
IMPLEMENTATION = "python-ctypes-libasound"

logger = logging.getLogger("michi-alsa-probe")

_FORMAT_NAMES = {value: name for name, value in FORMAT_IDS.items()}


def classify_error(error: AlsaProbeError) -> str:
    """Clasificación layer-aware (step + errno), nunca adivina soporte."""
    code = error.errno_code
    if code == 16:  # EBUSY
        return "device_busy"
    if code in (2, 19):  # ENOENT / ENODEV
        return "device_removed"
    if code in (1, 13):  # EPERM / EACCES
        return "permission_denied"
    if error.step in ("set_format", "set_rate", "set_channels"):
        if error.errno_code == 22:  # EINVAL: rechazo exacto inequívoco
            return "unsupported_format"
        # EIO/runtime (o cualquier otro errno): el tuple NO queda probado
        # como unsupported; la ambigüedad nunca produce evidencia negativa.
        return "negotiation_failed"
    if error.step == "hw_params":
        return "negotiation_failed"
    if error.step.startswith("readback_"):
        # C04: un readback fallido NUNCA es soporte; tampoco rechazo exacto.
        return "negotiation_failed"
    if error.step == "validate":
        return "protocol_error"
    return "internal_error"


def _requested_payload(args: argparse.Namespace) -> dict:
    return {
        "device": args.device,
        "rate_hz": args.rate,
        "format": args.format,
        "channels": args.channels,
    }


def _envelope(operation: str, ok: bool, result: object, error: object) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "tool": TOOL,
        "implementation": IMPLEMENTATION,
        "operation": operation,
        "ok": ok,
        "result": result,
        "error": error,
    }


def _error_envelope(
    operation: str, category: str, alsa_error_code: int | None, detail: str
) -> dict:
    return _envelope(
        operation,
        False,
        None,
        {
            "category": category,
            "alsa_error_code": alsa_error_code,
            "detail": detail,
        },
    )


_EXACT_REJECTION_STEPS = ("set_format", "set_rate", "set_channels")


def _probe_once(args: argparse.Namespace) -> tuple[dict, bool]:
    """Un intento exacto; devuelve (envelope JSON, retryable).

    `retryable` es True SOLO para el rechazo exacto EINVAL de los setters
    (semántica de rechazo intencionada), nunca para cualquier categoría
    genérica.
    """
    try:
        negotiated = alsa_ctypes.probe_exact(
            args.device,
            rate_hz=args.rate,
            transport_format=args.format,
            channels=args.channels,
        )
    except AlsaRuntimeMissingError as exc:
        return _error_envelope("probe", "alsa_runtime_missing", None, str(exc)), False
    except AlsaProbeError as exc:
        retryable = exc.errno_code == 22 and exc.step in _EXACT_REJECTION_STEPS
        return (
            _error_envelope("probe", classify_error(exc), exc.errno_code, exc.message),
            retryable,
        )
    negotiated_payload = {
        "rate_hz": negotiated.rate_hz,
        "format": _FORMAT_NAMES.get(negotiated.format_id, str(negotiated.format_id)),
        "channels": negotiated.channels,
        "significant_bits": negotiated.significant_bits,
    }
    requested = _requested_payload(args)
    exact = (
        negotiated_payload["rate_hz"] == requested["rate_hz"]
        and negotiated_payload["format"] == requested["format"]
        and negotiated_payload["channels"] == requested["channels"]
    )
    if not exact:
        return _error_envelope(
            "probe",
            "negotiation_failed",
            None,
            f"negotiated {negotiated_payload} != requested {requested}",
        )
    return (
        _envelope(
            "probe",
            True,
            {"requested": requested, "negotiated": negotiated_payload},
            None,
        ),
        False,
    )


def _run_probe(args: argparse.Namespace) -> tuple[dict, int]:
    envelope, retryable = _probe_once(args)
    if retryable:
        # Gate §401: retry-once SOLO para el rechazo exacto de setters.
        logger.warning("EINVAL en setter exacto: retry-once del mismo tuple")
        # El rechazo se conserva solo si el retry también lo confirma.
        envelope, _ = _probe_once(args)
    return envelope, 0 if envelope["ok"] else 1


def _run_version() -> tuple[dict, int]:
    try:
        version = alsa_ctypes.library_version()
    except AlsaRuntimeMissingError as exc:
        return _error_envelope("version", "alsa_runtime_missing", None, str(exc)), 1
    return _envelope(
        "version", True, {"library": "libasound.so.2", "version": version}, None
    ), 0


def _run_enumerate() -> tuple[dict, int]:
    from pathlib import Path

    from michi.infrastructure.audio_devices.sysfs_snapshot import read_alsa_cards

    cards = read_alsa_cards(Path("/sys"))
    devices = [
        {
            "locator": card.binding.locator,
            "card_index": card.binding.card_index,
            "pcm_device": card.binding.pcm_device,
            "physical_path": card.physical_path,
        }
        for card in cards
        if card.binding is not None
    ]
    return _envelope("enumerate", True, {"devices": devices}, None), 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=TOOL)
    parser.add_argument("--json", action="store_true", help="salida JSON (siempre)")
    sub = parser.add_subparsers(dest="operation", required=True)
    sub.add_parser("version")
    sub.add_parser("enumerate")
    probe = sub.add_parser("probe")
    probe.add_argument("--device", required=True)
    probe.add_argument("--rate", type=int, required=True)
    probe.add_argument("--format", required=True)
    probe.add_argument("--channels", type=int, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(stream=sys.stderr, level=logging.WARNING)
    parser = _build_parser()
    # --json puede aparecer antes o después del subcomando
    args, _unknown = parser.parse_known_args(argv)
    if args.operation == "version":
        envelope, exit_code = _run_version()
    elif args.operation == "enumerate":
        envelope, exit_code = _run_enumerate()
    else:
        envelope, exit_code = _run_probe(args)
    sys.stdout.write(json.dumps(envelope, separators=(",", ":")) + "\n")
    sys.stdout.flush()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
