"""AP2-F10 — host family exclusivity and ordered handover."""

from __future__ import annotations

import importlib.util

import pytest

from michi.application.dsd_to_pcm_plan import DsdToPcmPlanner
from tests.audio_phase2.test_dop_host_runtime import _PREFIX
from tests.audio_phase2.test_dop_host_runtime import _payload as _dop_payload
from tests.audio_phase2.test_dsd_pcm_host import _format
from tests.audio_phase2.test_dsd_pcm_host import _payload as _dsd_payload
from tests.audio_phase2.test_dsd_source_truth import build_dsf

_HAS_GI = importlib.util.find_spec("gi") is not None

pytestmark = pytest.mark.skipif(
    not _HAS_GI or _PREFIX is None,
    reason="GStreamer or Gate A michidop prefix unavailable",
)


def _ports():
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


def test_dop_prepare_is_denied_while_dsd_pcm_owns_the_host(tmp_path):
    plan = DsdToPcmPlanner().plan(
        source_identity="exclusive:dsd",
        source_format=_format(),
        quality_profile="FAST",
        binding_generation=1,
        available_output_rates=(88_200,),
        decoder_available=True,
        target_qualified=True,
        backend_version="gst-libav",
        stable_device_id="dev:exclusive",
        binding_locator="lab",
        host_generation=1,
    )
    dsd = tmp_path / "exclusive.dsf"
    dsd.write_bytes(build_dsf(sample_count=8_192))
    dop = tmp_path / "exclusive-dop.dsf"
    dop.write_bytes(build_dsf(sample_count=8_192))
    supervisor, port = _ports()
    try:
        port.activate()
        identity = port.prepare_dsd_pcm(_dsd_payload(plan, dsd))
        expected = {
            "plan_id": identity["plan_id"],
            "execution_id": identity["execution_id"],
            "stable_device_id": identity["stable_device_id"],
            "device": identity["device"],
            "binding_generation": identity["binding_generation"],
            "host_generation": identity["host_generation"],
        }
        with pytest.raises(Exception, match="DOP_DSD_PCM_CONFLICT"):
            port.prepare_dop(_dop_payload(dop))
        port.abort_dsd_pcm(expected)
        # After confirmed release the destination can be prepared.
        port.prepare_dop(_dop_payload(dop))
    finally:
        supervisor.close()
