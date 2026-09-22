"""DAC-V35-100R1.3 — playback compatibility, output-mode separation, lifecycle.

Phase gates are prefixed with the R1.3 phase they seal:

- ``pc13_02_*`` Shared playback baseline (explicit Shared never plans Direct)
- ``pc13_03_*`` device identity vs output-path policy separation
- ``pc13_04_*`` bounded candidate carrier resolution
- ``pc13_05_*`` compatible Direct (container-width adaptation only)
- ``pc13_06_*`` output failure presentation and recovery intents
- ``pc13_07_*`` native lifecycle hardening (command fence, close atomicity)
"""

from __future__ import annotations

from pathlib import Path

from michi.application.audio_output_selection_coordinator import (
    AudioOutputSelectionCoordinator,
)
from michi.domain.audio_output import OutputPathPreference
from tests.dac.test_v35_productive_direct_composition import (
    _close_graph,
    _direct_graph,
)


def _coordinator(graph) -> AudioOutputSelectionCoordinator:
    return AudioOutputSelectionCoordinator(
        profiles=graph.audio_output_profiles,
        devices=graph.audio_device_registry,
        output_session=graph.output_session,
        engines=graph.audio_engine_service,
    )


def _shared_graph(tmp_path: Path, probe_calls: list[dict]):
    """Graph whose qualification adapter refuses to be called."""

    class _ForbiddenProbe:
        def probe_exact(self, **kwargs):
            probe_calls.append(kwargs)
            raise AssertionError("Shared output must never run an exact ALSA probe")

    return _direct_graph(
        tmp_path,
        qualification_adapter=_ForbiddenProbe(),
        preseed_qualification=False,
    )


# ── Phase 2 — Shared playback ──────────────────────────────────────────────


def test_pc13_02_01_shared_selection_persists_without_direct_profile(
    qapp, tmp_path: Path
) -> None:
    probe_calls: list[dict] = []
    graph, _bindings = _shared_graph(tmp_path, probe_calls)
    coordinator = _coordinator(graph)
    try:
        coordinator.select_shared_output()

        selection = graph.audio_output_profiles.load_selection()
        assert selection.selected_profile_id is None
        assert selection.selected_device_id is None
        session_state = graph.output_session.selection_state()
        assert session_state.selected_device_id is None
        assert session_state.selected_profile_id is None
        assert graph.output_session.mode == "shared"
        assert probe_calls == []
    finally:
        _close_graph(graph)


def test_pc13_02_02_shared_playback_bypasses_direct_planner_and_probe(
    qapp, tmp_path: Path
) -> None:
    probe_calls: list[dict] = []
    graph, bindings = _shared_graph(tmp_path, probe_calls)
    coordinator = _coordinator(graph)
    media = tmp_path / "shared.flac"
    try:
        coordinator.select_shared_output()
        graph.playback.load_and_play(media)

        assert graph.output_session.mode == "shared"
        assert graph.output_session.plan is None
        assert graph.direct_output_executor.handle is None
        # Shared playback never installs a Strict Direct sink on the engine.
        assert bindings.pipelines[-1].audio_sink is None
        assert probe_calls == []
    finally:
        _close_graph(graph)


def test_pc13_02_03_shared_playback_uses_shared_transaction(
    qapp, tmp_path: Path
) -> None:
    probe_calls: list[dict] = []
    graph, _bindings = _shared_graph(tmp_path, probe_calls)
    coordinator = _coordinator(graph)
    media = tmp_path / "shared.flac"
    try:
        coordinator.select_shared_output()
        token = graph.output_session.prepare_for_media(media)

        assert token.startswith("output-tx:shared:")
        assert graph.output_session.mode == "shared"
        assert graph.output_session._shared_receipt is not None
        assert graph.output_session._executor is None
        assert probe_calls == []
    finally:
        _close_graph(graph)


# ── Phase 3 — device identity vs output-path policy ────────────────────────


def test_pc13_03_01_device_selection_never_implies_strict_direct(
    qapp, tmp_path: Path
) -> None:
    probe_calls: list[dict] = []
    graph, _bindings = _shared_graph(tmp_path, probe_calls)
    coordinator = _coordinator(graph)
    try:
        coordinator.select_shared_output()
        coordinator.select_device("usb:2622:0105:DX5ABC123")

        selection = graph.audio_output_profiles.load_selection()
        assert selection.selected_device_id == "usb:2622:0105:DX5ABC123"
        assert selection.selected_profile_id is None
        assert graph.output_session.mode == "shared"
        assert probe_calls == []
    finally:
        _close_graph(graph)


def test_pc13_03_02_path_mode_selection_never_changes_device_identity(
    qapp, tmp_path: Path
) -> None:
    probe_calls: list[dict] = []
    graph, _bindings = _shared_graph(tmp_path, probe_calls)
    coordinator = _coordinator(graph)
    device_id = "usb:2622:0105:DX5ABC123"
    try:
        coordinator.select_shared_output()
        coordinator.select_device(device_id)
        coordinator.select_path_mode("strict")

        selection = graph.audio_output_profiles.load_selection()
        assert selection.selected_device_id == device_id
        profile = next(
            item
            for item in graph.audio_output_profiles.load_profiles()
            if item.profile_id == selection.selected_profile_id
        )
        assert profile.stable_device_id == device_id
        assert profile.path is OutputPathPreference.HARDWARE_DIRECT
        assert graph.output_session.mode == "shared"  # no playback started yet
    finally:
        _close_graph(graph)


def test_pc13_03_03_strict_and_compatible_are_distinct_persisted_policies(
    qapp, tmp_path: Path
) -> None:
    probe_calls: list[dict] = []
    graph, _bindings = _shared_graph(tmp_path, probe_calls)
    coordinator = _coordinator(graph)
    device_id = "usb:2622:0105:DX5ABC123"
    try:
        coordinator.select_shared_output()
        coordinator.select_device(device_id)
        coordinator.select_path_mode("strict")
        strict_id = graph.audio_output_profiles.load_selection().selected_profile_id

        coordinator.select_path_mode("compatible")
        compatible_id = graph.audio_output_profiles.load_selection().selected_profile_id

        assert strict_id != compatible_id
        profiles = {
            item.profile_id: item
            for item in graph.audio_output_profiles.load_profiles()
        }
        assert profiles[strict_id].path is OutputPathPreference.HARDWARE_DIRECT
        assert (
            profiles[compatible_id].path
            is OutputPathPreference.HARDWARE_DIRECT_COMPATIBLE
        )
        # Switching policy never changes the selected hardware identity.
        assert (
            graph.audio_output_profiles.load_selection().selected_device_id == device_id
        )
    finally:
        _close_graph(graph)


def test_pc13_03_04_restart_restores_device_and_policy_truth(
    qapp, tmp_path: Path
) -> None:
    probe_calls: list[dict] = []
    graph, _bindings = _shared_graph(tmp_path, probe_calls)
    coordinator = _coordinator(graph)
    device_id = "usb:2622:0105:DX5ABC123"
    try:
        coordinator.select_shared_output()
        coordinator.select_device(device_id)
        coordinator.select_path_mode("compatible")

        # A fresh coordinator over the same persisted authorities == restart.
        restarted = _coordinator(graph)
        selection = graph.audio_output_profiles.load_selection()
        assert selection.selected_device_id == device_id
        profile = next(
            item
            for item in graph.audio_output_profiles.load_profiles()
            if item.profile_id == selection.selected_profile_id
        )
        assert profile.path is OutputPathPreference.HARDWARE_DIRECT_COMPATIBLE

        # Device identity survives a policy re-selection after restart.
        restarted.select_path_mode("strict")
        after = graph.audio_output_profiles.load_selection()
        assert after.selected_device_id == device_id
        assert after.selected_profile_id != selection.selected_profile_id
    finally:
        _close_graph(graph)
