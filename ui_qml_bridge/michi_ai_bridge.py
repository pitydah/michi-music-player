from __future__ import annotations

import json
import logging

from PySide6.QtCore import QObject, Signal, Property, Slot

from ui_qml_bridge.action_registry import ActionRegistry
from ui_qml_bridge.navigation_bridge import NavigationBridge
from ui_qml_bridge.capability_bridge import CapabilityBridge
from ui_qml_bridge.page_state_store import PageStateStore
from ui_qml_bridge.accessibility_bridge import AccessibilityBridge

logger = logging.getLogger("michi.ai.bridge")

AI_STATES = frozenset({
    "IDLE", "PLANNING", "CONFIRMATION_REQUIRED", "QUEUED", "RUNNING",
    "CANCELLING", "CANCELLED", "SUCCEEDED", "PARTIAL_SUCCESS", "FAILED",
})


class MichiAIBridge(QObject):
    contextChanged = Signal()
    responseReceived = Signal(str)
    statusChanged = Signal(str)
    backendChanged = Signal()
    downloadProgressChanged = Signal()

    def __init__(
        self,
        michi_ai_service=None,
        job_service=None,
        confirmation_service=None,
        device_sync_service=None,
        action_registry: ActionRegistry | None = None,
        navigation_bridge: NavigationBridge | None = None,
        capability_bridge: CapabilityBridge | None = None,
        page_state_store: PageStateStore | None = None,
        accessibility_bridge: AccessibilityBridge | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._dev_svc = device_sync_service
        self._ai_svc = michi_ai_service
        self._ai_engine = michi_ai_service
        self._job_svc = job_service
        self._confirm_svc = confirmation_service
        self._registry = action_registry or ActionRegistry()
        self._nav = navigation_bridge
        self._cap_bridge = capability_bridge
        self._page_state = page_state_store
        self._access = accessibility_bridge

        if michi_ai_service is None:
            logger.warning("MichiAIBridge created WITHOUT michi_ai_service — AI features unavailable")
        else:
            logger.info("MichiAIBridge created with michi_ai_service=%s", type(michi_ai_service).__name__)

        self._status = "IDLE"
        self._suggestions: list[dict] = []
        self._backend_type: str = "calico"
        self._model_status: str = "not_installed"
        self._download_progress: float = 0.0
        self._ram_usage_mb: int = 0
        self._chat_history: list[dict] = []
        self._pending_action: dict | None = None
        self._last_error = ""
        self._current_task_id = ""
        self._session_id = "default"
        self._current_plan: dict = {}
        self._last_trace: dict = {}

    @Property(bool, notify=statusChanged)
    def backendAvailable(self) -> bool:
        return self._ai_svc is not None

    @Property(str, notify=statusChanged)
    def status(self):
        return self._status

    def _set_status(self, new: str):
        if new in AI_STATES and new != self._status:
            self._status = new
            self.statusChanged.emit(new)

    @Property(str, notify=contextChanged)
    def lastError(self):
        return self._last_error

    @Property(str, notify=backendChanged)
    def backendType(self):
        return self._backend_type

    @Property(str, notify=backendChanged)
    def modelStatus(self):
        return self._model_status

    @Property(float, notify=downloadProgressChanged)
    def downloadProgress(self):
        return self._download_progress

    @Property(int, notify=backendChanged)
    def ramUsageMb(self):
        return self._ram_usage_mb

    @Property("QVariantList", notify=contextChanged)
    def suggestions(self):
        return self._suggestions

    @Property("QVariantList", notify=contextChanged)
    def capabilities(self) -> list[dict]:
        """Real capabilities the assistant can use right now."""
        return self._build_capabilities()

    def _build_capabilities(self) -> list[dict]:
        caps: list[dict] = []
        registry = getattr(self._ai_engine, "tool_registry", None)
        tools = getattr(registry, "_tools", None)
        if isinstance(tools, dict) and tools:
            grouped: dict[str, int] = {}
            for defn in tools.values():
                for tag in getattr(defn, "tags", ()) or ("general",):
                    grouped[tag] = grouped.get(tag, 0) + 1
            for tag in sorted(grouped):
                caps.append({"area": tag, "tool_count": grouped[tag], "available": True})
        if self._cap_bridge is not None:
            try:
                states = self._cap_bridge.capabilities
                unavailable = sorted(k for k, v in states.items() if v != "available")
                if unavailable:
                    caps.append({"area": "limitado", "tool_count": 0,
                                 "available": False, "detail": ", ".join(unavailable[:6])})
            except Exception:
                logger.debug("capability bridge read failed", exc_info=True)
        return caps

    @Property("QVariantMap", notify=contextChanged)
    def currentPlan(self) -> dict:
        """Plan/intent of the action being planned or awaiting confirmation."""
        return dict(self._current_plan)

    @Property("QVariantMap", notify=contextChanged)
    def lastTrace(self) -> dict:
        """Optional technical trace of the last processed message."""
        return dict(self._last_trace)

    @Slot()
    def refresh(self):
        self._suggestions = self._build_suggestions()
        self._sync_backend_state()
        self.contextChanged.emit()

    def _sync_backend_state(self):
        if self._ai_engine and hasattr(self._ai_engine, 'backend_selector'):
            sel = self._ai_engine.backend_selector
            self._backend_type = sel._active_name
            sel.available_backends()
            be = sel.active
            self._model_status = "loaded" if be.is_available() and type(be).__name__ != "CalicoBackend" else \
                                 "not_installed"
            stats = be.get_runtime_stats()
            self._ram_usage_mb = stats.get("ram_mb", 0)
            self.backendChanged.emit()

    def _build_suggestions(self) -> list[dict]:
        if self._ai_engine and hasattr(self._ai_engine, 'get_suggestions'):
            try:
                items = self._ai_engine.get_suggestions({"page": self._page_state.previousRoute() if self._page_state else "home"})
                if items and isinstance(items, (list, tuple)):
                    return [
                        {"title": s.get("title", ""), "description": s.get("description", ""),
                         "action": s.get("action", "navigate"), "route": s.get("route", "")}
                        for s in items[:5]
                    ]
            except Exception:
                logger.debug("suggestion fetch failed", exc_info=True)
        # Fallback actions are natural-language phrases the IntentRouter maps
        # to tools registered in ToolRegistryV2; routes exist in route_registry.
        return [
            {"title": "Reproducir música", "description": "Reanuda la reproducción de tu cola actual",
             "action": "reproduce", "route": ""},
            {"title": "Buscar en biblioteca", "description": "Busca canciones, álbumes o artistas",
             "action": "busca en mi biblioteca", "route": ""},
            {"title": "Crear playlist", "description": "Crea una lista de reproducción nueva",
             "action": "crear playlist", "route": "playlists"},
            {"title": "Diagnosticar biblioteca", "description": "Revisa el estado de tu biblioteca",
             "action": "diagnostica mi biblioteca", "route": ""},
            {"title": "Abrir ajustes", "description": "Configura Michi Music Player",
             "action": "abrir ajustes", "route": "settings"},
        ]

    @Slot(str)
    def setBackend(self, name: str):
        if self._ai_engine and hasattr(self._ai_engine, 'set_active_backend'):
            self._ai_engine.set_active_backend(name)
            self._sync_backend_state()
            self.contextChanged.emit()

    @Slot(str)
    def installModel(self, model_id: str):
        if not self._ai_engine or not hasattr(self._ai_engine, 'backend_selector'):
            return
        bs = self._ai_engine.backend_selector
        mgr = getattr(bs, '_model_manager', None)
        if mgr is None:
            return

        def _progress(done: int, total: int):
            if total > 0:
                self._download_progress = round(done / total * 100, 1)
            else:
                self._download_progress = 0.0
            self.downloadProgressChanged.emit()

        self._download_progress = 0.0
        self._model_status = "downloading"
        self.downloadProgressChanged.emit()
        self.backendChanged.emit()

        success = mgr.install(model_id, progress_callback=_progress)
        if success:
            self._model_status = "installed"
        else:
            self._model_status = "corrupt"
        self._download_progress = 0.0
        self._sync_backend_state()
        self.downloadProgressChanged.emit()
        self.backendChanged.emit()

    @Slot()
    def cancelDownload(self):
        self._model_status = "not_installed"
        self._download_progress = 0.0
        self.downloadProgressChanged.emit()
        self.backendChanged.emit()

    @Slot()
    def unloadModel(self):
        if self._ai_engine and hasattr(self._ai_engine, 'backend_selector'):
            be = self._ai_engine.backend_selector.active
            be.unload()
            self._sync_backend_state()
            self.contextChanged.emit()

    @Slot(result=dict)
    def runBenchmark(self):
        from core.ai.model_benchmark import ModelBenchmark
        if self._ai_engine and hasattr(self._ai_engine, 'backend_selector'):
            be = self._ai_engine.backend_selector.active
            bm = ModelBenchmark(be)
            return bm.run_all()
        return {"error": "No engine available"}

    @Slot()
    def cancel(self):
        if self._ai_engine and hasattr(self._ai_engine, 'cancel'):
            self._ai_engine.cancel()
        pending_plan_id = (self._pending_action or {}).get("plan_id", "")
        if pending_plan_id and self._ai_engine and hasattr(self._ai_engine, "cancel_plan"):
            try:
                self._ai_engine.cancel_plan(pending_plan_id)
            except Exception:
                logger.debug("cancel_plan failed", exc_info=True)
        if self._current_task_id and self._job_svc:
            if self._job_svc.get_job(self._current_task_id) is not None:
                self._job_svc.cancel_job(self._current_task_id)
            self._current_task_id = ""
        self._pending_action = None
        self._current_plan = {}
        self._last_error = ""
        self._set_status("CANCELLED")

    # ── Pre-execution confirmation (P0) ────────────────────────────────
    # Destructive / confirmation-required tools are planned by the engine
    # but NEVER executed until the user explicitly accepts via confirmPlan.

    @Slot(str, result=dict)
    def confirmPlan(self, plan_id: str) -> dict:
        """Execute a pending plan after explicit user confirmation."""
        engine = self._ai_engine
        if engine is None or not hasattr(engine, "confirm_plan"):
            return {"ok": False, "error": "NO_AI_SERVICE", "plan_id": plan_id}
        self._set_status("RUNNING")
        try:
            result = engine.confirm_plan(plan_id)
        except Exception as exc:
            logger.debug("confirm_plan failed", exc_info=True)
            self._set_status("FAILED")
            self._last_error = str(exc)
            self.contextChanged.emit()
            return {"ok": False, "error": str(exc), "plan_id": plan_id}

        if result.get("ok"):
            self._set_status("SUCCEEDED")
            response = result.get("response") or "Acción ejecutada."
        else:
            self._set_status("FAILED")
            self._last_error = result.get("error") or result.get("response") or "EXECUTION_FAILED"
            response = result.get("response") or f"No se pudo ejecutar la acción: {self._last_error}"

        if (self._pending_action or {}).get("plan_id") == plan_id:
            self._pending_action = None
        if self._current_plan.get("plan_id") == plan_id:
            self._current_plan = {}
        self._chat_history.append({"role": "assistant", "text": response})
        self.responseReceived.emit(response)
        self.contextChanged.emit()
        return result

    @Slot(str, result=dict)
    def rejectPlan(self, plan_id: str) -> dict:
        """Reject a pending plan; the action is never executed."""
        engine = self._ai_engine
        if engine is None or not hasattr(engine, "reject_plan"):
            return {"ok": False, "error": "NO_AI_SERVICE", "plan_id": plan_id}
        try:
            result = engine.reject_plan(plan_id)
        except Exception as exc:
            logger.debug("reject_plan failed", exc_info=True)
            return {"ok": False, "error": str(exc), "plan_id": plan_id}

        if (self._pending_action or {}).get("plan_id") == plan_id:
            self._pending_action = None
        if self._current_plan.get("plan_id") == plan_id:
            self._current_plan = {}
        self._set_status("IDLE")
        response = result.get("response") or "Acción rechazada."
        self._chat_history.append({"role": "assistant", "text": response})
        self.responseReceived.emit(response)
        self.contextChanged.emit()
        return result

    @Slot(str, result=dict)
    def cancelPlan(self, plan_id: str) -> dict:
        """Cancel a pending plan (e.g. timeout or explicit cancel)."""
        engine = self._ai_engine
        if engine is None or not hasattr(engine, "cancel_plan"):
            return {"ok": False, "error": "NO_AI_SERVICE", "plan_id": plan_id}
        try:
            result = engine.cancel_plan(plan_id)
        except Exception as exc:
            logger.debug("cancel_plan failed", exc_info=True)
            return {"ok": False, "error": str(exc), "plan_id": plan_id}

        if (self._pending_action or {}).get("plan_id") == plan_id:
            self._pending_action = None
        if self._current_plan.get("plan_id") == plan_id:
            self._current_plan = {}
        self._set_status("CANCELLED")
        response = result.get("response") or "Confirmación cancelada."
        self._chat_history.append({"role": "assistant", "text": response})
        self.responseReceived.emit(response)
        self.contextChanged.emit()
        return result

    @Slot(str)
    def sendMessage(self, text: str):
        self._chat_history.append({"role": "user", "text": text})
        normalized = text.strip().lower()
        if normalized in ("cancel", "detener", "parar"):
            self.cancel()
            return
        # Textual confirmation: only when a real engine plan is pending.
        pending_plan_id = (self._pending_action or {}).get("plan_id", "")
        if pending_plan_id and normalized in ("sí", "si", "yes", "confirmar", "confirmo", "adelante"):
            self.confirmPlan(pending_plan_id)
            return
        if pending_plan_id and normalized in ("no", "rechazar", "rechazo", "negativo"):
            self.rejectPlan(pending_plan_id)
            return
        self._set_status("PLANNING")

        if not self._ai_engine:
            self._set_status("FAILED")
            self._last_error = "NO_AI_SERVICE"
            response = "El asistente AI no esta disponible."
            self._chat_history.append({"role": "assistant", "text": response})
            self.responseReceived.emit(response)
            self.contextChanged.emit()
            return

        try:
            context = {}
            if self._page_state:
                context["page"] = self._page_state.previousRoute()
            if self._cap_bridge:
                context["capabilities"] = dict(self._cap_bridge.capabilities)

            result = self._ai_engine.process_message(text, context=context)
            self._last_trace = {
                "intent": result.get("intent", ""),
                "backend": result.get("backend", ""),
                "elapsed_ms": result.get("elapsed_ms", 0),
                "risk_level": result.get("risk_level", ""),
                "tool_ok": (result.get("tool_result") or {}).get("ok"),
            }
            self._handle_ai_result(result, text)
        except Exception as e:
            logger.debug("MichiAIEngine failed", exc_info=True)
            self._set_status("FAILED")
            self._last_error = str(e)
            self._last_trace = {"error": str(e)}
            response = f"Error al procesar: {str(e)}"
            self._chat_history.append({"role": "assistant", "text": response})
            self.responseReceived.emit(response)
            self.contextChanged.emit()

    def _handle_ai_result(self, result: dict, original_text: str):
        if result.get("requires_confirmation"):
            intent_info = result.get("intent")
            plan_id = result.get("plan_id", "") or ""
            plan_info = result.get("plan") if isinstance(result.get("plan"), dict) else {}
            self._pending_action = {
                "intent": intent_info, "entities": {}, "_original": original_text,
                "plan_id": plan_id,
            }
            self._current_plan = {
                "action": plan_info.get("action") or original_text,
                "intent": intent_info if isinstance(intent_info, str) else (intent_info or {}).get("name", ""),
                "tool": plan_info.get("tool", ""),
                "plan_id": plan_id,
                "risk_level": result.get("risk_level", ""),
                "destructive": plan_info.get("destructive", False),
                "requires_confirmation": True,
            }
            self._set_status("CONFIRMATION_REQUIRED")
            msg = result.get("response") or "¿Confirmas que quieres realizar esta accion?"
            self._chat_history.append({"role": "assistant", "text": msg})
            self.responseReceived.emit(msg)
            self.contextChanged.emit()
            return

        self._current_plan = {}
        success = result.get("ok", False)
        if success:
            self._set_status("SUCCEEDED")
            response = result.get("response", "Hecho.")
        else:
            self._set_status("FAILED")
            self._last_error = result.get("response", "UNKNOWN")
            response = result.get("response", "Error al procesar la solicitud.")

        self._chat_history.append({"role": "assistant", "text": response})
        self.responseReceived.emit(response)
        self.contextChanged.emit()

    @Slot(result=str)
    def getChatHistory(self):
        return json.dumps(self._chat_history)

    @Slot(result=dict)
    def aiScore(self) -> dict:
        score = 0
        if self._ai_engine:
            score += 25
        if self._registry and any(a.handler for a in self._registry._actions.values()):
            score += 20
        if self._confirm_svc:
            score += 15
        if self._nav:
            score += 10
        if self._job_svc:
            score += 10
        if self._cap_bridge:
            score += 10
        if self._page_state:
            score += 5
        if self._access:
            score += 5
        if self._status in AI_STATES:
            score += 5
        if self._suggestions:
            score += 5
        if self._chat_history:
            score += 5
        return {
            "score": min(100, score),
            "status": self._status,
            "has_ai_service": self._ai_svc is not None,
            "has_registry": self._registry is not None,
            "has_confirmation": self._confirm_svc is not None,
            "has_nav": self._nav is not None,
            "has_job": self._job_svc is not None,
            "has_capability": self._cap_bridge is not None,
            "has_page_state": self._page_state is not None,
            "has_accessibility": self._access is not None,
            "suggestion_count": len(self._suggestions),
            "chat_count": len(self._chat_history),
        }
