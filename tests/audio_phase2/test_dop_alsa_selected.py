"""AP2-F09 — selected ALSA DoP carrier vertical (explicit hardware opt-in)."""

from __future__ import annotations

import contextlib
import importlib.util
import os
import time
from pathlib import Path

import pytest

from tests.audio_phase2.test_dsd_source_truth import build_dsf

_HAS_GI = importlib.util.find_spec("gi") is not None
_PREFIX = Path(os.environ.get("MICHI_DOP_PREFIX", "/tmp/michi-dop-gate-a"))
_PLUGIN = _PREFIX / "lib/gstreamer-1.0/libmichidop.so"
_DEVICE = os.environ.get("MICHI_DOP_ALSA_DEVICE", "")

pytestmark = pytest.mark.skipif(
    not _HAS_GI
    or os.environ.get("MICHI_RUN_DOP_HARDWARE") != "1"
    or not _DEVICE
    or not _PLUGIN.exists(),
    reason="selected-ALSA DoP test requires explicit hardware opt-in",
)


def test_selected_alsa_receives_exact_carrier(monkeypatch) -> None:
    from michi.infrastructure.audio_engines.gstreamer_host_client import (
        GStreamerHostSupervisor,
    )
    from michi.infrastructure.audio_engines.gstreamer_host_port import (
        GStreamerHostedAudioPort,
    )

    monkeypatch.setenv("MICHI_DOP_PLUGIN_PREFIX", str(_PREFIX))
    monkeypatch.setenv("GST_PLUGIN_PATH", str(_PLUGIN.parent))
    path = Path(os.environ.get("TMPDIR", "/tmp")) / "michi-dop-silence.dsf"
    payload = bytes([0x69]) * ((352_800 // 4) * 2)
    path.write_bytes(build_dsf(sample_count=352_800 // 4, payload=payload))
    supervisor = GStreamerHostSupervisor(
        start_timeout_s=45.0,
        command_timeout_s=30.0,
        terminate_grace_s=8.0,
        term_grace_s=5.0,
        kill_grace_s=5.0,
    )
    port = GStreamerHostedAudioPort(
        supervisor, command_deadline_s=30.0, load_deadline_s=30.0
    )
    identity = None
    try:
        port.activate()
        identity = port.prepare_dop(
            {
                "path": str(path),
                "plan_id": "dop:alsa-selected",
                "execution_id": "exec:dop-alsa-selected",
                "host_generation": 1,
                "binding_generation": 1,
                "stable_device_id": "selected:alsa",
                "locator": _DEVICE,
                "source_family": "dsf",
                "source_rate_hz": 352_800,
                "carrier_rate_hz": 176_400,
                "carrier_format": "S32LE",
                "channels": 2,
                "reverse_payload_bits": False,
                "sink_factory": "alsasink",
            }
        )
        assert identity["prerolled"] is True
        assert identity["sink_factory"] == "alsasink"
        assert identity["carrier_rate_hz"] == 176_400
        assert identity["carrier_format"] == "S32LE"
        sink = next(
            item for item in identity["observations"] if item["factory"] == "alsasink"
        )
        assert sink["media_type"] == "audio/x-raw"
        expected = {
            key: identity[key]
            for key in (
                "plan_id",
                "execution_id",
                "stable_device_id",
                "device",
                "binding_generation",
                "host_generation",
            )
        }
        assert port.commit_dop(expected)["committed"] is True
        assert port.start_dop()["confirmed"] is True
        deadline = time.monotonic() + 8.0
        while time.monotonic() < deadline:
            if port.query_dop_evidence().get("eos"):
                break
            time.sleep(0.02)
        assert port.query_dop_evidence()["eos"] is True
    finally:
        if identity is not None:
            with contextlib.suppress(Exception):
                port.stop_dop(
                    {
                        key: identity[key]
                        for key in (
                            "plan_id",
                            "execution_id",
                            "stable_device_id",
                            "device",
                            "binding_generation",
                            "host_generation",
                        )
                    }
                )
        supervisor.close()
