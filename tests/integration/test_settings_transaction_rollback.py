"""Settings reset_all must be transactional and compensable.

A failure on any key rolls back every already-applied key to its captured
previous value (readback through the settings store), the result reports
FAILED + the rolled_back list, and exactly ONE event is emitted per call.
The success path applies every default, readback shows defaults, and a single
snapshot event is emitted.
"""
from __future__ import annotations

from unittest.mock import patch

from core.settings_runtime_coordinator import SettingsRuntimeCoordinator
from core.settings_service import SettingsService
from core.settings_schema import ALL_CATEGORIES


class FakeStore:
    """In-memory stand-in for QSettings (value/setValue/sync/status/contains)."""

    def __init__(self, seed: dict | None = None) -> None:
        self.data = dict(seed or {})
        self.synced = 0

    def value(self, key, default=None):
        return self.data.get(key, default)

    def setValue(self, key, value):
        self.data[key] = value

    def sync(self):
        self.synced += 1

    def status(self):
        return 0

    def contains(self, key):
        return key in self.data

    def remove(self, key):
        self.data.pop(key, None)


def _all_keys() -> list[str]:
    return [
        entry.key
        for cat in ALL_CATEGORIES
        for section in cat.sections
        for entry in section.entries
    ]


def _make_service(store: FakeStore):
    """Service + coordinator with adapters, backed by ``store``."""
    from core.settings_adapters import AudioSettingsAdapter, LibrarySettingsAdapter
    coordinator = SettingsRuntimeCoordinator()
    coordinator.register_adapter(AudioSettingsAdapter())
    coordinator.register_adapter(LibrarySettingsAdapter())
    service = SettingsService(coordinator=coordinator, event_bus=None)
    patchers = [
        patch("core.settings_runtime_coordinator.SETTINGS", store),
        patch("core.settings_service.SETTINGS", store),
    ]
    for p in patchers:
        p.start()
    return coordinator, service, patchers


def _valid_non_default(entry):
    """A value that differs from the default AND passes schema validation."""
    if entry.entry_type == "bool":
        return not entry.default
    if entry.entry_type in ("int", "float"):
        if entry.min_value is None or entry.max_value is None:
            return entry.default + 1
        mid = (entry.min_value + entry.max_value) / 2
        if mid == entry.default:
            mid = entry.default + 1
        return int(mid) if entry.entry_type == "int" else float(mid)
    if entry.entry_type == "select" and entry.options:
        for opt in entry.options:
            if opt.get("value") != entry.default:
                return opt.get("value")
        return None
    if entry.entry_type in ("text", "file", "directory", "secret", "audio_device"):
        return f"{entry.default}-user"
    return None


def _non_default_seed() -> dict:
    """One distinct, VALID non-default value per schema key."""
    seed = {}
    for cat in ALL_CATEGORIES:
        for section in cat.sections:
            for entry in section.entries:
                value = _valid_non_default(entry)
                if value is not None:
                    seed[entry.key] = value
    return seed


class TestResetAllSuccess:
    def test_success_applies_defaults_and_readback_matches(self):
        store = FakeStore(_non_default_seed())
        _coordinator, service, patchers = _make_service(store)
        try:
            result = service.reset_all()

            assert result["ok"] is True, result
            assert result["status"] == "COMPLETED", result
            for cat in ALL_CATEGORIES:
                for section in cat.sections:
                    for entry in section.entries:
                        assert store.value(entry.key) == entry.default, entry.key
            assert result["failed"] == []
            assert result["rolled_back"] == []
            assert "audio/device" in result["restart_required"], (
                "restart-required keys must be reported"
            )
        finally:
            for p in patchers:
                p.stop()

    def test_success_emits_single_snapshot_event(self):
        store = FakeStore(_non_default_seed())
        previous_snapshot = dict(store.data)
        events: list[tuple[str, dict]] = []

        class FakeBus:
            def emit(self, event, payload):
                events.append((event, payload))

        coordinator = SettingsRuntimeCoordinator()
        service = SettingsService(coordinator=coordinator, event_bus=FakeBus())
        patchers = [
            patch("core.settings_runtime_coordinator.SETTINGS", store),
            patch("core.settings_service.SETTINGS", store),
        ]
        for p in patchers:
            p.start()
        try:
            result = service.reset_all()

            assert result["ok"] is True
            assert len(events) == 1, "exactly one event per reset_all"
            event, payload = events[0]
            assert event == "settings.reset_all.completed"
            assert payload["previous"] == previous_snapshot
            assert payload["new"] == store.data
            assert "applied" in payload
        finally:
            for p in patchers:
                p.stop()


class TestResetAllRollback:
    def test_failure_rolls_back_all_previously_applied_keys(self):
        store = FakeStore(_non_default_seed())
        previous_snapshot = dict(store.data)
        coordinator, service, patchers = _make_service(store)
        failing = _all_keys()[5]

        original_execute = coordinator.execute

        def exploding_execute(key, value):
            if key == failing:
                return {
                    "ok": False, "key": key, "error_code": "INJECTED_FAILURE",
                    "message": "Injected failure for rollback test",
                }
            return original_execute(key, value)

        coordinator.execute = exploding_execute
        try:
            result = service.reset_all()

            assert result["ok"] is False
            assert result["status"] == "FAILED", result
            assert result["failed"][0]["key"] == failing
            assert result["rolled_back"], "applied keys must be compensated"
            for cat in ALL_CATEGORIES:
                for section in cat.sections:
                    for entry in section.entries:
                        expected = previous_snapshot.get(entry.key, entry.default)
                        assert store.value(entry.key) == expected, entry.key
        finally:
            for p in patchers:
                p.stop()

    def test_failure_result_reports_rolled_back_list_and_single_event(self):
        store = FakeStore(_non_default_seed())
        events: list[str] = []

        class FakeBus:
            def emit(self, event, payload):
                events.append(event)

        coordinator = SettingsRuntimeCoordinator()
        service = SettingsService(coordinator=coordinator, event_bus=FakeBus())
        failing = _all_keys()[3]

        original_execute = coordinator.execute

        def exploding_execute(key, value):
            if key == failing:
                return {
                    "ok": False, "key": key, "error_code": "INJECTED_FAILURE",
                    "message": "Injected failure for rollback test",
                }
            return original_execute(key, value)

        coordinator.execute = exploding_execute
        patchers = [
            patch("core.settings_runtime_coordinator.SETTINGS", store),
            patch("core.settings_service.SETTINGS", store),
        ]
        for p in patchers:
            p.start()
        try:
            result = service.reset_all()

            assert result["ok"] is False
            assert set(result["rolled_back"]) == set(result["applied"])
            assert len(result["rolled_back"]) > 0
            assert len(events) == 1
            assert events[0] == "settings.reset_all.failed"
        finally:
            for p in patchers:
                p.stop()

    def test_no_coordinator_returns_failed(self):
        service = SettingsService(coordinator=None)
        result = service.reset_all()
        assert result["ok"] is False
        assert result["error_code"] == "NO_COORDINATOR"


class TestSettingsOpenDelegatesNavigation:
    def test_open_without_navigation_is_unavailable(self):
        service = SettingsService(coordinator=None)
        result = service.open()
        assert result["ok"] is False
        assert result["code"] == "NAVIGATION_UNAVAILABLE"

    def test_open_delegates_to_navigation_service(self):
        class FakeNavigation:
            def navigate(self, route, params=None):
                return {"ok": True, "code": "NAVIGATION_REQUESTED", "route": route}

        service = SettingsService(coordinator=None, navigation_service=FakeNavigation())
        result = service.open()
        assert result["ok"] is True
        assert result["status"] == "NAVIGATION_REQUESTED"
        assert result["route"] == "settings"
