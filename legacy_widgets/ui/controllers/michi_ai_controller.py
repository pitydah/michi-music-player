"""LEGACY - reemplazado por ui_qml_bridge correspondiente."""
from __future__ import annotations

"""MichiAIController — orchestrates Michi AI page, context, tools, and plans."""


import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject

from michi_ai.context.ai_context_bridge import MichiAIContextBridge
from michi_ai.context.ai_snapshot_service import MichiAISnapshotService
from michi_ai.context.ai_insight_service import MichiAIInsightService
from michi_ai.planner.plan_builder import PlanBuilder
from michi_ai.planner.plan_executor import PlanExecutor
from michi_ai.tools.tool_registry import ToolRegistry, ToolDef
from michi_ai.tools.tool_permissions import ToolPermission

if TYPE_CHECKING:
    from ui.window import MainWindow

logger = logging.getLogger("michi_ai.controller")


class MichiAIController(QObject):
    def __init__(self, window: MainWindow, context_service=None, parent=None):
        super().__init__(parent or window)
        self._win = window
        self._page = None
        self._context_svc = context_service
        self._bridge = MichiAIContextBridge(context_service=context_service)
        self._snapshot_svc = MichiAISnapshotService(context_service=context_service)
        self._insight_svc = MichiAIInsightService()
        self._tool_registry = ToolRegistry()
        self._plan_builder = PlanBuilder()
        self._plan_executor = PlanExecutor(self._tool_registry)
        self._register_tools()

    def _register_tools(self) -> None:
        from michi_ai.tools.library_tools import get_library_health, list_missing_metadata, search_library, summarize_current_selection
        from michi_ai.tools.playlist_tools import create_playlist_from_selection, queue_selection
        from michi_ai.tools.audio_lab_tools import get_audio_analysis_status, list_tracks_missing_features
        from michi_ai.tools.sync_tools import get_sync_status, list_sync_peers
        from michi_ai.tools.michi_link_tools import get_michi_link_status
        from michi_ai.tools.config_tools import list_config_plans, create_config_plan
        w = self._win
        tools = [
            ToolDef("get_library_health", "Obtener estado de la biblioteca", ToolPermission.READ_ONLY, fn=lambda **kw: get_library_health(db=getattr(w, "_db", None), **kw)),
            ToolDef("list_missing_metadata", "Listar metadatos incompletos", ToolPermission.READ_ONLY, fn=lambda **kw: list_missing_metadata(db=getattr(w, "_db", None), **kw)),
            ToolDef("search_library", "Buscar en la biblioteca", ToolPermission.READ_ONLY, fn=lambda **kw: search_library(db=getattr(w, "_db", None), **kw)),
            ToolDef("summarize_current_selection", "Resumir seleccion actual", ToolPermission.READ_ONLY, fn=lambda **kw: summarize_current_selection(db=getattr(w, "_db", None), **kw)),
            ToolDef("create_playlist_from_selection", "Crear playlist desde seleccion", ToolPermission.WRITES_METADATA, fn=lambda **kw: create_playlist_from_selection(db=getattr(w, "_db", None), **kw)),
            ToolDef("queue_selection", "Encolar seleccion", ToolPermission.SAFE_ACTION, fn=lambda **kw: queue_selection(db=getattr(w, "_db", None), playback=getattr(w, "_playback", None), **kw)),
            ToolDef("get_audio_analysis_status", "Estado del analisis de audio", ToolPermission.READ_ONLY, fn=lambda **kw: get_audio_analysis_status(db=getattr(w, "_db", None), **kw)),
            ToolDef("list_tracks_missing_features", "Canciones sin features acusticas", ToolPermission.READ_ONLY, fn=lambda **kw: list_tracks_missing_features(db=getattr(w, "_db", None), **kw)),
            ToolDef("get_sync_status", "Estado de la sincronizacion", ToolPermission.READ_ONLY, fn=lambda **kw: get_sync_status(sync_manager=getattr(w, "_sync_mgr", None), **kw)),
            ToolDef("list_sync_peers", "Listar dispositivos Sync", ToolPermission.READ_ONLY, fn=lambda **kw: list_sync_peers(sync_manager=getattr(w, "_sync_mgr", None), **kw)),
            ToolDef("get_michi_link_status", "Estado de Michi Link", ToolPermission.READ_ONLY, fn=lambda **kw: get_michi_link_status(michi_link_ctrl=getattr(w, "_michi_link_ctrl", None), **kw)),
            ToolDef("list_config_plans", "Listar planes de configuracion", ToolPermission.READ_ONLY, fn=lambda **kw: list_config_plans(planner=getattr(w, "_config_planner", None), **kw)),
            ToolDef("create_config_plan", "Crear plan de configuracion", ToolPermission.CONFIG_CHANGE, fn=lambda **kw: create_config_plan(planner=getattr(w, "_config_planner", None), **kw)),
        ]
        for t in tools:
            self._tool_registry.register(t)
        logger.info("Registered %d Michi AI tools", len(tools))

    def _ensure_page(self):
        if self._page is None:
            from michi_ai.ui.michi_ai_page import MichiAIPage
            self._page = MichiAIPage()
            self._page.navigation_requested.connect(self._win._on_sidebar_navigate)
            self._page.tool_requested.connect(self._on_tool_requested)
        return self._page

    def show(self):
        page = self._ensure_page()
        w = self._win
        if not w._views.widget("michi_ai"):
            w._views.register("michi_ai", page)
        self.refresh()
        w._fade_content("michi_ai")
        self._bridge._record("michi_ai_opened")

    def refresh(self):
        page = self._page
        if page is None:
            return
        try:
            snapshot = self._snapshot_svc.build_snapshot()
            page.set_snapshot(snapshot)
            w = self._win
            insights = self._insight_svc.generate(snapshot, audio_intel=None, db=getattr(w, "_db", None))
            page.set_insights(insights)
            actions = [i for i in insights if i.get("suggested_action")]
            page.set_actions(actions)
        except Exception:
            logger.exception("Michi AI refresh failed")

    def execute_tool(self, tool_name: str, params: dict | None = None, confirmed: bool = False):
        result = self._tool_registry.execute(tool_name, params, confirmed=confirmed)
        self._bridge.record_tool_result(tool_name, result.ok)
        return result

    def _on_tool_requested(self, tool_name: str, params: dict):
        self.execute_tool(tool_name, params)
