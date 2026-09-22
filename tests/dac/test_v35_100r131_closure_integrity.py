"""DAC-V35-100R1.3.1 — closure integrity corrective gates.

Phase prefixes:

- ``ci131_01_*`` device identity vs output path separation
- ``ci131_02_*`` qualification single-flight under follower timeout
- ``ci131_03_*`` GLib context-command commit authority
- ``ci131_04_*`` GStreamer close first-error-wins + best-effort
- ``ci131_05_*`` tuple-scoped capability presentation
- ``ci131_06_*`` one user intent -> one playback request
- ``ci131_07_*`` authorized container-adaptation relation
"""

from __future__ import annotations

from pathlib import Path

from michi.application.audio_output_selection_coordinator import (
    AudioOutputSelectionCoordinator,
)
from tests.dac.test_v35_productive_direct_composition import (
    _close_graph,
    _direct_graph,
)

DEVICE_ID = "usb:2622:0105:DX5ABC123"


def _coordinator(graph) -> AudioOutputSelectionCoordinator:
    return AudioOutputSelectionCoordinator(
        profiles=graph.audio_output_profiles,
        devices=graph.audio_device_registry,
        output_session=graph.output_session,
        engines=graph.audio_engine_service,
    )


def _graph(tmp_path: Path, probe_calls: list[dict] | None = None):
    calls = probe_calls if probe_calls is not None else []

    class _ForbiddenProbe:
        def probe_exact(self, **kwargs):
            calls.append(kwargs)
            raise AssertionError("Shared output must never run an exact ALSA probe")

    return _direct_graph(
        tmp_path,
        qualification_adapter=_ForbiddenProbe(),
        preseed_qualification=False,
    )


# ── Phase 1 — device identity vs output path ───────────────────────────────


def test_ci131_01_a_shared_policy_preserves_selected_dac_identity(
    qapp, tmp_path: Path
) -> None:
    graph, _bindings = _graph(tmp_path)
    coordinator = _coordinator(graph)
    try:
        coordinator.select_shared_output()
        coordinator.select_device(DEVICE_ID)
        coordinator.select_path_mode("strict")
        coordinator.select_path_mode("shared")

        selection = graph.audio_output_profiles.load_selection()
        assert selection.selected_device_id == DEVICE_ID
        assert selection.selected_profile_id is None
        assert graph.output_session.mode == "shared"
        assert graph.output_session.selection_state().selected_device_id == DEVICE_ID
    finally:
        _close_graph(graph)


def test_ci131_01_b_shared_then_strict_keeps_the_same_dac(qapp, tmp_path: Path) -> None:
    graph, _bindings = _graph(tmp_path)
    coordinator = _coordinator(graph)
    try:
        coordinator.select_device(DEVICE_ID)
        coordinator.select_path_mode("compatible")
        coordinator.select_path_mode("shared")
        coordinator.select_path_mode("strict")

        selection = graph.audio_output_profiles.load_selection()
        assert selection.selected_device_id == DEVICE_ID
        profile = next(
            item
            for item in graph.audio_output_profiles.load_profiles()
            if item.profile_id == selection.selected_profile_id
        )
        assert profile.stable_device_id == DEVICE_ID
    finally:
        _close_graph(graph)


def test_ci131_01_c_restart_restores_remembered_dac_and_shared_policy(
    qapp, tmp_path: Path
) -> None:
    graph, _bindings = _graph(tmp_path)
    coordinator = _coordinator(graph)
    try:
        coordinator.select_device(DEVICE_ID)
        coordinator.select_path_mode("strict")
        coordinator.select_path_mode("shared")

        # Fresh coordinator over the same persisted authorities == restart.
        restarted = _coordinator(graph)
        selection = graph.audio_output_profiles.load_selection()
        assert selection.selected_device_id == DEVICE_ID
        assert selection.selected_profile_id is None

        restarted.select_path_mode("strict")
        after = graph.audio_output_profiles.load_selection()
        assert after.selected_device_id == DEVICE_ID
        assert after.selected_profile_id is not None
    finally:
        _close_graph(graph)


def test_ci131_01_d_clearing_the_device_is_an_explicit_intent(
    qapp, tmp_path: Path
) -> None:
    graph, _bindings = _graph(tmp_path)
    coordinator = _coordinator(graph)
    try:
        coordinator.select_device(DEVICE_ID)
        coordinator.select_path_mode("strict")

        coordinator.clear_device_selection()

        selection = graph.audio_output_profiles.load_selection()
        assert selection.selected_device_id is None
        assert selection.selected_profile_id is None
        assert graph.output_session.selection_state().selected_device_id is None
    finally:
        _close_graph(graph)


def test_ci131_01_e_shared_playback_still_bypasses_direct_and_probe(
    qapp, tmp_path: Path
) -> None:
    probe_calls: list[dict] = []
    graph, bindings = _graph(tmp_path, probe_calls)
    coordinator = _coordinator(graph)
    try:
        coordinator.select_device(DEVICE_ID)
        coordinator.select_path_mode("strict")
        coordinator.select_path_mode("shared")

        graph.playback.load_and_play(tmp_path / "shared-after-strict.flac")

        assert graph.output_session.mode == "shared"
        assert graph.output_session.plan is None
        assert graph.direct_output_executor.handle is None
        assert bindings.pipelines[-1].audio_sink is None
        assert probe_calls == []
    finally:
        _close_graph(graph)
