"""AP2-F05 WU0.1 Finding C — output-intent freshness (OI matrix).

A pending preparation is fenced by the MONOTONIC output-intent revision, so a
worker built for an older user intent can never commit over a newer one,
independently of the media-request generation. ABA is sealed by the revision
(value equality is not freshness).
"""

from __future__ import annotations

import dataclasses
import threading
import time
from pathlib import Path

import pytest

from michi.application.audio_output_planner import OutputPlanner
from michi.application.audio_output_profile_service import AudioOutputProfileService
from michi.application.audio_output_selection_coordinator import (
    AudioOutputSelectionCoordinator,
)
from michi.application.output_session_service import (
    OutputRequest,
    OutputSessionService,
)
from michi.domain.audio_output import (
    AudioOutputSelection,
    OutputPathPreference,
    stable_direct_preset,
)


class _MemRepo:
    def __init__(self) -> None:
        self.profiles: dict = {}
        self.selection = AudioOutputSelection(None, None, 0)

    def load_profiles(self):
        return tuple(sorted(self.profiles.values(), key=lambda item: item.profile_id))

    def save_profile(self, profile) -> None:
        self.profiles[profile.profile_id] = profile

    def load_selection(self) -> AudioOutputSelection:
        return self.selection

    def save_selection(self, selection) -> None:
        self.selection = selection


class _DeferredExecutor:
    def __init__(self) -> None:
        self._completions: list[tuple] = []
        self._lock = threading.Lock()

    def submit(self, work, completed) -> None:
        def run() -> None:
            try:
                value = work()
            except Exception as exc:  # noqa: BLE001 - typed completion
                with self._lock:
                    self._completions.append((completed, None, exc))
            else:
                with self._lock:
                    self._completions.append((completed, value, None))

        threading.Thread(target=run, daemon=True).start()

    def deliver(self) -> int:
        delivered = 0
        while True:
            with self._lock:
                if not self._completions:
                    return delivered
                completed, value, error = self._completions.pop(0)
            completed(value, error)
            delivered += 1

    def wait(self, timeout_s: float = 5.0) -> None:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            with self._lock:
                if self._completions:
                    return
            time.sleep(0.005)
        raise AssertionError("no completion arrived")


class _BlockingResolver:
    def __init__(self, profiles: AudioOutputProfileService) -> None:
        self._profiles = profiles
        self.entered = threading.Event()
        self.release = threading.Event()

    def snapshot_output_intent(self):
        return self._profiles.snapshot_output_intent()

    def pending_device_id(self, path):
        return None

    def __call__(self, path: Path) -> OutputRequest:
        self.entered.set()
        self.release.wait(timeout=8.0)
        return OutputRequest.shared()


def _harness():
    profiles = AudioOutputProfileService(_MemRepo())
    profiles.save_profile(stable_direct_preset("p1", "usb:A"))
    profiles.save_profile(stable_direct_preset("p2", "usb:B"))
    profiles.save_selection(AudioOutputSelection("p1", "usb:A", 1))
    resolver = _BlockingResolver(profiles)
    executor = _DeferredExecutor()
    cancelled: list[int] = []
    service = OutputSessionService(
        OutputPlanner(),
        request_provider=resolver,
        executors={},
        async_submit=executor.submit,
        cancel_prepare_work=lambda: cancelled.append(1),
    )
    return profiles, resolver, executor, service, cancelled


def _dispatch_and_settle(service, executor, resolver):
    tokens: list[str] = []
    failures: list[Exception] = []
    service.prepare_for_media_async(
        Path("/tmp/media.flac"), tokens.append, failures.append
    )
    assert resolver.entered.wait(timeout=2.0)
    return tokens, failures


_MUTATIONS = {
    "OI-01 select device B": lambda profiles: profiles.save_selection(
        AudioOutputSelection("p2", "usb:B", 10)
    ),
    "OI-02 select shared": lambda profiles: profiles.save_selection(
        AudioOutputSelection(None, "usb:A", 11)
    ),
    "OI-03 choose direct B": lambda profiles: profiles.save_selection(
        AudioOutputSelection("p2", "usb:B", 12)
    ),
    "OI-04 select profile Y": lambda profiles: profiles.save_selection(
        AudioOutputSelection("p2", "usb:B", 13)
    ),
    "OI-05 strict -> compatible": lambda profiles: profiles.save_profile(
        dataclasses.replace(
            next(p for p in profiles.load_profiles() if p.profile_id == "p1"),
            path=OutputPathPreference.HARDWARE_DIRECT_COMPATIBLE,
        )
    ),
    "OI-06 same profile content change": lambda profiles: profiles.save_profile(
        dataclasses.replace(
            next(p for p in profiles.load_profiles() if p.profile_id == "p1"),
            resync_delay_ms=123,
        )
    ),
}


@pytest.mark.parametrize("name", list(_MUTATIONS))
def test_old_output_intent_can_never_commit(name: str) -> None:
    profiles, resolver, executor, service, _cancelled = _harness()
    tokens, failures = _dispatch_and_settle(service, executor, resolver)

    before = profiles.output_intent_revision
    _MUTATIONS[name](profiles)
    assert profiles.output_intent_revision > before

    resolver.release.set()
    executor.wait()
    executor.deliver()
    assert tokens == [], name
    assert failures and failures[0].code == "OUTPUT_PREPARATION_STALE", name


def test_aba_selection_change_back_is_still_stale() -> None:
    profiles, resolver, executor, service, _cancelled = _harness()
    captured = profiles.snapshot_output_intent()
    tokens, failures = _dispatch_and_settle(service, executor, resolver)

    # A -> B -> A: the values return to the captured ones, but the monotonic
    # revision does not, so freshness cannot be defeated by value equality.
    profiles.save_selection(AudioOutputSelection("p2", "usb:B", 20))
    profiles.save_selection(AudioOutputSelection("p1", "usb:A", 21))
    current = profiles.snapshot_output_intent()
    assert (current.selected_profile_id, current.selected_device_id) == (
        captured.selected_profile_id,
        captured.selected_device_id,
    )
    assert current.revision != captured.revision

    resolver.release.set()
    executor.wait()
    executor.deliver()
    assert tokens == []
    assert failures and failures[0].code == "OUTPUT_PREPARATION_STALE"


def test_unchanged_intent_still_commits() -> None:
    profiles, resolver, executor, service, _cancelled = _harness()
    tokens, failures = _dispatch_and_settle(service, executor, resolver)
    resolver.release.set()
    executor.wait()
    executor.deliver()
    assert len(tokens) == 1 and failures == []


def test_selection_mutation_cancels_the_pending_characterization() -> None:
    profiles, resolver, executor, service, cancelled = _harness()

    devices_calls: list = []

    class _Devices:
        def select_device(self, device_id) -> None:
            devices_calls.append(device_id)

    class _Engines:
        pass

    coordinator = AudioOutputSelectionCoordinator(
        profiles=profiles,
        devices=_Devices(),  # type: ignore[arg-type]
        output_session=service,
        engines=_Engines(),  # type: ignore[arg-type]
    )

    tokens, failures = _dispatch_and_settle(service, executor, resolver)
    assert cancelled == []
    coordinator.select_shared_output()
    # The mutation superseded the pending preparation AND cancelled the
    # blocking characterization work (no orphan worker).
    assert cancelled, "selection change must cancel the pending characterization"

    resolver.release.set()
    executor.wait()
    executor.deliver()
    assert tokens == []
    assert failures and failures[0].code == "OUTPUT_PREPARATION_STALE"
