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


def test_set_value_marks_bridge_dirty_and_commit_clears_it(qtbot):
    bridge = SettingsBridgeV2(FakeSettingsService())

    result = bridge.setValue("appearance.theme", "light")

    assert result["ok"] is True
    assert bridge.hasPendingChanges is True
    assert bridge.pendingCount == 1
    assert bridge.pending()["pending"][0]["previous"] == "dark"

    committed = bridge.commitAll()
    assert committed == {"ok": True, "committed": 1}
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
    assert result["restored"] == 2
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
