"""AP2-F10 S13 — Qt owner loop + supervised GStreamer host end to end.

The production chain is PlaybackService → OutputSessionService →
GStreamerHostedAudioPort → GStreamerHostSupervisor, with the real
QtAsyncCallExecutor delivering every completion back to the Qt owner thread.
The terminal sink is fakesink: this is laboratory evidence, not DAC
certification.
"""

from __future__ import annotations

import importlib.util
import threading
from pathlib import Path

import pytest
from PySide6.QtCore import QTimer

from michi.application.audio_family_transition import TransitionPhase
from michi.application.output_session_service import HandoverState
from michi.domain.audio_output import OutputSessionState
from michi.domain.signal_truth import OutputFamilyState
from michi.infrastructure.qt_async_call import QtAsyncCallExecutor
from tests.audio_phase2.test_dsd_source_truth import build_dsf
from tests.audio_phase2.test_family_handover_product_e2e import _PREFIX, _build
from tests.audio_phase2.test_preparation_async_qt import _pump_until

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("gi") is None or _PREFIX is None,
    reason="GStreamer or Gate A michidop prefix unavailable",
)


def _run(qapp, tmp_path, monkeypatch, *, first: str, second: str) -> None:
    source_dsd = tmp_path / "target.dsf"
    source_dop = tmp_path / "dop.dsf"
    executor = QtAsyncCallExecutor()
    supervisor, port, session, playback, truth = _build(
        tmp_path, monkeypatch, dsd_source=source_dsd, async_submit=executor.submit
    )
    source_dop.write_bytes(source_dsd.read_bytes())
    first_family = "dsd_pcm" if first == "dsd_pcm.dsf" else "dop"
    second_family = "dop" if first_family == "dsd_pcm" else "dsd_pcm"
    first_path = source_dsd if first_family == "dsd_pcm" else source_dop
    second_path = source_dop if second_family == "dop" else source_dsd
    accepted: list[Path] = []
    rejected: list[tuple[Path, str]] = []
    owner_threads: list[int] = []
    overlap = {"seen": False}

    sampler = QTimer()
    sampler.setInterval(1)
    sampler.timeout.connect(
        lambda: overlap.__setitem__(
            "seen", overlap["seen"] or (port.dsd_pcm_active and port.dop_active)
        )
    )
    ticks = {"n": 0}
    clock = QTimer()
    clock.setInterval(1)
    clock.timeout.connect(lambda: ticks.__setitem__("n", ticks["n"] + 1))

    def on_accepted(path: Path) -> None:
        accepted.append(path)
        owner_threads.append(threading.get_ident())

    def on_rejected(path: Path, reason: str) -> None:
        rejected.append((path, reason))

    try:
        port.activate()
        clock.start()
        playback.load_and_play(first_path, on_accepted=on_accepted)
        assert _pump_until(qapp, lambda: bool(accepted), 60.0)
        assert session.mode == first_family
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
        clock.stop()

        assert rejected == []
        assert len(accepted) == 2
        assert len(set(owner_threads)) == 1
        assert owner_threads[0] == threading.get_ident()
        assert ticks["n"] > 0
        assert overlap["seen"] is False
        assert session.mode == second_family
        assert session.state is OutputSessionState.RUNNING
        assert getattr(port, f"{second_family}_active") is True
        assert getattr(port, f"{first_family}_active") is False
        assert playback.family_transition_receipts
        receipt = playback.family_transition_receipts[-1]
        assert receipt.phase is TransitionPhase.TARGET_STARTED
        assert receipt.predecessor_released is True
        assert session.handover_state is HandoverState.READY
        evidence = session.last_handover_release_evidence
        assert evidence is not None
        assert evidence["confirmed"] is True
        assert evidence["execution_id"] == predecessor_execution
        assert evidence["plan_id"] == predecessor_plan
        assert evidence["provenance"] == "SUPERVISED_HOST"

        events = [(event.family, event.state) for event in truth.output_family_events]
        assert (first_family, OutputFamilyState.RUNNING) in events
        assert (first_family, OutputFamilyState.RELEASED) in events
        assert (second_family, OutputFamilyState.RUNNING) in events

        playback.stop()
        assert _pump_until(qapp, lambda: session.state is OutputSessionState.IDLE, 30.0)
        assert port.dsd_pcm_active is False
        assert port.dop_active is False
    finally:
        sampler.stop()
        clock.stop()
        supervisor.close()


def test_e2e_a_qt_host_dsd_pcm_to_dop(qapp, tmp_path, monkeypatch) -> None:
    _run(qapp, tmp_path, monkeypatch, first="dsd_pcm.dsf", second="dop.dsf")


def test_e2e_b_qt_host_dop_to_dsd_pcm(qapp, tmp_path, monkeypatch) -> None:
    _run(qapp, tmp_path, monkeypatch, first="dop.dsf", second="target.dsf")


def _run_native(qapp, tmp_path, monkeypatch, *, first: str, second: str) -> None:
    source_dsd = tmp_path / "target.dsf"
    source_native = tmp_path / "native.dsf"
    executor = QtAsyncCallExecutor()
    supervisor, port, session, playback, truth = _build(
        tmp_path, monkeypatch, dsd_source=source_dsd, async_submit=executor.submit
    )
    source_native.write_bytes(build_dsf(sample_count=2_822_400))
    paths = {"native_dsd": source_native, "dsd_pcm": source_dsd}
    accepted: list[Path] = []
    rejected: list[tuple[Path, str]] = []
    owner_threads: list[int] = []
    overlap = {"seen": False}

    sampler = QTimer()
    sampler.setInterval(1)
    sampler.timeout.connect(
        lambda: overlap.__setitem__(
            "seen",
            overlap["seen"] or (port.native_dsd_active and port.dsd_pcm_active),
        )
    )
    ticks = {"n": 0}
    clock = QTimer()
    clock.setInterval(1)
    clock.timeout.connect(lambda: ticks.__setitem__("n", ticks["n"] + 1))

    def on_accepted(path: Path) -> None:
        accepted.append(path)
        owner_threads.append(threading.get_ident())

    def on_rejected(path: Path, reason: str) -> None:
        rejected.append((path, reason))

    try:
        port.activate()
        clock.start()
        playback.load_and_play(paths[first], on_accepted=on_accepted)
        assert _pump_until(qapp, lambda: bool(accepted), 60.0)
        assert session.mode == first
        assert session.state is OutputSessionState.RUNNING
        predecessor_execution = session.active_execution_id
        predecessor_plan = session.transition_snapshot()["plan_id"]
        assert predecessor_execution and predecessor_plan

        sampler.start()
        playback.load_and_play(
            paths[second], on_accepted=on_accepted, on_rejected=on_rejected
        )
        assert _pump_until(qapp, lambda: len(accepted) == 2, 60.0)
        sampler.stop()
        clock.stop()

        assert rejected == []
        assert len(owner_threads) == 2
        assert len(set(owner_threads)) == 1
        assert owner_threads[0] == threading.get_ident()
        assert ticks["n"] > 0
        assert overlap["seen"] is False
        assert session.mode == second
        assert session.state is OutputSessionState.RUNNING
        assert getattr(port, f"{first}_active") is False
        assert getattr(port, f"{second}_active") is True
        receipt = playback.family_transition_receipts[-1]
        assert receipt.phase is TransitionPhase.TARGET_STARTED
        assert receipt.predecessor_released is True
        evidence = session.last_handover_release_evidence
        assert evidence is not None
        assert evidence["confirmed"] is True
        assert evidence["execution_id"] == predecessor_execution
        assert evidence["plan_id"] == predecessor_plan
        assert evidence["provenance"] == "SUPERVISED_HOST"

        events = [(event.family, event.state) for event in truth.output_family_events]
        assert (first, OutputFamilyState.RUNNING) in events
        assert (first, OutputFamilyState.RELEASED) in events
        assert (second, OutputFamilyState.RUNNING) in events

        playback.stop()
        assert _pump_until(qapp, lambda: session.state is OutputSessionState.IDLE, 30.0)
        assert port.native_dsd_active is False
        assert port.dsd_pcm_active is False
    finally:
        sampler.stop()
        clock.stop()
        supervisor.close()


def test_e2e_t05_qt_host_native_to_dsd_pcm(qapp, tmp_path, monkeypatch) -> None:
    _run_native(qapp, tmp_path, monkeypatch, first="native_dsd", second="dsd_pcm")


def test_e2e_t06_qt_host_dsd_pcm_to_native(qapp, tmp_path, monkeypatch) -> None:
    _run_native(qapp, tmp_path, monkeypatch, first="dsd_pcm", second="native_dsd")
