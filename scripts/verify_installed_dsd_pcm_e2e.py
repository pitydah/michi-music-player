#!/usr/bin/env python3
"""Installed-wheel AP2-F10 DSD→PCM product vertical.

Runs from outside the source checkout and imports only the installed ``michi``
package. It traverses PlaybackService → OutputSessionService → supervised
GStreamer host → gst-libav DSD→PCM → explicit fakesink lab sink.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
import time
from pathlib import Path

F32LE = "F32LE"


def build_dsf(*, sample_count: int, payload: bytes) -> bytes:
    file_size = 28 + 52 + 12 + len(payload)
    header = b"DSD " + struct.pack("<QQQ", 28, file_size, 0)
    fmt = (
        b"fmt "
        + struct.pack("<Q", 52)
        + struct.pack("<II", 1, 0)
        + struct.pack("<I", 2)
        + struct.pack("<I", 2)
        + struct.pack("<I", 2_822_400)
        + struct.pack("<I", 8)
        + struct.pack("<Q", sample_count)
        + struct.pack("<I", 4096)
        + struct.pack("<I", 0)
    )
    return header + fmt + b"data" + struct.pack("<Q", 12 + len(payload)) + payload


def payload(sample_count: int) -> bytes:
    frames = sample_count * 4
    return bytes(0x69 if index % 2 == 0 else 0x96 for index in range(frames))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()

    import michi
    from michi.application.audio_output_planner import OutputPlanner
    from michi.application.dsd_to_pcm_plan import DsdToPcmPlanner
    from michi.application.output_session_service import (
        DsdPcmSessionPrepared,
        OutputRequest,
        OutputSessionService,
    )
    from michi.application.playback_service import PlaybackService
    from michi.domain.audio_output import OutputSessionState
    from michi.domain.dsd_signal import (
        DsdBitOrder,
        DsdOrganization,
        DsdPacking,
        DsdSignalFormat,
    )
    from michi.domain.signal_truth import OutputFamilyState, SignalTruthRecorder
    from michi.infrastructure.audio_engines.gstreamer_host_client import (
        GStreamerHostSupervisor,
    )
    from michi.infrastructure.audio_engines.gstreamer_host_port import (
        GStreamerHostedAudioPort,
    )

    package_path = Path(michi.__file__).resolve()
    if "site-packages" not in package_path.parts:
        raise SystemExit(f"INSTALLED_PACKAGE_REQUIRED: {package_path}")
    if Path.cwd().resolve() in package_path.parents:
        raise SystemExit("CHECKOUT_IMPORT_REJECTED")

    source_format = DsdSignalFormat(
        bit_rate_hz=2_822_400,
        channels=2,
        packing=DsdPacking.DSD_U8,
        bit_order=DsdBitOrder.LSBF,
        organization=DsdOrganization.INTERLEAVED,
        layout=("FL", "FR"),
    )
    plan = DsdToPcmPlanner().plan(
        source_identity="installed:dsd64",
        source_format=source_format,
        quality_profile="FAST",
        binding_generation=1,
        available_output_rates=(88_200,),
        decoder_available=True,
        target_qualified=True,
        backend_version="gst-libav",
        stable_device_id="dev:installed-lab",
        binding_locator="lab",
        host_generation=1,
        policy_revision=1,
        evidence_refs=("installed-wheel:e2e",),
    )
    source = Path("/tmp/michi-installed-dsd64.dsf")
    source.write_bytes(build_dsf(sample_count=44_100, payload=payload(44_100)))

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
    truth = SignalTruthRecorder()
    holder: dict[str, OutputSessionService] = {}

    def prepare(plan_value, path, instance_id):
        identity = port.prepare_dsd_pcm(
            {
                "path": str(path),
                "plan_id": plan_value.plan_id,
                "execution_id": instance_id,
                "binding_generation": plan_value.binding_generation,
                "stable_device_id": plan_value.stable_device_id,
                "locator": plan_value.binding_locator,
                "source_family": "dsf",
                "source_rate_hz": plan_value.source_format.bit_rate_hz,
                "source_bits": plan_value.source_format.bit_rate_hz,
                "bit_order": plan_value.source_format.bit_order.value,
                "channels": plan_value.channels,
                "decoder_factory": plan_value.decoder_factory,
                "target_rate_hz": plan_value.target_rate_hz,
                "output_format": plan_value.output_format,
                "quality_profile": plan_value.quality_profile,
                "resampler_policy": [
                    list(item) for item in plan_value.resampler_policy
                ],
                "sink_factory": "fakesink",
            }
        )
        port.add_dsd_pcm_eos_listener(holder["session"].notify_dsd_pcm_eos)
        expected = {
            "plan_id": identity["plan_id"],
            "execution_id": identity["execution_id"],
            "stable_device_id": identity["stable_device_id"],
            "device": identity["device"],
            "binding_generation": identity["binding_generation"],
            "host_generation": identity["host_generation"],
        }
        return DsdPcmSessionPrepared(
            plan=plan_value,
            execution_id=expected["execution_id"],
            stable_device_id=expected["stable_device_id"],
            binding_locator=expected["device"],
            host_generation=expected["host_generation"],
            runtime_identity=dict(identity),
            evidence_refs=plan_value.evidence_refs,
            handle=expected,
        )

    session = OutputSessionService(
        OutputPlanner(),
        request_provider=lambda _path: OutputRequest.dsd_to_pcm(
            plan, "dev:installed-lab", "profile:installed-lab"
        ),
        async_submit=None,
        dsd_pcm_prepare=prepare,
        dsd_pcm_commit=lambda prepared: port.commit_dsd_pcm(prepared.handle),
        dsd_pcm_abort=lambda prepared, _reason: port.abort_dsd_pcm(prepared.handle),
        dsd_pcm_stop=lambda prepared, _reason: port.stop_dsd_pcm(prepared.handle),
        dsd_pcm_plan_still_current=lambda _plan: True,
        truth_recorder=truth,
    )
    holder["session"] = session

    class _NoPcmVolume:
        def synchronize(self):
            raise AssertionError("DSD→PCM must not synchronize PCM volume")

        def restore(self, _volume, _muted):
            return None

    playback = PlaybackService(port, volume_port=_NoPcmVolume(), output_tx=session)
    accepted: list[Path] = []
    started = time.monotonic()
    try:
        port.activate()
        playback.load_and_play(source, on_accepted=accepted.append)
        if accepted != [source]:
            raise SystemExit("PLAYBACK_NOT_ACCEPTED")
        if session.state is not OutputSessionState.RUNNING:
            raise SystemExit(f"SESSION_NOT_RUNNING: {session.state}")
        execution = session.active_execution_id
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline:
            port.dispatch_pending()
            if session._dsd_pcm_terminal_execution == execution:
                break
            time.sleep(0.02)
        if session._dsd_pcm_terminal_execution != execution:
            raise SystemExit("EOS_NOT_OBSERVED")
        playback.stop()
        if session.state is not OutputSessionState.IDLE:
            raise SystemExit(f"SESSION_NOT_IDLE: {session.state}")
        if port.dsd_pcm_active:
            raise SystemExit("HOST_RESOURCE_NOT_RELEASED")
        states = [event.state for event in truth.output_family_events]
        if OutputFamilyState.RUNNING not in states:
            raise SystemExit("TRUTH_RUNNING_NOT_OBSERVED")
        if OutputFamilyState.RELEASED not in states:
            raise SystemExit("TRUTH_RELEASED_NOT_OBSERVED")
    finally:
        supervisor.close()
    result = {
        "schema_version": 1,
        "status": "PASS",
        "skipped": False,
        "package": str(package_path),
        "source": str(source),
        "plan_id": plan.plan_id,
        "execution_id": execution,
        "target_rate_hz": plan.target_rate_hz,
        "sink_factory": "fakesink",
        "truth_states": [str(state) for state in states],
        "elapsed_s": round(time.monotonic() - started, 3),
        "cleanup_confirmed": True,
    }
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.json is not None:
        args.json.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
