#!/usr/bin/env python3
"""Certify the INSTALLED Michi DoP package end to end.

This script is deliberately independent of the checkout test helpers: it is
executed from outside the repository with only the installed wheel importable.
It fails (never skips) when the installed plugin, manifest, host vertical or
playback confirmation are absent.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.util
import json
import os
import struct
import sys
import time
from pathlib import Path

_DSF_BLOCK = 4096
_DSF_FIXED_HEADER = 28 + 52 + 12


def _dsf_payload(channels: int, sample_count: int, block_size: int) -> bytes:
    frames = max(1, (sample_count + 7) // 8)
    return bytes((0x69 + (index % 17)) & 0xFF for index in range(frames * channels)) * (
        block_size // max(1, frames * channels) or 1
    )


def build_dsf(
    *,
    rate: int = 2_822_400,
    channels: int = 2,
    sample_count: int = 88_200,
    block_size: int = _DSF_BLOCK,
    payload: bytes | None = None,
) -> bytes:
    if payload is None:
        payload = _dsf_payload(channels, sample_count, block_size)
    file_size = _DSF_FIXED_HEADER + len(payload)
    data_chunk = 12 + len(payload)
    header = (
        b"DSD "
        + struct.pack("<Q", 28)
        + struct.pack("<Q", file_size)
        + struct.pack("<Q", 0)
        + b"fmt "
        + struct.pack("<Q", 52)
        + struct.pack("<I", 1)
        + struct.pack("<I", 0)
        + struct.pack("<I", 2)
        + struct.pack("<I", channels)
        + struct.pack("<I", rate)
        + struct.pack("<I", 8)
        + struct.pack("<Q", sample_count)
        + struct.pack("<I", block_size)
        + struct.pack("<I", 0)
        + b"data"
        + struct.pack("<Q", data_chunk)
    )
    return header + payload


def _plan(plugin_prefix: Path):
    from michi.application.dop_planner import DopPlannerV3
    from michi.domain.dop import (
        DopCarrierLayout,
        DopCarrierQualification,
        DopCarrierSupport,
        DopDeviceInterpretationEvidence,
        DopInterpretationState,
        DopPolicyDecision,
    )
    from michi.domain.dsd_signal import (
        DsdBitOrder,
        DsdOrganization,
        DsdPacking,
        DsdSignalFormat,
    )

    device = "installed-wheel:dop"
    locator = "hw:0,0"
    environment = "installed-wheel:env:1"
    revision = "installed-wheel:rev:1"
    source = DsdSignalFormat(
        bit_rate_hz=2_822_400,
        channels=2,
        packing=DsdPacking.DSD_U8,
        bit_order=DsdBitOrder.MSBF,
        organization=DsdOrganization.PLANAR,
        layout=("FL", "FR"),
    )
    carrier = DopCarrierQualification(
        stable_device_id=device,
        carrier_layout_id=DopCarrierLayout.S32_LE_LSB24.value,
        carrier_rate_hz=176_400,
        alsa_format="S32_LE",
        channels=2,
        support=DopCarrierSupport.QUALIFIED,
        environment_fingerprint=environment,
        evidence_refs=("installed-wheel:carrier",),
        binding_generation=1,
        binding_locator=locator,
        significant_transport_bits=24,
        provenance="installed-wheel:qualification",
    )
    interpretation = DopDeviceInterpretationEvidence(
        stable_device_id=device,
        source_dsd_multiplier=64,
        state=DopInterpretationState.USER_CONFIRMED,
        source="installed-wheel:declared",
        device_revision=revision,
        evidence_refs=("installed-wheel:interpretation",),
    )
    return DopPlannerV3().plan(
        stable_device_id=device,
        binding_locator=locator,
        binding_generation=1,
        execution_id=f"exec:installed-wheel:{os.getpid()}:{time.time_ns()}",
        host_generation=1,
        environment_fingerprint=environment,
        source=source,
        carrier_qualifications=(carrier,),
        interpretation=(interpretation,),
        policy=DopPolicyDecision(
            explicit_requested=True,
            auto_allowed=False,
            minimum_interpretation_state=DopInterpretationState.USER_CONFIRMED,
        ),
        current_device_revision=revision,
    )


class _Volume:
    def synchronize(self):
        raise AssertionError("DoP must not synchronize PCM volume")

    def restore(self, volume, muted):
        return None


def run() -> dict:
    import michi
    from michi.application.audio_output_planner import OutputPlanner
    from michi.application.output_session_service import (
        DopSessionPrepared,
        OutputRequest,
        OutputSessionService,
    )
    from michi.application.playback_service import PlaybackService
    from michi.domain.audio_output import OutputSessionState
    from michi.infrastructure.audio_engines.gstreamer_host_client import (
        GStreamerHostSupervisor,
    )
    from michi.infrastructure.audio_engines.gstreamer_host_port import (
        GStreamerHostedAudioPort,
    )
    from michi.infrastructure.audio_output.dop_plugin import (
        resolve_dop_manifest_path,
        resolve_dop_plugin_path,
    )
    from michi.infrastructure.audio_output.dop_runtime import DopOutputExecutor

    checks: list[str] = []
    package_file = Path(michi.__file__).resolve()
    checks.append(f"package={package_file}")
    if "site-packages" not in package_file.parts:
        raise AssertionError(f"michi imported outside site-packages: {package_file}")
    if package_file.is_relative_to(Path.cwd().resolve()):
        raise AssertionError(
            f"michi imported from the current checkout: {package_file}"
        )

    plugin = resolve_dop_plugin_path()
    manifest_path = resolve_dop_manifest_path()
    if not plugin.is_file() or not manifest_path.is_file():
        raise AssertionError(f"installed plugin incomplete: {plugin}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    digest = hashlib.sha256(plugin.read_bytes()).hexdigest()
    if manifest.get("name") != "michidop":
        raise AssertionError(f"manifest name is not michidop: {manifest!r}")
    expected_digest = manifest.get("sha256") or manifest.get("binary_sha256")
    if expected_digest != digest:
        raise AssertionError(
            f"manifest digest mismatch: declared={expected_digest} actual={digest}"
        )
    checks.append(f"plugin={plugin}")
    checks.append(f"plugin_sha256={digest}")
    checks.append(f"plugin_prefix={plugin.parent}")

    if importlib.util.find_spec("gi") is None:
        raise AssertionError("PyGObject is not installed in the wheel environment")

    plan = _plan(plugin.parent)
    source = (
        Path(os.environ.get("MICHI_DOP_E2E_SOURCE", ""))
        if os.environ.get("MICHI_DOP_E2E_SOURCE")
        else None
    )
    work = Path(os.environ.get("MICHI_DOP_E2E_WORKDIR", "/tmp/michi-dop-installed-e2e"))
    work.mkdir(parents=True, exist_ok=True)
    if source is None:
        source = work / "installed-wheel.dsf"
        source.write_bytes(
            build_dsf(sample_count=88_200, payload=bytes([0x69]) * 176_400)
        )

    os.environ["MICHI_GST_LAB_SINK"] = "fakesink"
    os.environ["GST_PLUGIN_PATH"] = str(plugin.parent)
    os.environ["MICHI_DOP_PLUGIN_PREFIX"] = str(plugin.parent)
    os.environ.pop("MICHI_DOP_PREFIX", None)

    request = OutputRequest(
        facts=None,
        selected_device_id=plan.stable_device_id,
        selected_profile_id="installed-wheel:profile",
        dop_plan=plan,
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
    holder: dict[str, OutputSessionService] = {}

    def prepare(plan_value, path, _instance):
        prepared = DopOutputExecutor(port, sink_factory="fakesink").prepare(
            plan_value, path
        )
        port.add_dop_eos_listener(holder["session"].notify_dop_eos)
        return DopSessionPrepared(
            plan=plan_value,
            execution_id=plan_value.execution_id,
            stable_device_id=plan_value.stable_device_id,
            runtime_identity=dict(prepared.identity),
            evidence_refs=(),
            handle=prepared,
        )

    def commit(prepared):
        DopOutputExecutor(port, sink_factory="fakesink").commit(prepared.handle)

    def stop(prepared, reason):
        return DopOutputExecutor(port, sink_factory="fakesink").stop(
            prepared.handle, reason
        )

    def abort(prepared, reason):
        return DopOutputExecutor(port, sink_factory="fakesink").abort(
            prepared.handle, reason
        )

    session = OutputSessionService(
        OutputPlanner(),
        request_provider=lambda _path: request,
        async_submit=None,
        dop_prepare=prepare,
        dop_commit=commit,
        dop_abort=abort,
        dop_stop=stop,
        dop_plan_still_current=lambda _plan: True,
    )
    holder["session"] = session
    playback = PlaybackService(port, volume_port=_Volume(), output_tx=session)
    accepted: list[Path] = []
    try:
        port.activate()
        playback.load_and_play(source, on_accepted=accepted.append)
        if accepted != [source]:
            raise AssertionError(
                f"PlaybackService did not accept the source: {accepted}"
            )
        if session.mode != "dop":
            raise AssertionError(f"session family is {session.mode}, expected dop")
        if session.state is not OutputSessionState.RUNNING:
            raise AssertionError(f"session state is {session.state}, expected RUNNING")
        if not session.dop_active:
            raise AssertionError("DoP session is not active")
        execution_id = session.active_execution_id
        if not execution_id:
            raise AssertionError("DoP session has no execution identity")
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline:
            port.dispatch_pending()
            if session._dop_terminal_execution == execution_id:
                break
            time.sleep(0.02)
        if session._dop_terminal_execution != execution_id:
            raise AssertionError("host DoP EOS was never observed")
        checks.append(f"execution={execution_id}")
        checks.append("state=RUNNING")
        checks.append("eos=observed")
        playback.stop()
        if session.state is not OutputSessionState.IDLE:
            raise AssertionError(f"session did not release: {session.state}")
        checks.append("release=IDLE")
    finally:
        with contextlib.suppress(Exception):
            supervisor.close()
    return {
        "status": "PASS",
        "skipped": False,
        "package_file": str(package_file),
        "plugin": str(plugin),
        "plugin_sha256": digest,
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-output", type=Path, default=None)
    args = parser.parse_args()
    try:
        result = run()
    except Exception as exc:  # noqa: BLE001 - certification boundary
        result = {
            "status": "FAIL",
            "skipped": False,
            "error": f"{type(exc).__name__}: {exc}",
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        if args.json_output is not None:
            args.json_output.write_text(
                json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
            )
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.json_output is not None:
        args.json_output.write_text(
            json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
