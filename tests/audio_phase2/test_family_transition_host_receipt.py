"""AP2-F10 — transition planner consumes real DSD/DoP host release receipts."""

from __future__ import annotations

import importlib.util

import pytest

from michi.application.audio_family_transition import (
    AudioFamily,
    AudioFamilyTransitionService,
    FamilyTransitionRequest,
    PlaybackStatus,
)
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


def _plan(*, source: AudioFamily, target: AudioFamily, identity: dict, released: dict):
    return AudioFamilyTransitionService().plan(
        FamilyTransitionRequest(
            media_identity="host:transition",
            source_family=source,
            target_family=target,
            predecessor_status=PlaybackStatus.PLAYING,
            request_epoch=2,
            current_epoch=1,
            output_generation=1,
            processing_generation=0,
            binding_generation=int(identity["binding_generation"]),
            destructive_boundary=True,
            plan_id=str(identity["plan_id"]),
            execution_id=str(identity["execution_id"]),
            stable_device_id=str(identity["stable_device_id"]),
            host_generation=int(identity["host_generation"]),
        )
    )


def test_real_host_receipts_release_dsd_then_dop_and_reverse(tmp_path):
    from michi.infrastructure.audio_engines.gstreamer_host_client import (
        GStreamerHostSupervisor,
    )
    from michi.infrastructure.audio_engines.gstreamer_host_port import (
        GStreamerHostedAudioPort,
    )

    source = tmp_path / "transition.dsf"
    source.write_bytes(build_dsf(sample_count=8_192, payload=bytes([0x69]) * 16_384))
    plan = DsdToPcmPlanner().plan(
        source_identity="host:transition",
        source_format=_format(),
        quality_profile="FAST",
        binding_generation=1,
        available_output_rates=(88_200,),
        decoder_available=True,
        target_qualified=True,
        backend_version="gst-libav",
        stable_device_id="dev:transition",
        binding_locator="lab",
        host_generation=1,
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
    try:
        port.activate()
        dsd_identity = port.prepare_dsd_pcm(_dsd_payload(plan, source))
        dsd_expected = {
            "plan_id": dsd_identity["plan_id"],
            "execution_id": dsd_identity["execution_id"],
            "stable_device_id": dsd_identity["stable_device_id"],
            "device": dsd_identity["device"],
            "binding_generation": dsd_identity["binding_generation"],
            "host_generation": dsd_identity["host_generation"],
        }
        port.commit_dsd_pcm(dsd_expected)
        port.start_dsd_pcm(dsd_expected)
        dsd_release = port.stop_dsd_pcm(dsd_expected)
        dsd_receipt = dsd_release["release"]
        transition = _plan(
            source=AudioFamily.DSD_TO_PCM,
            target=AudioFamily.DOP,
            identity=dsd_identity,
            released=dsd_receipt,
        )
        marked = AudioFamilyTransitionService().mark_released(transition, dsd_receipt)
        assert marked.predecessor_released is True

        dop_source = tmp_path / "transition.dop.dsf"
        dop_source.write_bytes(build_dsf(sample_count=8_192))
        dop_identity = port.prepare_dop(_dop_payload(dop_source))
        dop_expected = {
            "plan_id": dop_identity["plan_id"],
            "execution_id": dop_identity["execution_id"],
            "stable_device_id": dop_identity["stable_device_id"],
            "device": dop_identity["device"],
            "binding_generation": dop_identity["binding_generation"],
            "host_generation": dop_identity["host_generation"],
        }
        port.commit_dop(dop_expected)
        port.start_dop()
        dop_release = port.stop_dop(dop_expected)
        dop_receipt = dop_release["release"]
        reverse = _plan(
            source=AudioFamily.DOP,
            target=AudioFamily.DSD_TO_PCM,
            identity=dop_identity,
            released=dop_receipt,
        )
        marked_reverse = AudioFamilyTransitionService().mark_released(
            reverse, dop_receipt
        )
        assert marked_reverse.predecessor_released is True
    finally:
        supervisor.close()
