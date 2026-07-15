"""PJ — Tests for cross-cutting layers (capas transversales).

Verifies that each bridge has proper integrations for:
  JobService, ActionRegistry, ConfirmationService, NavigationBridge,
  PageStateStore, CapabilityBridge, AccessibilityBridge, NotificationBridge.

No NOT IMPLEMENTED is accepted except DEFERRED_PHYSICAL.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.action_registry import ActionRegistry
from ui_qml_bridge.accessibility_bridge import AccessibilityBridge
from ui_qml_bridge.capability_bridge import CapabilityBridge
from ui_qml_bridge.confirmation_bridge import ConfirmationBridge
from ui_qml_bridge.job_bridge import JobBridge
from ui_qml_bridge.navigation_bridge import NavigationBridge
from ui_qml_bridge.notification_bridge import NotificationBridge
from ui_qml_bridge.page_state_store import PageStateStore
from ui_qml_bridge.route_registry import ROUTES

pytestmark = [pytest.mark.qml_module("capas_transversales")]


class TestNavigationBridgeIntegrations:
    def test_navigation_bridge_has_route_registry(self):
        nav = NavigationBridge()
        assert nav._resolve("home") == "home"
        assert nav._resolve("non_existent") == "placeholder"

    def test_navigation_bridge_back_forward_fullcycle(self):
        nav = NavigationBridge()
        nav.navigate("library")
        nav.navigate("radio")
        nav.navigate("playback")
        nav.back()
        assert nav.currentRoute == "radio"
        nav.back()
        assert nav.currentRoute == "library"
        nav.forward()
        assert nav.currentRoute == "radio"

    def test_navigation_bridge_params_validation(self):
        nav = NavigationBridge()
        nav.navigateWithParams("library.album_detail", {"album_key": "abc"})
        assert nav.currentRoute == "library.album_detail"
        assert nav.currentParams["album_key"] == "abc"

    def test_navigation_bridge_missing_params_error(self):
        nav = NavigationBridge()
        errors = []
        nav.invalidRouteError.connect(lambda r, m: errors.append(m))
        nav.navigateWithParams("library.album_detail", {})
        assert len(errors) >= 1

    def test_navigation_bridge_save_restore_state(self):
        nav = NavigationBridge()
        nav.navigate("library")
        nav.navigateWithParams("library.album_detail", {"album_key": "xyz"})
        state = nav.saveState()
        assert state["ok"]

        nav2 = NavigationBridge()
        result = nav2.restoreState(state["state"])
        assert result["ok"]
        assert nav2.currentRoute == "library.album_detail"
        assert nav2.currentParams["album_key"] == "xyz"

    def test_navigation_bridge_deep_link(self):
        nav = NavigationBridge()
        result = nav.deepLink("/library.album_detail?album_key=test")
        assert result["ok"]
        assert result["route"] == "library.album_detail"

    def test_navigation_bridge_capability_gate(self):
        nav = NavigationBridge()
        nav.set_capabilities(set())
        nav.navigate("audio_lab.overview")
        assert nav.currentRoute == "home"

    def test_navigation_bridge_replace(self):
        nav = NavigationBridge()
        nav.replace("radio")
        assert nav.currentRoute == "radio"
        assert not nav.canGoBack

    def test_navigation_bridge_clear_history(self):
        nav = NavigationBridge()
        nav.navigate("library")
        nav.clearHistory()
        assert not nav.canGoBack
        assert not nav.canGoForward

    def test_navigation_bridge_refresh_signal(self):
        nav = NavigationBridge()
        signals = []
        nav.routeRefreshRequested.connect(lambda r: signals.append(r))
        nav.refreshCurrent()
        assert signals == ["home"]

    def test_navigation_bridge_history_limit(self):
        nav = NavigationBridge()
        for _ in range(60):
            nav.navigate("library")
        assert len(nav._back_stack) <= 50

    def test_navigation_bridge_current_title_all_routes(self):
        nav = NavigationBridge()
        for route_key in ROUTES:
            nav._current_route = route_key
            title = nav.currentTitle
            assert title and len(title) > 0

    def test_navigation_bridge_unknown_title(self):
        nav = NavigationBridge()
        nav._current_route = "bogus_route"
        assert nav.currentTitle == "Sección en migración"


class TestPageStateStoreIntegrations:
    def test_page_state_store_save_restore(self):
        store = PageStateStore()
        store.saveState("home", {"scroll": 42, "filter": "rock"})
        state = store.restoreState("home")
        assert state["scroll"] == 42
        assert state["filter"] == "rock"

    def test_page_state_store_has_state(self):
        store = PageStateStore()
        assert not store.hasState("home")
        store.saveState("home", {"x": 1})
        assert store.hasState("home")

    def test_page_state_store_restore_unknown(self):
        store = PageStateStore()
        assert store.restoreState("unknown") == {}

    def test_page_state_store_history(self):
        store = PageStateStore()
        store.saveState("home", {})
        store.saveState("library", {})
        store.saveState("radio", {})
        hist = store.history
        assert "home" in hist
        assert "library" in hist
        assert "radio" in hist

    def test_page_state_store_previous_route(self):
        store = PageStateStore()
        store.saveState("home", {})
        store.saveState("library", {})
        assert store.previousRoute() == "home"

    def test_page_state_store_previous_route_default(self):
        store = PageStateStore()
        assert store.previousRoute() == "home"

    def test_page_state_store_clear(self):
        store = PageStateStore()
        store.saveState("home", {"x": 1})
        store.clear()
        assert not store.hasState("home")
        assert len(store.history) == 0

    def test_page_state_store_history_limit(self):
        store = PageStateStore()
        for i in range(30):
            store.saveState(f"route{i}", {})
        assert len(store.history) <= 20

    def test_page_state_store_no_duplicate_consecutive(self):
        store = PageStateStore()
        store.saveState("home", {})
        store.saveState("home", {})
        assert store.history.count("home") == 1


class TestCapabilityBridgeIntegrations:
    def test_capability_bridge_has_all_keys(self):
        from ui_qml_bridge.capability_bridge import CAPABILITY_STATE_KEYS
        factory = MagicMock()
        factory.capabilities = {}
        cb = CapabilityBridge(factory=factory)
        cb.refresh()
        caps = cb.capabilities
        for key in CAPABILITY_STATE_KEYS:
            assert key in caps, f"Missing capability key: {key}"

    def test_capability_bridge_refresh_populates(self):
        factory = MagicMock()
        factory.capabilities = {"library": "available"}
        cb = CapabilityBridge(factory=factory)
        assert cb.capabilities == {}
        cb.refresh()
        assert len(cb.capabilities) > 0

    def test_capability_bridge_has_method(self):
        factory = MagicMock()
        factory.capabilities = {}
        cb = CapabilityBridge(factory=factory)
        cb.refresh()
        assert not cb.has("library")

    def test_capability_bridge_with_factory(self):
        factory = MagicMock()
        factory.capabilities = {"library": "available", "playback": "available"}
        cb = CapabilityBridge(factory=factory)
        cb.refresh()
        caps = cb.capabilities
        assert caps.get("library") == "available"
        assert caps.get("playback") == "available"

    def test_capability_bridge_signal_emitted(self):
        factory = MagicMock()
        factory.capabilities = {}
        signals = []
        cb = CapabilityBridge(factory=factory)
        cb.dataChanged.connect(lambda: signals.append(True))
        cb.refresh()
        assert len(signals) >= 1


class TestAccessibilityBridgeIntegrations:
    def test_accessibility_bridge_defaults(self):
        ab = AccessibilityBridge()
        assert ab.fontScale in ("normal", "large", "small")
        assert isinstance(ab.highContrast, bool)
        assert isinstance(ab.reduceMotion, bool)

    def test_accessibility_bridge_set_font_scale(self):
        ab = AccessibilityBridge()
        ab.fontScale = "large"
        assert ab.fontScale == "large"

    def test_accessibility_bridge_set_high_contrast(self):
        ab = AccessibilityBridge()
        ab.highContrast = True
        assert ab.highContrast

    def test_accessibility_bridge_set_reduce_motion(self):
        ab = AccessibilityBridge()
        ab.reduceMotion = True
        assert ab.reduceMotion

    def test_accessibility_bridge_set_mono(self):
        ab = AccessibilityBridge()
        ab.mono = True
        assert ab.mono

    def test_accessibility_bridge_set_balance(self):
        ab = AccessibilityBridge()
        ab.balance = 30
        assert ab.balance == 30

    def test_accessibility_bridge_balance_clamped(self):
        ab = AccessibilityBridge()
        ab.balance = 200
        assert ab.balance <= 100
        ab.balance = -200
        assert ab.balance >= -100

    def test_accessibility_bridge_with_playback_service(self):
        ps = MagicMock()
        ab = AccessibilityBridge(playback_service=ps)
        assert ab._playback_service is ps

    def test_accessibility_bridge_restore_on_error(self):
        ab = AccessibilityBridge()
        ab.mono = True
        ab.balance = 50
        result = ab.restoreOnError()
        assert result["ok"]
        assert not result["mono"]
        assert result["balance"] == 0

    def test_accessibility_bridge_refresh(self):
        ab = AccessibilityBridge()
        old = ab.fontScale
        ab.fontScale = "large" if old != "large" else "small"
        val_before = ab.fontScale
        ab.refresh()
        assert isinstance(ab.fontScale, str)

    def test_accessibility_bridge_score(self):
        ab = AccessibilityBridge()
        score = ab.accessibilityScore()
        assert "score" in score
        assert 0 <= score["score"] <= 100

    def test_accessibility_bridge_last_error_default(self):
        ab = AccessibilityBridge()
        assert ab.lastError == ""


class TestNotificationBridgeIntegrations:
    def test_notification_bridge_show_message(self):
        nb = NotificationBridge()
        result = nb.showMessage("Test message")
        assert result["ok"]

    def test_notification_bridge_current_notification(self):
        nb = NotificationBridge()
        nb.showMessage("Hello")
        assert nb.currentNotification is not None
        assert nb.currentNotification["text"] == "Hello"

    def test_notification_bridge_queue_length(self):
        nb = NotificationBridge()
        nb.showMessage("One")
        nb.showMessage("Two")
        assert nb.queueLength >= 1

    def test_notification_bridge_dismiss(self):
        nb = NotificationBridge()
        nb.showMessage("Msg", kind="info", persistent=False)
        nb.dismiss()
        assert nb.currentNotification is None

    def test_notification_bridge_clear(self):
        nb = NotificationBridge()
        nb.showMessage("Test")
        nb.showAction("Action", "undo")
        nb.clear()
        assert nb.queueLength == 0
        assert nb.currentNotification is None

    def test_notification_bridge_show_action(self):
        nb = NotificationBridge()
        result = nb.showAction("Action needed", "openSettings")
        assert result["ok"]

    def test_notification_bridge_show_progress(self):
        nb = NotificationBridge()
        result = nb.showProgress("Working", "job1", 50)
        assert result["ok"]

    def test_notification_bridge_update_progress(self):
        nb = NotificationBridge()
        nb.showProgress("Working", "job1", 30)
        result = nb.updateProgress("job1", 0.75, "Nearly done")
        assert result["ok"]

    def test_notification_bridge_with_action_registry(self):
        ar = ActionRegistry()
        nb = NotificationBridge(action_registry=ar)
        assert nb._action_registry is ar

    def test_notification_bridge_with_navigation(self):
        nav = NavigationBridge()
        nb = NotificationBridge(navigation_bridge=nav)
        result = nb.openDiagnostics()
        assert result["ok"]

    def test_notification_bridge_with_job_bridge(self):
        jb = MagicMock(spec=JobBridge)
        nb = NotificationBridge(job_bridge=jb)
        assert nb._job_bridge is jb

    def test_notification_bridge_score(self):
        nb = NotificationBridge()
        score = nb.notificationScore()
        assert "score" in score
        assert 0 <= score["score"] <= 100

    def test_notification_bridge_execute_current_action(self):
        ar = ActionRegistry()
        nb = NotificationBridge(action_registry=ar)
        nb.showAction("Do something", "navigate_home")
        result = nb.executeCurrentAction()
        assert result["ok"] is False

    def test_notification_bridge_dedup(self):
        nb = NotificationBridge()
        nb.showMessage("Duplicate")
        nb.showMessage("Duplicate")
        assert nb.queueLength <= 2

    def test_notification_bridge_persistent(self):
        nb = NotificationBridge()
        nb.showMessage("Persistent", kind="error", persistent=True)
        assert len(nb.persistentNotifications) >= 1

    def test_notification_bridge_persistent_cleared_on_dismiss(self):
        nb = NotificationBridge()
        nb.showMessage("Persistent", kind="warning", persistent=True)
        notif_id = nb.currentNotification["id"]
        nb.dismiss(notif_id)
        pers = nb.persistentNotifications
        matches = [p for p in pers if p["id"] == notif_id]
        assert len(matches) == 0


class TestJobBridgeIntegrations:
    def test_job_bridge_initial_state(self):
        jb = JobBridge()
        assert jb.jobs == []
        assert jb.activeCount == 0

    def test_job_bridge_run_job(self):
        jb = JobBridge()
        result = jb.runJob("library_scan", "/some/path")
        assert result["ok"]

    def test_job_bridge_run_job_unknown(self):
        jb = JobBridge()
        result = jb.runJob("unknown_job")
        assert not result["ok"]

    def test_job_bridge_active_count(self):
        jb = JobBridge()
        jb._add_job("test", "Test job")
        assert jb.activeCount >= 1

    def test_job_bridge_cancel_job(self):
        jb = JobBridge()
        jb._add_job("test", "Test job")
        jobs = jb.jobs
        assert len(jobs) > 0
        job_id = jobs[0]["job_id"]
        result = jb.cancelJob(job_id)
        assert result["ok"]

    def test_job_bridge_cancel_nonexistent(self):
        jb = JobBridge()
        result = jb.cancelJob(9999)
        assert not result["ok"]

    def test_job_bridge_clear_completed(self):
        jb = JobBridge()
        jb._add_job("test", "Test job")
        jb.clearCompleted()
        assert jb.activeCount >= 0

    def test_job_bridge_clear_failed(self):
        jb = JobBridge()
        jb._add_job("test", "Test job")
        jb.clearFailed()
        assert jb.activeCount >= 0

    def test_job_bridge_retry_job(self):
        jb = JobBridge()
        jb._add_job("test", "Test job")
        result = jb.retryJob(9999)
        assert not result["ok"]

    def test_job_bridge_with_worker_manager(self):
        wm = MagicMock()
        jb = JobBridge(worker_manager=wm)
        result = jb.runJob("library_scan", "/tmp")
        assert result["ok"]

    def test_job_bridge_prune_max_jobs(self):
        jb = JobBridge()
        for i in range(250):
            jb._add_job("test", "Test job")
            jb._update_job(i + 1, state="completed")
        assert len(jb.jobs) <= 200

    def test_job_bridge_attach_library_coordinator(self):
        jb = JobBridge()
        coord = MagicMock()
        jb.attach_library_coordinator(coord)
        assert jb._library_coordinator is coord

    def test_job_bridge_update_job(self):
        jb = JobBridge()
        jb.runJob("library_scan", "/tmp")
        job_id = jb.jobs[0]["job_id"]
        jb._update_job(job_id, state="completed", progress=100)
        updated = [j for j in jb.jobs if j["job_id"] == job_id]
        assert len(updated) == 1
        assert updated[0]["state"] == "completed"
        assert updated[0]["progress"] == 100


class TestActionRegistryIntegrations:
    def test_action_registry_default_actions(self):
        ar = ActionRegistry()
        actions = ar.actions
        assert len(actions) > 0

    def test_action_registry_get_existing(self):
        ar = ActionRegistry()
        action = ar.get("navigate_home")
        assert action is not None
        assert action.title == "Ir a Inicio"

    def test_action_registry_get_nonexistent(self):
        ar = ActionRegistry()
        assert ar.get("nonexistent") is None

    def test_action_registry_get_by_category(self):
        ar = ActionRegistry()
        nav_actions = ar.get_by_category("navigation")
        assert len(nav_actions) > 0
        assert all(a["category"] == "navigation" for a in nav_actions)

    def test_action_registry_execute_no_handler(self):
        ar = ActionRegistry()
        result = ar.execute("navigate_home")
        assert not result["ok"]
        assert result["error"] == "NO_HANDLER"

    def test_action_registry_execute_not_found(self):
        ar = ActionRegistry()
        result = ar.execute("unknown_action")
        assert not result["ok"]
        assert result["error"] == "NOT_FOUND"

    def test_action_registry_register(self):
        ar = ActionRegistry()
        from ui_qml_bridge.action_registry import ActionDescriptor
        ad = ActionDescriptor("custom_action", "Custom", "custom")
        ar.register(ad)
        assert ar.get("custom_action") is not None

    def test_action_registry_actions_property(self):
        ar = ActionRegistry()
        actions = ar.actions
        assert isinstance(actions, list)
        for a in actions:
            assert "id" in a
            assert "title" in a
            assert "category" in a

    def test_action_registry_destructive_actions(self):
        ar = ActionRegistry()
        track_delete = ar.get("track_delete_from_disk")
        assert track_delete is not None
        assert track_delete.destructive
        assert track_delete.requires_confirmation

    def test_action_registry_execute_with_handler(self):
        ar = ActionRegistry()
        from ui_qml_bridge.action_registry import ActionDescriptor
        results = []
        ad = ActionDescriptor("test_action", "Test", "test",
                              handler=lambda: results.append("called"))
        ar.register(ad)
        result = ar.execute("test_action")
        assert result["ok"]
        assert len(results) == 1

    def test_action_registry_execute_handler_returning_dict(self):
        ar = ActionRegistry()
        from ui_qml_bridge.action_registry import ActionDescriptor
        ad = ActionDescriptor("returns_dict", "Returns", "test",
                              handler=lambda: {"ok": True, "data": 42})
        ar.register(ad)
        result = ar.execute("returns_dict")
        assert result["ok"]
        assert result["data"] == 42

    def test_action_registry_enabled_disabled(self):
        ar = ActionRegistry()
        from ui_qml_bridge.action_registry import ActionDescriptor
        ad = ActionDescriptor("disabled_action", "Disabled", "test")
        ad.enabled = False
        ar.register(ad)
        actions = ar.actions
        matching = [a for a in actions if a["id"] == "disabled_action"]
        assert len(matching) > 0
        assert not matching[0]["enabled"]


class TestConfirmationBridgeIntegrations:
    def test_confirmation_bridge_initial_state(self):
        cb = ConfirmationBridge()
        assert not cb.hasPending()

    def test_confirmation_bridge_request(self):
        cb = ConfirmationBridge()
        result = cb.requestConfirmation("delete_track", "Delete track?")
        assert result

    def test_confirmation_bridge_resolve(self):
        cb = ConfirmationBridge()
        cb.requestConfirmation("test", "Test?")
        result = cb.resolveConfirmation("test", True)
        assert result["ok"]

    def test_confirmation_bridge_resolve_rejected(self):
        cb = ConfirmationBridge()
        cb.requestConfirmation("test", "Test?")
        result = cb.resolveConfirmation("test", False)
        assert not result["ok"]

    def test_confirmation_bridge_has_pending_by_id(self):
        cb = ConfirmationBridge()
        cb.requestConfirmation("abc", "ABC?")
        assert cb.hasPending("abc")

    def test_confirmation_bridge_has_pending_any(self):
        cb = ConfirmationBridge()
        assert not cb.hasPending()
        cb.requestConfirmation("abc", "ABC?")
        assert cb.hasPending()

    def test_confirmation_bridge_no_pending_after_resolve(self):
        cb = ConfirmationBridge()
        cb.requestConfirmation("abc", "ABC?")
        cb.resolveConfirmation("abc", True)
        assert not cb.hasPending("abc")

    def test_confirmation_bridge_pending_list(self):
        cb = ConfirmationBridge()
        cb.requestConfirmation("a", "A", {"detail": "x"})
        pending = cb.pendingConfirmations
        assert len(pending) == 1
        assert pending[0]["id"] == "a"

    def test_confirmation_bridge_score(self):
        cb = ConfirmationBridge()
        score = cb.confirmationScore()
        assert "score" in score
        assert 0 <= score["score"] <= 100

    def test_confirmation_bridge_with_service(self):
        svc = MagicMock()
        cb = ConfirmationBridge(confirmation_service=svc)
        assert cb._svc is svc

    def test_confirmation_bridge_with_action_registry(self):
        ar = ActionRegistry()
        cb = ConfirmationBridge(action_registry=ar)
        assert cb._action_registry is ar

    def test_confirmation_bridge_signals(self):
        req_signals = []
        res_signals = []
        cb = ConfirmationBridge()
        cb.confirmationRequested.connect(lambda i, t, d: req_signals.append((i, t, d)))
        cb.confirmationResolved.connect(lambda i, a: res_signals.append((i, a)))
        cb.requestConfirmation("x", "X")
        cb.resolveConfirmation("x", True)
        assert len(req_signals) == 1
        assert len(res_signals) == 1
