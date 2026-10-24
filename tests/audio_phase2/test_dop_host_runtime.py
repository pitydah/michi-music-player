"""AP2-F09 — Gate A DoP vertical through the supervised GStreamer host.

The Rust element lives in an isolated plugin prefix. The test is skipped when
that Gate A artifact is not installed; it never falls back to the checkout.
"""

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

pytestmark = pytest.mark.skipif(
    not _HAS_GI or not _PLUGIN.exists(),
    reason="Gate A michidop artifact is not installed in its private prefix",
)


def _payload(path: Path) -> dict:
    return {
        "path": str(path),
        "plan_id": "dop:host-test",
        "execution_id": "exec:dop-host",
        "host_generation": 1,
        "binding_generation": 1,
        "stable_device_id": "usb:test",
        "locator": "hw:3,0",
        "source_family": "dsf",
        "source_rate_hz": 352_800,
        "carrier_rate_hz": 176_400,
        "carrier_format": "S32LE",
        "channels": 2,
        "reverse_payload_bits": False,
        "sink_factory": "fakesink",
    }


def _supervisor_and_port():
    from michi.infrastructure.audio_engines.gstreamer_host_client import (
        GStreamerHostSupervisor,
    )
    from michi.infrastructure.audio_engines.gstreamer_host_port import (
        GStreamerHostedAudioPort,
    )

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
    return supervisor, port


def test_gate_a_dop_host_vertical_is_explicit_and_confirmed(
    tmp_path, monkeypatch
) -> None:
    dsf = tmp_path / "dop.dsf"
    dsf.write_bytes(build_dsf(sample_count=2_822_400))
    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    monkeypatch.setenv("GST_PLUGIN_PATH", str(_PLUGIN.parent))
    monkeypatch.setenv("MICHI_DOP_PLUGIN_PREFIX", str(_PREFIX))
    supervisor, port = _supervisor_and_port()
    try:
        port.activate()
        identity = port.prepare_dop(_payload(dsf))
        assert identity["dop"] is True
        assert identity["prerolled"] is True
        assert identity["plugin_filename"].startswith(str(_PREFIX))
        assert identity["carrier_rate_hz"] == 176_400
        assert identity["carrier_format"] == "S32LE"
        observations = {item["role"]: item for item in identity["observations"]}
        assert observations["michidop"]["media_type"] == "audio/x-raw"
        assert observations["sink"]["media_type"] == "audio/x-raw"
        assert "audio/x-dsd" in observations["dsd_caps"]["media_type"]
        expected = {
            "plan_id": identity["plan_id"],
            "execution_id": identity["execution_id"],
            "stable_device_id": identity["stable_device_id"],
            "device": identity["device"],
            "binding_generation": identity["binding_generation"],
            "host_generation": identity["host_generation"],
        }
        assert port.commit_dop(expected)["committed"] is True
        eom: list[bool] = []
        port.subscribe_end_of_media(lambda: eom.append(True))
        assert port.start_dop()["state"] == "PLAYING"
        deadline = time.monotonic() + 8.0
        while not eom and time.monotonic() < deadline:
            port.dispatch_pending()
            time.sleep(0.02)
        port.dispatch_pending()
        assert eom, "DoP EOS never reached the parent"
        evidence = port.query_dop_evidence()
        assert evidence["dop"] is True
        assert evidence["execution_id"] == "exec:dop-host"
    finally:
        with contextlib.suppress(Exception):
            port.abort_dop(expected)
        supervisor.close()
