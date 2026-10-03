"""Decoded-source characterization worker (subprocess-isolated).

``sys.executable -m michi.infrastructure.audio_engines.characterize_cli
characterize --path <file> --timeout-ms <n> --json``

The worker owns one disposable GStreamer preroll pipeline. The parent kills
the whole process when the budget expires, so a wedged GStreamer state
machine stays inside the worker and can never contaminate the application
process (see diagnostics/wedge-2026-10-03). stdout carries exactly one
bounded JSON object; PCM samples never travel through JSON.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCHEMA_VERSION = 1
TOOL = "michi-characterize"


def _payload_for_error(code: str, detail: str) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "ok": False,
        "error": {"code": code, "detail": detail[:500]},
    }


def _characterize(args: argparse.Namespace) -> int:
    payload: dict
    try:
        from michi.application.audio_output_ports import SourceCharacterizationError
        from michi.infrastructure.audio_engines.gstreamer import GStreamerBindings

        bindings = GStreamerBindings()
        signal = bindings.characterize_local_file(
            Path(args.path), max(1, int(args.timeout_ms)) * 1_000_000
        )
    except SourceCharacterizationError as exc:
        payload = _payload_for_error(exc.code, exc.detail or str(exc))
    except Exception as exc:  # noqa: BLE001 - worker boundary
        payload = _payload_for_error(
            "SOURCE_CHARACTERIZATION_FAILED", f"{type(exc).__name__}: {exc}"
        )
    else:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "ok": True,
            "result": {
                "encoding": signal.encoding,
                "rate_hz": signal.rate_hz,
                "significant_bits": signal.significant_bits,
                "channels": signal.channels,
                "channel_positions": (
                    list(signal.channel_positions)
                    if signal.channel_positions is not None
                    else None
                ),
            },
        }
    json.dump(payload, sys.stdout)
    sys.stdout.write("\n")
    sys.stdout.flush()
    return 0 if payload["ok"] else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog=TOOL)
    sub = parser.add_subparsers(dest="command", required=True)
    characterize = sub.add_parser("characterize")
    characterize.add_argument("--path", required=True)
    characterize.add_argument("--timeout-ms", type=int, default=5000)
    characterize.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "characterize":
        return _characterize(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
