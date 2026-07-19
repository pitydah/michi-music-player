from PySide6.QtCore import QObject, Property, Slot

from ui_qml_bridge.navigation_bridge import NavigationBridge


class Guard(QObject):
    def __init__(self):
        super().__init__()
        self.pending = True
        self.commits = 0
        self.rollbacks = 0
        self.fail_commit = False
        self.fail_rollback = False

    @Property(bool)
    def hasPendingChanges(self):
        return self.pending

    @Slot(result=dict)
    def commitAll(self):
        self.commits += 1
        if self.fail_commit:
            return {"ok": False, "error": "COMMIT_FAILED"}
        self.pending = False
        return {"ok": True}

    @Slot(result=dict)
    def rollbackAll(self):
        self.rollbacks += 1
        if self.fail_rollback:
            return {"ok": False, "error": "ROLLBACK_FAILED"}
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


def test_apply_resumes_replace_once_without_recursion(qtbot):
    bridge = NavigationBridge()
    guard = Guard()
    bridge.navigate("settings.general")
    bridge.registerLeaveGuard("settings", guard)
    blocked = []
    bridge.navigationBlocked.connect(lambda *_args: blocked.append(True))

    bridge.replace("home")
    result = bridge.resolvePendingNavigation("apply")

    assert result["ok"] is True
    assert guard.commits == 1
    assert bridge.currentRoute == "home"
    assert len(blocked) == 1


def test_guard_covers_back_forward_and_deep_links():
    bridge = NavigationBridge()
    guard = Guard()
    guard.pending = False
    bridge.registerLeaveGuard("settings", guard)
    bridge.navigate("library")
    bridge.navigate("settings")
    guard.pending = True

    bridge.back()
    assert bridge.currentRoute == "settings"
    assert bridge.resolvePendingNavigation("discard")["ok"] is True
    assert bridge.currentRoute == "library"

    guard.pending = True
    bridge.forward()
    assert bridge.currentRoute == "settings"

    result = bridge.deepLink("/home?source=test")
    assert result["blocked"] is True
    assert bridge.currentRoute == "settings"


def test_failed_guard_action_keeps_route_and_pending_request():
    bridge = NavigationBridge()
    guard = Guard()
    guard.fail_rollback = True
    bridge.navigate("settings")
    bridge.registerLeaveGuard("settings", guard)
    bridge.navigate("home")

    result = bridge.resolvePendingNavigation("discard")

    assert result["ok"] is False
    assert bridge.currentRoute == "settings"
    assert bridge.hasPendingNavigation is True
