"""AP2-F10 S17 — physical Managed ↔ DSD→PCM handover through a real DAC.

These tests are OPT-IN (``MICHI_PHYSICAL_DAC_TESTS=1``) and require the
SMSL/KINMAX USB DACs. They use ``plughw`` because the hardware exposes
S32_LE/S16_LE but not F32LE at the ``hw`` layer; the DSD→PCM terminal
format remains F32LE and ALSA performs the final container conversion.
This is physical ALSA runtime evidence, never an analog/bit-perfect claim.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import time
from dataclasses import replace
from pathlib import Path

import pytest

from tests.audio_phase2.test_dsd_source_truth import build_dsf
from tests.audio_phase2.test_managed_productive_flow import (
    DEVICE_ID,
    FIXTURE,
    _build_graph,
    _close,
    _select_managed,
)

pytestmark = [
    pytest.mark.skipif(
        importlib.util.find_spec("gi") is None
        or shutil.which("gst-inspect-1.0") is None,
        reason="PyGObject/GStreamer not available",
    ),
    pytest.mark.skipif(
        os.environ.get("MICHI_PHYSICAL_DAC_TESTS", "").strip() != "1",
        reason="set MICHI_PHYSICAL_DAC_TESTS=1 to run physical DAC tests",
    ),
    pytest.mark.skipif(
        shutil.which("aplay") is None
        or "SMSL USB AUDIO"
        not in subprocess.run(
            ["aplay", "-l"], capture_output=True, text=True, check=False
        ).stdout,
        reason="SMSL USB DAC not present",
    ),
]

LOCATOR = "plughw:CARD=AUDIO,DEV=0"


def _pump_until(graph, predicate, *, timeout: float = 30.0) -> bool:
    port = graph.gstreamer_engine_provider.current_port
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        port.dispatch_pending()
        if predicate():
            return True
        time.sleep(0.02)
    port.dispatch_pending()
    return bool(predicate())


def _force_physical_locator(graph) -> None:
    from michi.domain.audio_device import BindingKind

    registry = graph.audio_device_registry
    original = registry.bindings_for

    def bindings_for(stable_device_id, kind=None, *args, **kwargs):
        bindings = original(stable_device_id, kind, *args, **kwargs)
        if kind not in (None, BindingKind.ALSA_PCM):
            return bindings
        return tuple(
            replace(binding, locator=LOCATOR)
            if binding.kind is BindingKind.ALSA_PCM
            else binding
            for binding in bindings
        )

    registry.bindings_for = bindings_for


def _settings(tmp_path):
    from michi.application.settings_service import SettingsService
    from michi.infrastructure.sqlite_settings import SQLiteSettingsRepository

    settings = SettingsService(
        SQLiteSettingsRepository.open_for_startup(tmp_path / "michi.db")
    )
    settings.set_dsd_pcm_conversion_consent(True)
    return settings


def _build(tmp_path, monkeypatch):
    monkeypatch.delenv("MICHI_GST_LAB_SINK", raising=False)
    graph, coordinator = _build_graph(
        tmp_path,
        settings_service=_settings(tmp_path),
        extra_capabilities=(
            (88_200, "F32LE", 2, 32),
            (176_400, "F32LE", 2, 32),
        ),
    )
    _force_physical_locator(graph)
    return graph, coordinator


def test_t03_physical_managed_to_dsd_pcm(tmp_path, monkeypatch) -> None:
    from michi.application.output_session_service import HandoverState
    from michi.domain.playback import PlaybackStatus

    graph, coordinator = _build(tmp_path, monkeypatch)
    source = tmp_path / "target.dsf"
    source.write_bytes(build_dsf(sample_count=2_822_400))
    try:
        _select_managed(coordinator)
        accepted: list[Path] = []
        graph.playback.load_and_play(FIXTURE, on_accepted=accepted.append)
        assert _pump_until(
            graph,
            lambda: (
                accepted == [FIXTURE]
                and graph.playback.state.status is PlaybackStatus.PLAYING
                and graph.output_session.mode == "managed"
            ),
        ), (accepted, graph.playback.state.error_message, graph.output_session.state)
        predecessor = graph.output_session.transition_snapshot()
        assert predecessor["plan_id"] and predecessor["execution_id"]

        coordinator.select_path_mode("compatible")
        coordinator.select_device_for_playback(DEVICE_ID)
        coordinator.select_path_mode("compatible")
        graph.playback.load_and_play(source, on_accepted=accepted.append)
        assert _pump_until(
            graph,
            lambda: (
                len(accepted) == 2
                and graph.output_session.mode == "dsd_pcm"
                and graph.output_session.state.value == "running"
                and graph.playback.state.status is PlaybackStatus.PLAYING
            ),
        ), accepted
        assert graph.output_session.handover_state is HandoverState.READY
        evidence = graph.output_session.last_handover_release_evidence
        assert evidence is not None
        assert evidence["confirmed"] is True
        assert evidence["terminal_state"] == "RELEASED"
        assert evidence["provenance"] == "SUPERVISED_HOST"
        assert evidence["plan_id"] == predecessor["plan_id"]
        assert evidence["execution_id"] == predecessor["execution_id"]
        assert evidence["device"] == LOCATOR
        assert evidence["target_family"] == "dsd_pcm"

        graph.playback.stop()
        assert _pump_until(graph, lambda: graph.output_session.state.value == "idle")
    finally:
        _close(graph)


def test_t04_physical_dsd_pcm_to_managed(tmp_path, monkeypatch) -> None:
    from michi.application.output_session_service import HandoverState
    from michi.domain.playback import PlaybackStatus

    graph, coordinator = _build(tmp_path, monkeypatch)
    source = tmp_path / "target.dsf"
    source.write_bytes(build_dsf(sample_count=2_822_400))
    try:
        coordinator.select_device(DEVICE_ID)
        coordinator.select_path_mode("compatible")
        accepted: list[Path] = []
        graph.playback.load_and_play(source, on_accepted=accepted.append)
        assert _pump_until(
            graph,
            lambda: (
                accepted == [source]
                and graph.playback.state.status is PlaybackStatus.PLAYING
                and graph.output_session.mode == "dsd_pcm"
            ),
        ), (accepted, graph.playback.state.error_message, graph.output_session.state)
        predecessor = graph.output_session.transition_snapshot()
        assert predecessor["plan_id"] and predecessor["execution_id"]

        _select_managed(coordinator)
        graph.playback.load_and_play(FIXTURE, on_accepted=accepted.append)
        assert _pump_until(
            graph,
            lambda: (
                len(accepted) == 2
                and graph.output_session.mode == "managed"
                and graph.output_session.state.value == "running"
                and graph.playback.state.status is PlaybackStatus.PLAYING
            ),
        ), accepted
        assert graph.output_session.handover_state is HandoverState.READY
        evidence = graph.output_session.last_handover_release_evidence
        assert evidence is not None
        assert evidence["confirmed"] is True
        assert evidence["terminal_state"] == "RELEASED"
        assert evidence["provenance"] == "SUPERVISED_HOST"
        assert evidence["plan_id"] == predecessor["plan_id"]
        assert evidence["execution_id"] == predecessor["execution_id"]
        assert evidence["device"] == LOCATOR
        assert evidence["target_family"] == "managed"

        graph.playback.stop()
        assert _pump_until(graph, lambda: graph.output_session.state.value == "idle")
    finally:
        _close(graph)
