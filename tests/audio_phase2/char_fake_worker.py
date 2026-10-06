#!/usr/bin/env python
"""Fake characterization worker for single-flight tests (test-only).

Mimics the CLI JSON contract of ``characterize_cli``: accepts --path /
--timeout-ms / --json and sleeps ``CHAR_FAKE_SLEEP_MS`` before responding.

Usage: python -m tests.audio_phase2.char_fake_worker characterize --path P ...
"""

from __future__ import annotations

import json
import os
import sys
import time


def main() -> int:
    sleep_ms = int(os.environ.get("CHAR_FAKE_SLEEP_MS", "0"))
    if sleep_ms > 0:
        time.sleep(sleep_ms / 1000.0)
    payload = {
        "schema_version": 1,
        "ok": True,
        "result": {
            "encoding": "PCM",
            "rate_hz": 44100,
            "channels": 2,
            "significant_bits": 16,
            "channel_positions": None,
        },
    }
    json.dump(payload, sys.stdout)
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
