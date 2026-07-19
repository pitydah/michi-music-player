from PySide6.QtCore import QObject, Property, Slot

from ui_qml_bridge.navigation_bridge import NavigationBridge


class Guard(QObject):
    def __init__(self):
        super().__init__()
        self.pending = True
        self.commits = 0
        self.rollbacks = 0

    @Property(bool)
    def hasPendingChanges(self):
        return self.pending

    @Slot(result=dict)
    def commitAll(self):
        self.commits += 1
        self.pending = False
        return {"ok": True}

    @Slot(result=dict)
    def rollbackAll(self):
        self.rollbacks += 1
        self.pending = False
        return {"ok": True}


def test_navigation_is_blocked_until_pending_settings_are_resolved():
    bridge = NavigationBridge()
    guard = Guard()
    bridge.navigate("settings")
    bridge.registerLeaveGuard("settings", guard)

    bridge.navigate("home")

    assert bridge.currentRoute == "settings"
    assert bridge.hasPendingNavigation is True
    assert bridge.pendingTarget == "home"

    result = bridge.resolvePendingNavigation("discard")

    assert result["ok"] is True
    assert guard.rollbacks == 1
    assert bridge.currentRoute == "home"
    assert bridge.hasPendingNavigation is False


def test_navigation_cancel_keeps_current_route_and_pending_values():
    bridge = NavigationBridge()
    guard = Guard()
    bridge.navigate("settings")
    bridge.registerLeaveGuard("settings", guard)
    bridge.navigate("home")

    result = bridge.resolvePendingNavigation("cancel")

    assert result == {"ok": True, "cancelled": True}
    assert bridge.currentRoute == "settings"
    assert guard.pending is True
