from __future__ import annotations

from ui_qml_bridge.settings_bridge_v2 import SettingsBridgeV2


class FakeSettingsService:
    def __init__(self):
        self.values = {"appearance.theme": "dark", "audio.volume": 80}
        self.defaults = {"appearance.theme": "system", "audio.volume": 50}

    def categories(self):
        return [
            {
                "id": "general",
                "sections": [
                    {
                        "id": "main",
                        "entries": [
                            {"key": "appearance.theme"},
                            {"key": "audio.volume"},
                        ],
                    }
                ],
            }
        ]

    def get(self, key):
        return self.values.get(key)

    def set_(self, key, value):
        self.values[key] = value
        return {"ok": True, "value": value}

    def reset(self, key):
        self.values[key] = self.defaults[key]
        return {"ok": True}

    def reset_all(self):
        self.values.update(self.defaults)
        return {"ok": True}


class MemoryStore:
    def __init__(self, status=0):
        self.data = {}
        self._status = status
        self.removed = []

    def contains(self, key):
        return key in self.data

    def remove(self, key):
        self.data.pop(key, None)
        self.removed.append(key)

    def sync(self):
        return None

    def status(self):
        return self._status


def test_set_value_marks_bridge_dirty_and_commit_clears_it(qtbot):
    bridge = SettingsBridgeV2(FakeSettingsService())

    result = bridge.setValue("appearance.theme", "light")

    assert result["ok"] is True
    assert bridge.hasPendingChanges is True
    assert bridge.pendingCount == 1
    assert bridge.pending()["pending"][0]["previous"] == "dark"

    committed = bridge.commitAll()
    assert committed == {"ok": True, "changed": ["appearance.theme"], "failed": []}
    assert bridge.hasPendingChanges is False


def test_returning_to_original_value_removes_pending_change(qtbot):
    bridge = SettingsBridgeV2(FakeSettingsService())

    bridge.setValue("audio.volume", 60)
    bridge.setValue("audio.volume", 80)

    assert bridge.hasPendingChanges is False
    assert bridge.pendingCount == 0


def test_rollback_all_restores_original_values(qtbot):
    service = FakeSettingsService()
    bridge = SettingsBridgeV2(service)

    bridge.setValue("appearance.theme", "light")
    bridge.setValue("audio.volume", 20)
    result = bridge.rollbackAll()

    assert result["ok"] is True
    assert result["changed"] == ["audio.volume", "appearance.theme"]
    assert service.values == {"appearance.theme": "dark", "audio.volume": 80}
    assert bridge.hasPendingChanges is False


def test_reset_all_can_be_rolled_back(qtbot):
    service = FakeSettingsService()
    bridge = SettingsBridgeV2(service)

    assert bridge.resetAll()["ok"] is True
    assert service.values == service.defaults
    assert bridge.pendingCount == 2

    bridge.rollbackAll()
    assert service.values == {"appearance.theme": "dark", "audio.volume": 80}


def test_commit_failure_preserves_pending_state(qtbot):
    bridge = SettingsBridgeV2(FakeSettingsService(), settings=MemoryStore(status=1))
    bridge.setValue("appearance.theme", "light")

    result = bridge.commitAll()

    assert result["ok"] is False
    assert result["failed"][0]["error"] == "SETTINGS_SYNC_FAILED"
    assert bridge.hasPendingChanges is True


def test_rollback_removes_key_that_was_originally_absent(qtbot):
    store = MemoryStore()
    service = FakeSettingsService()
    bridge = SettingsBridgeV2(service, settings=store)
    bridge.setValue("appearance.theme", "light")

    result = bridge.rollback("appearance.theme")

    assert result["ok"] is True
    assert store.removed == ["appearance.theme"]
    assert service.values["appearance.theme"] == "dark"


def test_rollback_all_reports_partial_failure_and_keeps_failed_key(qtbot):
    class PartiallyFailingService(FakeSettingsService):
        def set_(self, key, value):
            if key == "appearance.theme" and value == "dark":
                return {"ok": False, "error": "RESTORE_FAILED"}
            return super().set_(key, value)

    service = PartiallyFailingService()
    bridge = SettingsBridgeV2(service, settings=MemoryStore())
    bridge.setValue("appearance.theme", "light")
    bridge.setValue("audio.volume", 20)

    result = bridge.rollbackAll()

    assert result["ok"] is False
    assert result["changed"] == ["audio.volume"]
    assert result["failed"][0]["key"] == "appearance.theme"
    assert bridge.pendingCount == 1


def test_reset_all_tracks_successes_when_one_key_fails(qtbot):
    class PartiallyFailingService(FakeSettingsService):
        def reset(self, key):
            if key == "appearance.theme":
                return {"ok": False, "error": "RESET_FAILED"}
            return super().reset(key)

    bridge = SettingsBridgeV2(PartiallyFailingService(), settings=MemoryStore())
    result = bridge.resetAll()

    assert result["ok"] is False
    assert result["changed"] == ["audio.volume"]
    assert result["failed"][0]["key"] == "appearance.theme"
    assert bridge.pendingCount == 1
