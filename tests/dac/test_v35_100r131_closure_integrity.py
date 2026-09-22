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


# ── Phase 2 — qualification single-flight ──────────────────────────────────


def _await(predicate, *, timeout_s: float = 5.0) -> bool:
    import time

    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.005)
    return bool(predicate())


class _GatedProbe:
    """Exact-open double whose physical body is released by the test."""

    def __init__(self) -> None:
        import threading

        self.calls: list[dict] = []
        self.entered = threading.Event()
        self.release = threading.Event()

    def probe_exact(self, **kwargs):
        from michi.domain.audio_evidence import ExactProbeResult, PcmTuple

        self.calls.append(kwargs)
        self.entered.set()
        self.release.wait(timeout=15)
        requested = PcmTuple(
            kwargs["rate_hz"], kwargs["transport_format"], kwargs["channels"], 16
        )
        return ExactProbeResult(
            requested, requested, "OPENED", None, None, "probe:single-flight"
        )


def _qualification_service(probe, *, follower_timeout_s: float = 10.0, env=None):
    from michi.application.dac_qualification_service import DacQualificationService

    environment = env or (lambda: "env:a")
    return DacQualificationService(
        probe,
        environment_fingerprint=environment,
        single_flight_timeout_s=follower_timeout_s,
    )


def _probe_once(service, *, generation: int | None = None):
    return service.probe_for_play(
        stable_device_id="usb:2622:0105:DX5ABC123",
        locator="hw:CARD=DX5,DEV=0",
        rate_hz=44_100,
        transport_format="S16_LE",
        channels=2,
        binding_generation=generation,
    )


def test_ci131_02_a_one_physical_leader_for_concurrent_equivalent_requests() -> None:
    import threading

    probe = _GatedProbe()
    service = _qualification_service(probe)
    results: list[object] = []

    def worker() -> None:
        results.append(_probe_once(service))

    leader = threading.Thread(target=worker)
    leader.start()
    assert _await(probe.entered.is_set), "the leader never started its physical probe"

    followers = [threading.Thread(target=worker) for _ in range(100)]
    for follower in followers:
        follower.start()
    assert _await(
        lambda: bool(service._flights)
        and next(iter(service._flights.values())).waiters == 100
    ), "followers did not coalesce onto the in-flight qualification"

    probe.release.set()
    leader.join(timeout=15)
    for follower in followers:
        follower.join(timeout=15)

    assert len(probe.calls) == 1
    assert len(results) == 101


def test_ci131_02_b_follower_timeout_never_launches_a_second_probe() -> None:
    import threading

    from michi.application.dac_qualification_service import (
        QualificationSingleFlightTimeoutError,
    )

    probe = _GatedProbe()
    service = _qualification_service(probe, follower_timeout_s=0.2)
    leader_results: list[object] = []
    follower_errors: list[BaseException] = []

    def leader() -> None:
        leader_results.append(_probe_once(service))

    def follower() -> None:
        try:
            _probe_once(service)
        except BaseException as exc:  # noqa: BLE001 — typed assertion below
            follower_errors.append(exc)

    leader_thread = threading.Thread(target=leader)
    leader_thread.start()
    assert _await(probe.entered.is_set)

    followers = [threading.Thread(target=follower) for _ in range(5)]
    for thread in followers:
        thread.start()
    for thread in followers:
        thread.join(timeout=10)

    # The leader is STILL blocked while every follower already timed out.
    assert probe.release.is_set() is False
    assert len(probe.calls) == 1
    assert len(follower_errors) == 5
    assert all(
        isinstance(item, QualificationSingleFlightTimeoutError)
        for item in follower_errors
    )
    assert all(item.code == "EXACT_QUALIFICATION_TIMEOUT" for item in follower_errors)

    probe.release.set()
    leader_thread.join(timeout=15)
    assert len(leader_results) == 1
    assert len(probe.calls) == 1


def test_ci131_02_c_flight_retires_and_a_future_request_can_lead() -> None:
    probe = _GatedProbe()
    probe.release.set()
    service = _qualification_service(probe)

    first = _probe_once(service)
    assert first.evidence.supported is True
    assert service._flights == {}

    second = _probe_once(service)
    assert second.evidence.supported is True
    assert len(probe.calls) == 2


def test_ci131_02_d_binding_generation_change_is_a_different_flight() -> None:
    probe = _GatedProbe()
    probe.release.set()
    service = _qualification_service(probe)

    _probe_once(service, generation=1)
    _probe_once(service, generation=2)

    assert len(probe.calls) == 2


def test_ci131_02_e_environment_change_is_a_different_flight() -> None:
    probe = _GatedProbe()
    probe.release.set()
    environment = {"value": "env:a"}
    service = _qualification_service(probe, env=lambda: environment["value"])

    first = _probe_once(service)
    environment["value"] = "env:b"
    second = _probe_once(service)

    assert len(probe.calls) == 2
    assert (
        first.evidence.environment_fingerprint
        != second.evidence.environment_fingerprint
    )
