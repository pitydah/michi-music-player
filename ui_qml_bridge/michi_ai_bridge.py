"""MichiAIBridge — connects QML Assistant to real Michi AIController and PlanBuilder."""

from PySide6.QtCore import QObject, Signal, Property, Slot
import json
import logging

logger = logging.getLogger("michi.ai.bridge")


class MichiAIBridge(QObject):
    contextChanged = Signal()
    responseReceived = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._suggestions = []
        self._chat_history = []
        self._controller = None

    def set_controller(self, controller):
        self._controller = controller

    @Property("QVariantList", notify=contextChanged)
    def suggestions(self):
        return self._suggestions

    @Slot()
    def refresh(self):
        try:
            from michi_ai.context.ai_context_bridge import MichiAIContextBridge
            bridge = MichiAIContextBridge()
            snapshot = bridge.build_snapshot()
            if snapshot:
                self._suggestions = []
                for s in (snapshot.get("suggestions") or []):
                    self._suggestions.append({
                        "title": s.get("title", ""),
                        "description": s.get("description", ""),
                        "action": s.get("action", "navigate"),
                        "route": s.get("route", ""),
                    })
        except Exception:
            logger.debug("MichiAI refresh failed", exc_info=True)
        if not self._suggestions:
            self._suggestions = [
                {"title": "Explorar biblioteca", "description": "Navega por tus álbumes y canciones",
                 "action": "navigate", "route": "library"},
                {"title": "Ver conexiones", "description": "Configura servidores y Michi Micro Server",
                 "action": "navigate", "route": "connections"},
                {"title": "Abrir Home Audio", "description": "Controla la reproducción en tu hogar",
                 "action": "navigate", "route": "home_audio"},
            ]
        self.contextChanged.emit()

    @Slot(str)
    def sendMessage(self, text: str):
        msg = text.strip().lower()
        response = self._try_plan(msg, text)
        if not response:
            response = self._fallback_response(msg)
        self._chat_history.append({"role": "user", "text": text})
        self._chat_history.append({"role": "assistant", "text": response})
        self.responseReceived.emit(response)

    def _try_plan(self, msg: str, original: str) -> str:
        try:
            from michi_ai.planner.plan_builder import PlanBuilder
            from michi_ai.tools.tool_registry import ToolRegistry
            registry = ToolRegistry()
            builder = PlanBuilder(tool_registry=registry)
            plan = builder.build_plan(original)
            if plan and hasattr(plan, 'steps') and plan.steps:
                descs = []
                for step in plan.steps[:3]:
                    descs.append(step.get("description", "") or step.get("tool", ""))
                if descs:
                    return "Puedo ayudarte con eso:\n" + "\n".join(f"  • {d}" for d in descs)
        except Exception:
            logger.debug("PlanBuilder failed", exc_info=True)
        return ""

    def _fallback_response(self, msg: str) -> str:
        if "biblioteca" in msg or "canciones" in msg:
            return "Puedes explorar tu biblioteca desde la sección Biblioteca. Usa el buscador para encontrar canciones y álbumes."
        if "reproduc" in msg or "música" in msg or "play" in msg:
            return "Abre la Biblioteca, busca una canción y haz doble clic para reproducirla."
        if "servidor" in msg or "conexion" in msg or "micro" in msg:
            return "Ve a Conexiones para configurar Michi Micro Server y servidores externos."
        if "home audio" in msg or "asistent" in msg or "hogar" in msg:
            return "Home Audio te permite conectar Home Assistant y el futuro Michi Music Stream."
        if "ayuda" in msg or "qué puedes" in msg:
            return "Puedo ayudarte a navegar por la app, buscar música, configurar servidores y controlar Home Audio."
        return "No tengo una respuesta para eso. Puedes preguntarme sobre biblioteca, reproducción, servidores o Home Audio."

    @Slot(result=str)
    def getChatHistory(self):
        return json.dumps(self._chat_history)
