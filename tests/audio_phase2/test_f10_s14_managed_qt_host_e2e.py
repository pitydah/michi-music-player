"""AP2-F10 S14 — Managed PCM ↔ DSD→PCM on the Qt owner loop and real host.

The chain is the productive bootstrap graph:
PlaybackService → OutputSessionService → GStreamerHostedAudioPort →
GStreamerHostSupervisor.  The terminal sink is fakesink: laboratory evidence,
not a physical DAC certification.
"""

from __future__ import annotations

import importlib.util
import threading
from pathlib import Path

import pytest
from PySide6.QtCore import QTimer

from michi.application.output_session_service import HandoverState
from michi.domain.audio_output import OutputSessionState
from michi.infrastructure.qt_async_call import QtAsyncCallExecutor
from tests.audio_phase2.test_family_handover_product_e2e import _PREFIX
from tests.audio_phase2.test_managed_productive_flow import (
    FIXTURE,
    _build_graph,
    _close,
    _select_managed,
)
from tests.audio_phase2.test_preparation_async_qt import _pump_until

pytestmark = [
    pytest.mark.skipif(
        importlib.util.find_spec("gi") is None or _PREFIX is None,
        reason="GStreamer or Gate A michidop prefix unavailable",
    ),
    # Known blocker: PlaybackService performs the generic router load before the
    # managed commit, so the host managed execution is no longer addressable and
    # the predecessor release returns MANAGED_STOP_STALE. Keep the reproducer
    # strict so a future fix flips it to XPASS and forces this marker to be removed.
    pytest.mark.xfail(
        strict=True,
        reason=(
            "T03/T04 blocked: PlaybackService generic load bypasses the managed "
            "host execution; managed release returns MANAGED_STOP_STALE"
        ),
    ),
]


def _run(qapp, tmp_path, monkeypatch, *, first: str, second: str) -> None:
    from tests.audio_phase2.test_dsd_source_truth import build_dsf

    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    monkeypatch.setenv("GST_PLUGIN_PATH", str(_PREFIX))
    monkeypatch.setenv("MICHI_DOP_PLUGIN_PREFIX", str(_PREFIX))
    monkeypatch.setenv("MICHI_DSD_PCM_CONVERT", "1")
    dsd = tmp_path / "target.dsf"
    dsd.write_bytes(build_dsf(sample_count=352_800, payload=bytes([0x69]) * 705_600))
    executor = QtAsyncCallExecutor()
    graph, coordinator = _build_graph(tmp_path, output_preparation_executor=executor)
    _select_managed(coordinator)
    graph.set_processing_profile(None)
    session = graph.output_session
    playback = graph.playback
    accepted: list[Path] = []
    rejected: list[tuple[Path, str]] = []
    owner_threads: list[int] = []
    overlap = {"seen": False}

    sampler = QTimer()
    sampler.setInterval(1)
    sampler.timeout.connect(
        lambda: overlap.__setitem__(
            "seen",
            overlap["seen"] or (session.mode == "managed" and session.dsd_pcm_active),
        )
    )

    def on_accepted(path: Path) -> None:
        accepted.append(path)
        owner_threads.append(threading.get_ident())

    def on_rejected(path: Path, reason: str) -> None:
        rejected.append((path, reason))

    first_path = FIXTURE if first == "managed" else dsd
    second_path = dsd if second == "dsd_pcm" else FIXTURE
    try:
        playback.load_and_play(first_path, on_accepted=on_accepted)
        assert _pump_until(qapp, lambda: bool(accepted), 60.0)
        assert session.mode == first
        assert session.state is OutputSessionState.RUNNING
        predecessor_execution = session.active_execution_id
        predecessor_plan = session.transition_snapshot()["plan_id"]
        assert predecessor_execution and predecessor_plan

        sampler.start()
        playback.load_and_play(
            second_path, on_accepted=on_accepted, on_rejected=on_rejected
        )
        assert _pump_until(qapp, lambda: len(accepted) == 2, 60.0)
        sampler.stop()

        assert rejected == []
        assert len(set(owner_threads)) == 1
        assert owner_threads[0] == threading.get_ident()
        assert overlap["seen"] is False
        assert session.mode == second
        assert session.state is OutputSessionState.RUNNING
        assert session.dsd_pcm_active is (second == "dsd_pcm")
        assert session.handover_state is HandoverState.READY
        evidence = session.last_handover_release_evidence
        assert evidence is not None
        assert evidence["confirmed"] is True
        assert evidence["execution_id"] == predecessor_execution
        assert evidence["plan_id"] == predecessor_plan
        assert evidence["provenance"] == "SUPERVISED_HOST"
        assert evidence["target_family"] == second

        events = [
            (event.family, event.state)
            for event in graph.signal_truth.output_family_events
        ]
        assert (first, "running") in events
        assert (first, "released") in events
        assert (second, "running") in events

        playback.stop()
        assert _pump_until(qapp, lambda: session.state is OutputSessionState.IDLE, 30.0)
    finally:
        sampler.stop()
        _close(graph)


def test_t03_managed_to_dsd_pcm_on_qt_host(qapp, tmp_path, monkeypatch) -> None:
    _run(qapp, tmp_path, monkeypatch, first="managed", second="dsd_pcm")


def test_t04_dsd_pcm_to_managed_on_qt_host(qapp, tmp_path, monkeypatch) -> None:
    _run(qapp, tmp_path, monkeypatch, first="dsd_pcm", second="managed")
