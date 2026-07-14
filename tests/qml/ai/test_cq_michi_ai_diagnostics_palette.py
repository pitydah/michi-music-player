"""CQ — Michi AI + Diagnostics + Command Palette.

Michi AI después de Diagnostics. Acciones via ActionRegistry. Sin handler: ACTION_UNAVAILABLE.
Diagnostics: snapshots, services, jobs, logs, DB health, playback health, export, async.
Command Palette: actions, routes, tracks, settings, devices, capability filtering, keyboard.
"""
from __future__ import annotations

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
    def bridge(self):
        return MichiAIBridge(
            ai_controller=MagicMock(),
            context_service=MagicMock(),
            plan_builder=MagicMock(),
            tool_registry=MagicMock(),
            action_registry=MagicMock(),
            navigation_bridge=MagicMock(),
            track_action_service=MagicMock(),
            playlist_service=MagicMock(),
            global_search_service=MagicMock(),
            settings_service=MagicMock(),
            diagnostics_service=MagicMock(),
            worker_manager=MagicMock(),
        )

    def test_initial_state(self, bridge):
        assert bridge.status == "idle"
        assert bridge.lastError == ""

    def test_refresh(self, bridge):
        bridge.refresh()

    def test_cancel(self, bridge):
        bridge.cancel()
        assert bridge.status == "cancelled"

    def test_send_message_unknown(self, bridge):
        bridge.sendMessage("xyzzy unknown command")
        assert len(bridge._chat_history) >= 1

    def test_send_message_reproducir(self, bridge):
        bridge._track_action_service = MagicMock()
        bridge._track_action_service.play_track.return_value = {"ok": True}
        bridge.sendMessage("reproduce canción 1")
        assert bridge.status in ("completed", "executing")

    def test_send_message_buscar(self, bridge):
        bridge._global_search_service = MagicMock()
        bridge._global_search_service.search.return_value = {"ok": True, "count": 5}
        bridge.sendMessage("buscar rock")
        assert bridge.status in ("completed", "executing")

    def test_send_message_abrir_ruta(self, bridge):
        bridge._nav = MagicMock()
        bridge.sendMessage("ir a biblioteca")
        assert bridge.status in ("completed", "executing")

    def test_send_message_crear_playlist(self, bridge):
        bridge._playlist_service = MagicMock()
        bridge._playlist_service.create.return_value = {"ok": True}
        bridge.sendMessage("crear playlist llamada Favoritas")
        assert bridge.status == "awaiting_confirmation" or bridge.status in ("completed", "executing")

    def test_confirm_action(self, bridge):
        bridge._pending_action = {"name": "crear playlist", "description": "crear playlist", "_original": "crear playlist"}
        bridge._playlist_service = MagicMock()
        bridge._playlist_service.create.return_value = {"ok": True}
        bridge.sendMessage("sí")

    def test_cancel_action(self, bridge):
        bridge._pending_action = {"name": "test"}
        bridge.sendMessage("no")
        assert bridge._pending_action is None

    def test_diagnostic_action(self, bridge):
        bridge._diagnostics = MagicMock()
        bridge._diagnostics.runQuickCheck.return_value = {"ok": True}
        bridge.sendMessage("diagnosticar biblioteca")
        assert bridge.status in ("completed", "executing")

    def test_ai_score(self, bridge):
        score = bridge.aiScore()
        assert "score" in score
        assert score["score"] >= 0

    def test_get_chat_history(self, bridge):
        history = bridge.getChatHistory()
        assert isinstance(history, str)

    def test_abrir_ajustes(self, bridge):
        bridge._nav = MagicMock()
        bridge.sendMessage("abrir ajustes")
        assert bridge._nav.navigate.called


# ── Diagnostics ──

class TestDiagnostics:
    @pytest.fixture
    def wm(self):
        wm = MagicMock()
        wm.run_task.return_value = MagicMock()
        return wm

    @pytest.fixture
    def bridge(self, wm):
        return DiagnosticsBridge(worker_manager=wm)

    def test_initial_state(self, bridge):
        assert bridge.jobs == []

    def test_refresh_returns_ok(self, bridge, wm):
        result = bridge.refresh()
        assert result["ok"] is True

    def test_refresh_schedules_jobs(self, bridge, wm):
        bridge.refresh()
        assert wm.run_task.called

    def test_copy_diagnostics_returns_string(self, bridge):
        bridge._jobs = [{"status": "PASS", "id": "test", "message": "OK", "duration_ms": 10}]
        text = bridge.copyDiagnostics()
        assert "Michi Music Player Diagnostics" in text
        assert "PASS" in text

    def test_copy_with_empty_jobs(self, bridge):
        text = bridge.copyDiagnostics()
        assert text != ""

    def test_db_health_check(self, bridge):
        result = bridge._check_db_integrity()
        assert result["status"] in ("FAIL", "PASS", "WARN")

    def test_library_status_check(self, bridge):
        result = bridge._check_library_status()
        assert result["status"] in ("FAIL", "PASS", "WARN")

    def test_player_status_check(self):
        bridge = DiagnosticsBridge(player_service=MagicMock())
        result = bridge._check_player_status()
        assert result["status"] in ("FAIL", "PASS", "WARN")

    def test_storage_paths_check(self, bridge):
        result = bridge._check_storage_paths()
        assert result["status"] in ("FAIL", "PASS", "WARN")

    def test_services_check(self, bridge):
        result = bridge._check_services_availability()
        assert result["status"] in ("FAIL", "PASS", "WARN")
        assert "value" in result


# ── Command Palette ──

class TestCommandPalette:
    @pytest.fixture
    def registry(self):
        return ActionRegistry()

    @pytest.fixture
    def bridge(self, registry):
        return CommandPaletteBridge(action_registry=registry)

    def test_initial_commands(self, bridge):
        assert len(bridge.commands) >= 10

    def test_search_commands_empty_query(self, bridge):
        results = bridge.searchCommands("")
        assert len(results) >= 10

    def test_search_by_title(self, bridge):
        results = bridge.searchCommands("Inicio")
        assert len(results) >= 1
        assert any("Inicio" in r["title"] for r in results)

    def test_search_by_category(self, bridge):
        results = bridge.searchCommands("navigation")
        assert len(results) >= 1
        assert all(r["category"] == "navigation" or "navigation" in r["category"].lower() for r in results)

    def test_execute_unknown_command(self, bridge):
        result = bridge.executeCommand("nonexistent")
        assert result["ok"] is False

    def test_execute_registered_command_no_handler(self, bridge):
        result = bridge.executeCommand("navigate_home")
        assert result["ok"] is False

    def test_action_has_id(self, bridge):
        for cmd in bridge.commands:
            assert "id" in cmd

    def test_action_has_category(self, bridge):
        for cmd in bridge.commands:
            assert "category" in cmd

    def test_action_has_title(self, bridge):
        for cmd in bridge.commands:
            assert "title" in cmd

    def test_registry_actions_property(self, registry):
        assert len(registry.actions) >= 10

    def test_get_by_category(self, registry):
        nav = registry.get_by_category("navigation")
        assert len(nav) >= 5

    def test_register_new_action(self, registry):
        from ui_qml_bridge.action_registry import ActionDescriptor
        desc = ActionDescriptor("test_action", "Test Action", "testing", "test")
        registry.register(desc)
        assert registry.get("test_action") is not None

    def test_get_nonexistent(self, registry):
        assert registry.get("nonexistent") is None

    def test_actions_list_all_visible(self, registry):
        for a in registry.actions:
            assert a["visible"] is True

    def test_destructive_flag(self, registry):
        delete = registry.get("track_delete_from_disk")
        assert delete is not None
        assert delete.destructive is True
        assert delete.requires_confirmation is True
