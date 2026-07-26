from __future__ import annotations
"""CQ — Michi AI + Diagnostics + Command Palette.
Michi AI después de Diagnostics. Acciones via ActionRegistry. Sin handler: ACTION_UNAVAILABLE.
Diagnostics: snapshots, services, jobs, logs, DB health, playback health, export, async.
Command Palette: actions, routes, tracks, settings, devices, capability filtering, keyboard.
"""

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.michi_ai_bridge import MichiAIBridge
from ui_qml_bridge.diagnostics_bridge import DiagnosticsBridge
from ui_qml_bridge.command_palette_bridge import CommandPaletteBridge
from ui_qml_bridge.action_registry import ActionRegistry

pytestmark = pytest.mark.isolation


# ── Michi AI ──

class TestMichiAI:
    @pytest.fixture
    def mocks(self) -> None:
        return {
            "michi_ai_service": MagicMock(),
            "action_registry": MagicMock(),
            "navigation_bridge": MagicMock(),
        }

    @pytest.fixture
    def bridge(self, mocks) -> None:
        svc = mocks["michi_ai_service"]
        svc.process_message.return_value = {"ok": True, "response": "OK"}
        return MichiAIBridge(
            michi_ai_service=svc,
            action_registry=mocks["action_registry"],
            navigation_bridge=mocks["navigation_bridge"],
        )

    def test_initial_state(self, bridge) -> None:
        assert bridge.status == "IDLE"
        assert bridge.lastError == ""

    def test_refresh(self, bridge) -> None:
        bridge.refresh()

    def test_cancel(self, bridge) -> None:
        bridge.cancel()
        assert bridge.status == "CANCELLED"

    def test_send_message_unknown(self, bridge, mocks) -> None:
        mocks["michi_ai_service"].process_message.return_value = {
            "ok": False, "response": "No entendí"
        }
        bridge.sendMessage("xyzzy unknown command")
        assert len(bridge._chat_history) >= 1

    def test_send_message_reproducir(self, bridge, mocks) -> None:
        mocks["michi_ai_service"].process_message.return_value = {
            "ok": True, "response": "Reproduciendo..."
        }
        bridge.sendMessage("reproduce canción 1")
        assert bridge.status == "SUCCEEDED"

    def test_send_message_buscar(self, bridge, mocks) -> None:
        mocks["michi_ai_service"].process_message.return_value = {
            "ok": True, "response": "Resultados encontrados"
        }
        bridge.sendMessage("buscar rock")
        assert bridge.status == "SUCCEEDED"

    def test_send_message_abrir_ruta(self, bridge, mocks) -> None:
        mocks["michi_ai_service"].process_message.return_value = {
            "ok": True, "response": "Navegando..."
        }
        bridge.sendMessage("ir a biblioteca")
        assert bridge.status == "SUCCEEDED"

    def test_send_message_crear_playlist(self, bridge, mocks) -> None:
        mocks["michi_ai_service"].process_message.return_value = {
            "requires_confirmation": True, "intent": "crear playlist"
        }
        bridge.sendMessage("crear playlist llamada Favoritas")
        assert bridge.status == "CONFIRMATION_REQUIRED"

    def test_confirm_action(self, bridge, mocks) -> None:
        bridge._pending_action = {"intent": "crear playlist", "entities": {}}
        mocks["michi_ai_service"].process_message.return_value = {
            "ok": True, "response": "Playlist creada."
        }
        bridge.sendMessage("sí")

    def test_cancel_action(self, bridge, mocks) -> None:
        bridge._pending_action = {"intent": "test", "entities": {}}
        bridge.cancel()
        assert bridge._pending_action is None
        assert bridge.status == "CANCELLED"

    def test_diagnostic_action(self, bridge, mocks) -> None:
        mocks["michi_ai_service"].process_message.return_value = {
            "ok": True, "response": "Diagnóstico completo."
        }
        bridge.sendMessage("diagnosticar biblioteca")
        assert bridge.status == "SUCCEEDED"

    def test_ai_score(self, bridge) -> None:
        score = bridge.aiScore()
        assert "score" in score
        assert score["score"] >= 0

    def test_get_chat_history(self, bridge) -> None:
        history = bridge.getChatHistory()
        assert isinstance(history, str)

    def test_abrir_ajustes(self, bridge, mocks) -> None:
        mocks["michi_ai_service"].process_message.return_value = {
            "ok": True, "response": "Abriendo ajustes..."
        }
        bridge.sendMessage("abrir ajustes")
        assert bridge.status == "SUCCEEDED"


# ── Diagnostics ──

class TestDiagnostics:
    @pytest.fixture
    def wm(self) -> None:
        wm = MagicMock()
        wm.run_task.return_value = MagicMock()
        return wm

    @pytest.fixture
    def ds(self) -> None:
        d = MagicMock()
        d.check_player_api.return_value = {"status": "ok", "api_version": "v1"}
        d.check_sync_server.return_value = {"status": "ok", "running": True}
        d.check_pairing.return_value = {"status": "ok", "paired": 1}
        d.check_playback.return_value = {"status": "ok", "state": "playing"}
        d.check_queue.return_value = {"status": "ok", "queue_length": 5}
        d.check_continue_readiness.return_value = {"status": "ready", "has_queue": True}
        return d

    @pytest.fixture
    def bridge(self, wm, ds) -> None:
        return DiagnosticsBridge(diagnostics_service=ds, worker_manager=wm)

    def test_initial_state(self, bridge) -> None:
        assert bridge.jobs == []

    def test_refresh_returns_ok(self, bridge, wm) -> None:
        result = bridge.refresh()
        assert result["ok"] is True

    def test_refresh_schedules_jobs(self, bridge, wm) -> None:
        bridge.refresh()
        assert wm.run_task.called

    def test_copy_diagnostics_returns_string(self, bridge) -> None:
        bridge._jobs = [{"status": "PASS", "id": "test", "message": "OK", "duration_ms": 10}]
        text = bridge.copyDiagnostics()
        assert "Michi Music Player Diagnostics" in text
        assert "PASS" in text

    def test_copy_with_empty_jobs(self, bridge) -> None:
        text = bridge.copyDiagnostics()
        assert text != ""

    def test_player_api_check(self, ds) -> None:
        bridge = DiagnosticsBridge(diagnostics_service=ds)
        result = bridge._check_player_api()
        assert result["status"] in ("PASS", "WARN", "FAIL")

    def test_sync_server_check(self, ds) -> None:
        bridge = DiagnosticsBridge(diagnostics_service=ds)
        result = bridge._check_sync_server()
        assert result["status"] in ("PASS", "WARN", "FAIL")

    def test_playback_check(self, ds) -> None:
        bridge = DiagnosticsBridge(diagnostics_service=ds, player_service=MagicMock())
        result = bridge._check_playback()
        assert result["status"] in ("PASS", "WARN", "FAIL")

    def test_storage_paths_check(self, bridge) -> None:
        result = bridge._check_storage_paths()
        assert result["status"] in ("FAIL", "PASS", "WARN")

    def test_services_check(self, bridge) -> None:
        result = bridge._check_services_availability()
        assert result["status"] in ("FAIL", "PASS", "WARN")
        assert "value" in result


# ── Command Palette ──

class TestCommandPalette:
    @pytest.fixture
    def registry(self) -> None:
        return ActionRegistry()

    @pytest.fixture
    def bridge(self, registry) -> None:
        return CommandPaletteBridge(action_registry=registry)

    def test_initial_commands(self, bridge) -> None:
        assert len(bridge.commands) >= 10

    def test_search_commands_empty_query(self, bridge) -> None:
        results = bridge.searchCommands("")
        assert len(results) >= 10

    def test_search_by_title(self, bridge) -> None:
        results = bridge.searchCommands("Inicio")
        assert len(results) >= 1
        assert any("Inicio" in r["title"] for r in results)

    def test_search_by_category(self, bridge) -> None:
        results = bridge.searchCommands("navigation")
        assert len(results) >= 1
        assert all(r["category"] == "navigation" or "navigation" in r["category"].lower() for r in results)

    def test_execute_unknown_command(self, bridge) -> None:
        result = bridge.executeCommand("nonexistent")
        assert result["ok"] is False

    def test_execute_registered_command_no_handler(self, bridge) -> None:
        result = bridge.executeCommand("navigate_home")
        assert result["ok"] is False

    def test_action_has_id(self, bridge) -> None:
        for cmd in bridge.commands:
            assert "id" in cmd

    def test_action_has_category(self, bridge) -> None:
        for cmd in bridge.commands:
            assert "category" in cmd

    def test_action_has_title(self, bridge) -> None:
        for cmd in bridge.commands:
            assert "title" in cmd

    def test_registry_actions_property(self, registry) -> None:
        assert len(registry.actions) >= 10

    def test_get_by_category(self, registry) -> None:
        nav = registry.get_by_category("navigation")
        assert len(nav) >= 5

    def test_register_new_action(self, registry) -> None:
        from ui_qml_bridge.action_registry import ActionDescriptor
        desc = ActionDescriptor("test_action", "Test Action", "testing", "test")
        registry.register(desc)
        assert registry.get("test_action") is not None

    def test_get_nonexistent(self, registry) -> None:
        assert registry.get("nonexistent") is None

    def test_actions_list_all_visible(self, registry) -> None:
        for a in registry.actions:
            assert a["visible"] is True

    def test_destructive_flag(self, registry) -> None:
        delete = registry.get("track_delete_from_disk")
        assert delete is not None
        assert delete.destructive is True
        assert delete.requires_confirmation is True
