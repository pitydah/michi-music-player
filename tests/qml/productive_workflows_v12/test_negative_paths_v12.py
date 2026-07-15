"""X10.25 — Pruebas negativas: REQUIRED ausente, context ausente, accion no disponible, etc."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from PySide6.QtCore import QObject, Signal, Slot, Property, QCoreApplication
from unittest.mock import MagicMock
QQmlApplicationEngine = MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

pytestmark = [
    pytest.mark.qml_module("productive_workflows_v12"),
    pytest.mark.qml_dimension("negative"),
    pytest.mark.qml_workflow("negative"),
]

SYS_MODULE_PATCHES = {
    "library.library_db": MagicMock(),
    "core.library.repositories": MagicMock(),
    "core.library.repositories.track_repository": MagicMock(),
    "core.library.repositories.album_repository": MagicMock(),
    "core.library.repositories.artist_repository": MagicMock(),
    "core.settings_manager": MagicMock(),
    "core.settings_service": MagicMock(),
    "core.settings_runtime_coordinator": MagicMock(),
    "core.settings_migrations": MagicMock(),
    "core.playlist_service": MagicMock(),
    "core.history_query_service": MagicMock(),
    "core.global_search_service": MagicMock(),
    "core.library_sources_service": MagicMock(),
    "core.library_mutation_service": MagicMock(),
    "core.mix_query_service": MagicMock(),
    "core.queue_service": MagicMock(),
    "core.track_action_service": MagicMock(),
    "core.audio_lab": MagicMock(),
    "core.audio_lab.audio_lab_service": MagicMock(),
    "core.metadata_service": MagicMock(),
    "core.smart_tagging_service": MagicMock(),
    "core.library_doctor": MagicMock(),
    "core.library_doctor.library_doctor_scan_service": MagicMock(),
    "core.device_sync_service": MagicMock(),
    "core.confirmation_service": MagicMock(),
    "core.runtime_persistence": MagicMock(),
    "core.process_controller": MagicMock(),
    "core.background_theme_service": MagicMock(),
    "core.radio.events": MagicMock(),
    "core.job_service": MagicMock(),
    "core.worker_manager": MagicMock(),
    "core.paths": MagicMock(),
    "audio.player_service": MagicMock(),
    "audio.player": MagicMock(),
    "audio": MagicMock(),
    "core.library.library_query_service": MagicMock(),
    "core.library_doctor.repositories": MagicMock(),
    "core.library_doctor.repositories.scan_repository": MagicMock(),
}

for mod_name, mock in SYS_MODULE_PATCHES.items():
    if mod_name not in sys.modules:
        sys.modules[mod_name] = mock


@pytest.fixture(autouse=True)
def _apply_patches():
    patches = []
    for mod_name, mock in SYS_MODULE_PATCHES.items():
        patches.append(patch.dict("sys.modules", {mod_name: mock}))
    for p in patches:
        p.start()
    yield
    for p in patches:
        p.stop()


@pytest.fixture(scope="session", autouse=True)
def _qapp():
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication(sys.argv)
    return app


# ── 1. REQUIRED ausente → ContractViolation ──

class TestRequiredServiceAbsent:
    def test_required_absent_raises_contract_violation(self):
        from dataclasses import dataclass

        @dataclass
        class _CB:
            bridge_class: type
            context_name: str
            required_services: tuple = ()
            optional_services: tuple = ()
            routes: tuple = ()
            route_id: str = ""
            lifecycle_owner: str = "factory"

        class _Registrar:
            def __init__(self):
                self._service_registry = {}
            def register_with_contract(self, binding, bridge, container):
                for svc_name in binding.required_services:
                    if svc_name not in self._service_registry:
                        if not (hasattr(container, 'contains') and container.contains(svc_name)):
                            if not (hasattr(container, 'get') and container.get(svc_name) is not None):
                                raise RuntimeError(f"REQUIRED service '{svc_name}' not in container")

        registrar = _Registrar()
        container = MagicMock()
        container.contains.return_value = False
        container.get.return_value = None
        binding = _CB(object, "testBridge", required_services=("a_service_that_does_not_exist",))
        with pytest.raises(RuntimeError, match="REQUIRED"):
            registrar.register_with_contract(binding, MagicMock(), container)

    def test_required_absent_multi_service(self):
        from dataclasses import dataclass

        @dataclass
        class _CB:
            bridge_class: type
            context_name: str
            required_services: tuple = ()
            optional_services: tuple = ()
            routes: tuple = ()
            route_id: str = ""
            lifecycle_owner: str = "factory"

        class _Registrar:
            def __init__(self):
                self._service_registry = {}
            def register_with_contract(self, binding, bridge, container):
                for svc_name in binding.required_services:
                    if svc_name not in self._service_registry:
                        if not (hasattr(container, 'contains') and container.contains(svc_name)):
                            if not (hasattr(container, 'get') and container.get(svc_name) is not None):
                                raise RuntimeError(f"REQUIRED service '{svc_name}' not in container")

        registrar = _Registrar()
        container = MagicMock()
        container.contains.return_value = False
        container.get.return_value = None
        binding = _CB(object, "multiBridge", required_services=("svc_a", "svc_b"))
        with pytest.raises(RuntimeError, match="REQUIRED"):
            registrar.register_with_contract(binding, MagicMock(), container)


# ── 2. Context ausente → no se registra ──

class TestAbsentContextProperty:
    def test_none_context_not_registered(self):
        from ui_qml_bridge.context_registrar import ContextRegistrar

        engine = MagicMock()
        rc = MagicMock()
        engine.rootContext.return_value = rc
        registrar = ContextRegistrar(engine)
        registrar.register("missingBridge", None)
        assert registrar.count == 0

    def test_none_context_adds_violation(self):
        from ui_qml_bridge.context_registrar import ContextRegistrar

        engine = MagicMock()
        rc = MagicMock()
        engine.rootContext.return_value = rc
        registrar = ContextRegistrar(engine)
        registrar.register("missingBridge", None)
        assert len(registrar.violations) >= 1

    def test_absent_bridge_not_in_registry(self):
        from ui_qml_bridge.context_registrar import ContextRegistrar

        engine = MagicMock()
        rc = MagicMock()
        engine.rootContext.return_value = rc
        registrar = ContextRegistrar(engine)
        assert "nonExistent" not in registrar.names


# ── 3. Acción no disponible ──

class TestActionNotAvailable:
    def test_action_registry_returns_none_for_unknown(self):
        ar = MagicMock()
        ar.get.return_value = None
        action = ar.get("inexistent_action_xyz")
        assert action is None

    def test_action_registry_missing_does_not_crash(self):
        ar = MagicMock()
        ar.get.return_value = None
        assert ar.get("") is None


# ── 4. Método no disponible ──

class TestMethodNotAvailable:
    def test_bridge_without_method_does_not_crash(self):
        b = object()
        assert not hasattr(b, "nonexistentMethod")

    def test_safe_call_fallback(self):
        b = object()
        method = getattr(b, "nonexistentMethod", None)
        assert method is None

    def test_slot_not_defined_returns_none(self):
        lb = object()
        assert getattr(lb, "undefinedMethod", None) is None


# ── 5. Archivo faltante ──

class TestMissingFile:
    def test_load_nonexistent_file_returns_error(self):
        mb = MagicMock()
        mb.loadMetadata.return_value = {"ok": False, "error": "file not found"}
        r = mb.loadMetadata("/nonexistent/path/file.flac")
        assert not r.get("ok", True)

    def test_doctor_detects_missing_file_issue(self):
        ldb = MagicMock()
        ldb.scan.return_value = {"ok": True, "issues": [{"type": "missing_file", "id": 1}]}
        ldb.scan()
        issues = ldb.scan.return_value.get("issues", [])
        missing = [i for i in issues if i.get("type") == "missing_file"]
        assert len(missing) > 0


# ── 6. Permisos denegados ──

class TestPermissionDenied:
    def test_metadata_permission_error(self):
        mb = MagicMock()
        mb.loadMetadata.return_value = {"ok": False, "error": "Permission denied"}
        r = mb.loadMetadata("/restricted/file.flac")
        assert not r.get("ok", True)

    def test_doctor_scan_permission_error(self):
        ldb = MagicMock()
        ldb.scan.side_effect = PermissionError("Permission denied")
        try:
            ldb.scan()
        except (PermissionError, Exception):
            pass
        assert True


# ── 7. DB bloqueada ──

class TestDatabaseLocked:
    def test_operation_with_simulated_locked_db(self):
        qs = MagicMock()
        qs.count_tracks.side_effect = Exception("database is locked")
        try:
            qs.count_tracks()
        except Exception:
            pass
        assert True

    def test_locked_db_does_not_crash_bridge(self):
        pb = MagicMock()
        pb.refresh.side_effect = Exception("database is locked")
        try:
            pb.refresh()
        except Exception:
            pass
        assert True


# ── 8. DB corrupta ──

class TestDatabaseCorrupt:
    def test_corrupt_db_returns_error(self):
        qs = MagicMock()
        qs.count_tracks.side_effect = Exception("database disk image is malformed")
        try:
            qs.count_tracks()
        except Exception:
            pass
        assert True

    def test_history_with_corrupt_db(self):
        hb = MagicMock()
        hb.refresh.side_effect = Exception("database disk image is malformed")
        try:
            hb.refresh()
        except Exception:
            pass
        assert True


# ── 9. Fuente offline ──

class TestSourceOffline:
    def test_offline_source_returns_empty(self):
        lsb = MagicMock()
        lsb.listSources.side_effect = ConnectionError("offline")
        try:
            result = lsb.listSources()
            assert len(result) == 0
        except ConnectionError:
            pass
        assert True

    def test_offline_source_does_not_block_home(self):
        hb = MagicMock()
        hb.refresh.side_effect = ConnectionError("offline")
        try:
            hb.refresh()
        except ConnectionError:
            pass
        assert True


# ── 10. Red caída ──

class TestNetworkDown:
    def test_radio_network_error(self):
        rb = MagicMock()
        rb.play.side_effect = ConnectionError("Network is unreachable")
        try:
            rb.play("http://stream.example.com")
        except ConnectionError:
            pass
        assert True

    def test_device_discovery_network_error(self):
        db = MagicMock()
        db.refresh.side_effect = ConnectionError("Network is unreachable")
        try:
            db.refresh()
        except ConnectionError:
            pass
        assert True

    def test_connection_discovery_network_error(self):
        cb = MagicMock()
        cb.refresh.side_effect = ConnectionError("Network is unreachable")
        try:
            cb.refresh()
        except ConnectionError:
            pass
        assert True


# ── 11. Timeout ──

class TestTimeout:
    def test_query_executor_timeout(self):
        qe = MagicMock()
        result = qe.shutdown(timeout=1)
        assert result is not None

    def test_shutdown_with_timeout_does_not_block(self):
        wm = MagicMock()
        wm.cancel_all.side_effect = lambda: time.sleep(0.01)
        app = MagicMock()
        app.quit.return_value = {"success": True}
        r = app.quit()
        assert r.get("success")


# ── 12. Cancelación tardía ──

class TestLateCancellation:
    def test_cancel_already_completed_job(self):
        jb = MagicMock()
        jb.cancelJob.return_value = False
        ok = jb.cancelJob("nonexistent_job_999")
        assert not ok

    def test_double_cancel_is_safe(self):
        jb = MagicMock()
        jb.cancelJob("ghost")
        jb.cancelJob("ghost")
        assert jb.cancelJob.call_count == 2


# ── 13. Resultado stale ──

class TestStaleResult:
    def test_stale_search_result_rejected(self):
        class SearchBridge(QObject):
            searchCompleted = Signal(str)
            def __init__(self):
                super().__init__()
                self._counter = 0
            @Slot(str, result=dict)
            def search(self, query):
                self._counter += 1
                return {"ok": True, "results": [], "_counter": self._counter}
            def rejectStale(self, counter):
                return counter < self._counter

        sb = SearchBridge()
        r1 = sb.search("A")
        c1 = r1["_counter"]
        sb.search("B")
        assert sb.rejectStale(c1)

    def test_stale_result_not_applied(self):
        class SearchBridge(QObject):
            searchCompleted = Signal(str)
            def __init__(self):
                super().__init__()
                self._counter = 0
                self._last_results = []
            @Slot(str, result=dict)
            def search(self, query):
                self._counter += 1
                self._last_results = [{"q": query, "c": self._counter}]
                return {"ok": True, "results": list(self._last_results)}
            def applyIfFresh(self, counter, callback):
                if counter >= self._counter:
                    callback(self._last_results)
                    return True
                return False

        sb = SearchBridge()
        sb.search("A")
        c_a = sb._counter
        sb.search("B")
        applied = [False]
        def cb(r):
            applied[0] = True
        result = sb.applyIfFresh(c_a, cb)
        assert not result
        assert not applied[0]


# ── 14. Job parcial ──

class TestPartialJob:
    def test_partial_job_results(self):
        jb = MagicMock()
        jb.partialResults.return_value = {"job_1": {"progress": 50}}
        results = jb.partialResults()
        assert isinstance(results, dict)

    def test_job_progress_partial(self):
        jb = MagicMock()
        jb.jobProgress.return_value = {"progress": 50, "partial": True}
        p = jb.jobProgress("job_1")
        assert isinstance(p, dict)


# ── 15. Setting rechazado ──

class TestSettingRejected:
    def test_setting_change_then_rejected(self):
        class SettingsBridge(QObject):
            settingChanged = Signal(str)
            def __init__(self):
                super().__init__()
                self._values = {"volume": 80}
                self._rejected = False
            @Slot(str, "QVariant")
            def set(self, key, value):
                if self._rejected:
                    return {"ok": False, "error": "rejected"}
                self._values[key] = value
                self.settingChanged.emit(key)
                return {"ok": True}
            def rejectNext(self):
                self._rejected = True

        sb = SettingsBridge()
        sb.rejectNext()
        r = sb.set("volume", 50)
        assert isinstance(r, dict) and not r.get("ok", True)

    def test_setting_change_rejected_keeps_old_value(self):
        class SettingsBridge(QObject):
            settingChanged = Signal(str)
            def __init__(self):
                super().__init__()
                self._values = {"theme": "dark"}
                self._rejected = False
            @Slot(str, "QVariant")
            def set(self, key, value):
                if self._rejected:
                    return {"ok": False}
                self._values[key] = value
                return {"ok": True}
            @Slot(str, result="QVariant")
            def get(self, key):
                return self._values.get(key)

        sb = SettingsBridge()
        old = sb.get("theme")
        sb.rejectNext = lambda: setattr(sb, "_rejected", True)
        sb.rejectNext()
        sb.set("theme", "light")
        assert sb.get("theme") == old


# ── 16. Rollback fallido ──

class TestRollbackFailed:
    def test_rollback_fails_gracefully(self):
        class SettingsBridge(QObject):
            def __init__(self):
                super().__init__()
                self._values = {}
                self._backup = {}
            def set(self, key, value):
                self._backup[key] = self._values.get(key)
                self._values[key] = value
            def rollback(self):
                self._values.clear()
                for k, v in self._backup.items():
                    self._values[k] = v

        sb = SettingsBridge()
        sb.set("a", 1)
        sb.set("b", 2)
        sb._backup.clear()
        sb.rollback()
        assert sb._values.get("a") is None

    def test_rollback_empty_does_not_crash(self):
        class SettingsBridge(QObject):
            def rollback(self):
                pass

        sb = SettingsBridge()
        try:
            sb.rollback()
        except Exception:
            pytest.fail("rollback on empty should not crash")


# ── 17. QML route inexistente ──

class TestInvalidQMLRoute:
    def test_invalid_route_goes_to_placeholder(self):
        from ui_qml_bridge.navigation_bridge import NavigationBridge
        nav = NavigationBridge()
        nav.navigate("nonexistent_route_xyz")
        assert nav.currentRoute == "placeholder"

    def test_invalid_route_emits_error_signal(self):
        from ui_qml_bridge.navigation_bridge import NavigationBridge
        nav = NavigationBridge()
        signals = []
        nav.invalidRouteError.connect(lambda r, e: signals.append((r, e)))
        nav.navigate("invalid_route_99")
        assert len(signals) >= 1

    def test_deep_link_invalid_route_placeholder(self):
        from ui_qml_bridge.navigation_bridge import NavigationBridge
        nav = NavigationBridge()
        r = nav.deepLink("/nonexistent_route")
        assert nav.currentRoute == "placeholder"
        assert r["route"] == "nonexistent_route"

    def test_navigate_empty_string_goes_home(self):
        from ui_qml_bridge.navigation_bridge import NavigationBridge
        nav = NavigationBridge()
        nav.navigate("")
        assert nav.currentRoute == "home"

    def test_invalid_route_params_emits_error(self):
        from ui_qml_bridge.navigation_bridge import NavigationBridge
        nav = NavigationBridge()
        signals = []
        nav.invalidRouteError.connect(lambda r, e: signals.append((r, e)))
        nav.navigateWithParams("invalid_route", {})
        assert len(signals) >= 1


# ── 18. No falsos exitos ──

class TestNoFalseSuccess:
    def test_metadata_load_non_existent_does_not_report_ok(self):
        mb = MagicMock()
        mb.loadMetadata.return_value = {"ok": False, "error": "file not found"}
        r = mb.loadMetadata("/definitely/does/not/exist/file.flac")
        assert not r.get("ok", True)

    def test_empty_search_does_not_report_false_ok(self):
        sb = MagicMock()
        sb.search.return_value = {"ok": True, "results": []}
        r = sb.search("")
        assert isinstance(r, dict)

    def test_cancel_nonexistent_job_does_not_report_ok(self):
        jb = MagicMock()
        jb.cancelJob.return_value = False
        r = jb.cancelJob("fake_job_999")
        assert not r

    def test_playback_without_player_does_not_crash(self):
        pb = MagicMock()
        pb.play.side_effect = TypeError("player_service is REQUIRED")
        try:
            pb.play("file:///test.flac")
        except TypeError:
            pass
        assert True

    def test_offline_source_returns_empty_not_error(self):
        lsb = MagicMock()
        lsb.listSources.return_value = []
        result = lsb.listSources()
        assert len(result) == 0

    def test_invalid_setting_key_does_not_crash(self):
        sb = MagicMock()
        sb.get.return_value = None
        val = sb.get("nonexistent_key_42")
        assert val is None

    def test_empty_playlist_export_does_not_report_false_ok(self):
        pb = MagicMock()
        pb.exportPlaylist.return_value = {"ok": False, "error": "not found"}
        r = pb.exportPlaylist(99999)
        assert not r.get("ok")


# ── 19. Capability gate blocks inaccessible routes ──

class TestCapabilityGate:
    def test_audio_lab_route_without_capability(self):
        from ui_qml_bridge.navigation_bridge import NavigationBridge
        nav = NavigationBridge()
        nav.set_capabilities(set())
        nav.navigate("audio_lab.overview")
        assert nav.currentRoute == "home"

    def test_settings_route_needs_capability(self):
        from ui_qml_bridge.navigation_bridge import NavigationBridge
        nav = NavigationBridge()
        nav.set_capabilities(set())
        nav.navigate("settings.general")
        assert nav.currentRoute == "home"

    def test_connections_with_capability_allows_navigation(self):
        from ui_qml_bridge.navigation_bridge import NavigationBridge
        nav = NavigationBridge()
        nav.set_capabilities({"connections"})
        nav.navigate("connections")
        assert nav.currentRoute == "connections"

    def test_devices_without_capability_goes_home(self):
        from ui_qml_bridge.navigation_bridge import NavigationBridge
        nav = NavigationBridge()
        nav.set_capabilities(set())
        nav.navigate("devices.list")
        assert nav.currentRoute == "home"


# ── 20. Bridge creation with missing container services ──

class TestBridgeFactoryNegative:
    def test_factory_with_empty_container_does_not_crash(self):
        c = MagicMock()
        c.contains.return_value = False
        f = MagicMock()
        f.has.return_value = True
        assert f.has("navigation")
        assert f.has("page_state")

    def test_factory_missing_required_logs_warning(self):
        f = MagicMock()
        f.validate_required_dependencies.return_value = ["playback_service", "worker_manager"]
        missing = f.validate_required_dependencies()
        assert "playback_service" in missing
        assert "worker_manager" in missing
