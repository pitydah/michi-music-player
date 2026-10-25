"""AP2-F09 — PlaybackService -> OutputSession -> real host -> michidop."""

from __future__ import annotations

import importlib.util
import time
from pathlib import Path

import pytest

from michi.application.audio_output_planner import OutputPlanner
from michi.application.output_session_service import (
    DopSessionPrepared,
    OutputSessionService,
)
from michi.application.playback_service import PlaybackService
from michi.domain.audio_output import OutputSessionState
from michi.domain.dop import DopInterpretationState, DopPolicyDecision
from michi.infrastructure.audio_output.dop_runtime import DopOutputExecutor
from tests.audio_phase2.test_dop_resolver import _resolver
from tests.audio_phase2.test_dsd_source_truth import build_dsf

_HAS_GI = importlib.util.find_spec("gi") is not None


def _resolved_prefix():
    from michi.infrastructure.audio_output.dop_plugin import resolve_dop_prefix

    try:
        return resolve_dop_prefix()
    except RuntimeError:
        return None


_PREFIX = _resolved_prefix()
_PLUGIN = (
    _PREFIX / "libmichidop.so"
    if _PREFIX is not None
    else Path("/nonexistent/libmichidop.so")
)

pytestmark = pytest.mark.skipif(
    not _HAS_GI or not _PLUGIN.exists(),
    reason="installed Gate A/B michidop artifact is not available",
)


class _Volume:
    def synchronize(self):
        raise AssertionError("DoP must not synchronize PCM volume")

    def restore(self, volume, muted):
        return None


def test_playback_service_reaches_dop_playing_and_eos(tmp_path, monkeypatch) -> None:
    from michi.infrastructure.audio_engines.gstreamer_host_client import (
        GStreamerHostSupervisor,
    )
    from michi.infrastructure.audio_engines.gstreamer_host_port import (
        GStreamerHostedAudioPort,
    )

    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    monkeypatch.setenv("GST_PLUGIN_PATH", str(_PREFIX))
    monkeypatch.setenv("MICHI_DOP_PLUGIN_PREFIX", str(_PREFIX))
    source = tmp_path / "doop.dsf"
    source.write_bytes(
        build_dsf(sample_count=352_800 // 4, payload=bytes([0x69]) * 176_400)
    )
    resolver = _resolver(
        DopPolicyDecision(
            explicit_requested=True,
            auto_allowed=False,
            minimum_interpretation_state=DopInterpretationState.USER_CONFIRMED,
        )
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
    session_holder: dict[str, OutputSessionService] = {}

    def prepare(plan_value, path, _instance):
        prepared = DopOutputExecutor(port, sink_factory="fakesink").prepare(
            plan_value, path
        )
        port.add_dop_eos_listener(session_holder["s"].notify_dop_eos)
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
        request_provider=resolver,
        async_submit=None,
        dop_prepare=prepare,
        dop_commit=commit,
        dop_abort=abort,
        dop_stop=stop,
        dop_plan_still_current=lambda _plan: True,
    )
    session_holder["s"] = session
    playback = PlaybackService(port, volume_port=_Volume(), output_tx=session)
    accepted: list[Path] = []
    try:
        port.activate()
        playback.load_and_play(source, on_accepted=accepted.append)
        assert accepted == [source]
        assert session.mode == "dop"
        assert session.state is OutputSessionState.RUNNING
        assert session.dop_active is True
        execution_id = session.active_execution_id
        assert execution_id
        deadline = time.monotonic() + 8.0
        while time.monotonic() < deadline:
            port.dispatch_pending()
            if session._dop_terminal_execution == execution_id:
                break
            time.sleep(0.02)
        assert session._dop_terminal_execution == execution_id
        playback.stop()
        assert session.state is OutputSessionState.IDLE
        accepted.clear()
        playback.load_and_play(source, on_accepted=accepted.append)
        assert accepted == [source]
        assert session.mode == "dop"
        execution_id = session.active_execution_id
        assert execution_id
        deadline = time.monotonic() + 8.0
        while time.monotonic() < deadline:
            port.dispatch_pending()
            if session._dop_terminal_execution == execution_id:
                break
            time.sleep(0.02)
        assert session._dop_terminal_execution == execution_id
        playback.stop()
        assert session.state is OutputSessionState.IDLE
    finally:
        supervisor.close()
