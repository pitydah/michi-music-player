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
from michi.application.carrier_resolution import (
    CandidateCarrierResolver,
    CarrierAdaptationKind,
)
from michi.domain.audio_evidence import DecodedSourceSignal
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


# ── Phase 4 — bounded candidate carrier resolution ─────────────────────────


def _decoded_source(bits: int | None, *, rate: int = 44_100, channels: int = 2):
    return DecodedSourceSignal("PCM", rate, bits, channels, None)


def test_pc13_04_01_sixteen_bit_exact_candidate_is_the_narrow_container() -> None:
    resolved = CandidateCarrierResolver().candidates(
        _decoded_source(16), allow_adaptation=False
    )
    assert [item.tuple.transport_format for item in resolved] == ["S16_LE"]
    assert resolved[0].adaptation_kind is CarrierAdaptationKind.EXACT
    assert resolved[0].tuple.significant_bits == 16
    assert resolved[0].tuple.rate_hz == 44_100
    assert resolved[0].tuple.channels == 2


def test_pc13_04_02_compatible_adds_bounded_wide_container_candidate() -> None:
    resolved = CandidateCarrierResolver().candidates(
        _decoded_source(16), allow_adaptation=True
    )
    assert [item.tuple.transport_format for item in resolved] == ["S16_LE", "S32_LE"]
    adapted = resolved[1]
    assert adapted.adaptation_kind is CarrierAdaptationKind.CONTAINER_WIDTH
    # Container width never fabricates precision.
    assert adapted.tuple.significant_bits == 16
    assert adapted.tuple.rate_hz == 44_100
    assert adapted.tuple.channels == 2


def test_pc13_04_03_strict_excludes_every_adaptation_candidate() -> None:
    strict = CandidateCarrierResolver().candidates(
        _decoded_source(16), allow_adaptation=False
    )
    assert all(item.is_exact for item in strict)
    assert all(
        item.adaptation_kind is not CarrierAdaptationKind.CONTAINER_WIDTH
        for item in strict
    )


def test_pc13_04_04_unknown_significant_bits_never_candidates_or_adapts() -> None:
    for allow_adaptation in (False, True):
        assert (
            CandidateCarrierResolver().candidates(
                _decoded_source(None), allow_adaptation=allow_adaptation
            )
            == ()
        )


def test_pc13_04_05_invalid_source_geometry_yields_no_candidates() -> None:
    resolver = CandidateCarrierResolver()
    assert resolver.candidates(_decoded_source(16, rate=0), allow_adaptation=True) == ()
    assert (
        resolver.candidates(_decoded_source(16, channels=0), allow_adaptation=True)
        == ()
    )


def test_pc13_04_06_twenty_four_bit_candidates_are_deterministic() -> None:
    resolver = CandidateCarrierResolver()
    first = resolver.candidates(_decoded_source(24), allow_adaptation=True)
    second = resolver.candidates(_decoded_source(24), allow_adaptation=True)
    assert first == second
    assert [item.tuple.transport_format for item in first] == ["S32_LE"]
    assert first[0].tuple.significant_bits == 24


def test_pc13_04_07_candidate_set_is_bounded_and_priority_ordered() -> None:
    resolver = CandidateCarrierResolver()
    resolved = resolver.candidates(_decoded_source(16), allow_adaptation=True)
    assert len(resolved) <= resolver.MAX_CANDIDATES
    assert [item.priority for item in resolved] == sorted(
        item.priority for item in resolved
    )
    assert resolved[0].is_exact


def test_pc13_04_08_carrier_tuple_returns_the_exact_candidate_only() -> None:
    from michi.application.audio_output_planner import carrier_tuple

    source = _decoded_source(16)
    assert carrier_tuple(source) == CandidateCarrierResolver().candidates(
        source, allow_adaptation=False
    )[0].tuple
    assert carrier_tuple(_decoded_source(None)) is None
