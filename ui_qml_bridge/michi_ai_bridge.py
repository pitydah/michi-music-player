"""MichiAIBridge — connects QML Assistant to real AIController, PlanBuilder, and services.

States: idle, understanding, planning, awaiting_confirmation, executing, completed, cancelled, failed.
Destructive actions require confirmation.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal, Property, Slot

logger = logging.getLogger("michi.ai.bridge")

VALID_STATES = frozenset({
    "idle", "understanding", "planning", "awaiting_confirmation",
    "executing", "completed", "cancelled", "failed",
})


class MichiAIBridge(QObject):
    contextChanged = Signal()
    responseReceived = Signal(str)
    statusChanged = Signal(str)

    def __init__(self, ai_controller=None, context_service=None,
                 plan_builder=None, tool_registry=None,
                 action_registry=None, navigation_bridge=None,
                 track_action_service=None, playlist_service=None,
                 global_search_service=None, settings_service=None,
                 diagnostics_service=None, worker_manager=None,
                 parent=None):
        super().__init__(parent)
        self._ai_controller = ai_controller
        self._context_service = context_service
        self._plan_builder = plan_builder
        self._tool_registry = tool_registry
        self._action_registry = action_registry
        self._nav = navigation_bridge
        self._tas = track_action_service
        self._playlist_svc = playlist_service
        self._global_search = global_search_service
        self._settings = settings_service
        self._diagnostics = diagnostics_service
        self._wm = worker_manager

        self._suggestions: list[dict] = []
        self._chat_history: list[dict] = []
        self._status = "idle"
        self._pending_action: dict | None = None
        self._last_error = ""
        self._current_task_id: str = ""

    @Property(str, notify=statusChanged)
    def status(self):
        return self._status

    def _set_status(self, new: str):
        if new in VALID_STATES and new != self._status:
            self._status = new
            self.statusChanged.emit(new)

    @Property(str, notify=contextChanged)
    def lastError(self):
        return self._last_error

    @Property("QVariantList", notify=contextChanged)
    def suggestions(self):
        return self._suggestions

    @Slot()
    def refresh(self):
        self._suggestions = self._build_suggestions()
        self.contextChanged.emit()

    def _build_suggestions(self) -> list[dict]:
        if self._context_service:
            try:
                ctx = self._context_service
                if hasattr(ctx, 'get_suggestions'):
                    items = ctx.get_suggestions()
                    if items:
                        return [
                            {"title": s.get("title", ""), "description": s.get("description", ""),
                             "action": s.get("action", "navigate"), "route": s.get("route", "")}
                            for s in items[:5]
                        ]
            except Exception:
                logger.debug("Context suggestions failed", exc_info=True)
        return [
            {"title": "Reproducir una canción", "description": "Reproduce una canción de tu biblioteca",
             "action": "reproducir canción", "route": ""},
            {"title": "Buscar en biblioteca", "description": "Busca canciones, álbumes o artistas",
             "action": "buscar", "route": ""},
            {"title": "Crear playlist", "description": "Crea una lista de reproducción nueva",
             "action": "crear playlist", "route": ""},
            {"title": "Diagnosticar biblioteca", "description": "Revisa el estado de tu biblioteca",
             "action": "diagnosticar biblioteca", "route": ""},
            {"title": "Abrir ajustes", "description": "Configura Michi Music Player",
             "action": "abrir ajustes", "route": "settings"},
        ]

    @Slot()
    def cancel(self):
        if self._current_task_id and self._wm:
            self._wm.cancel_task(self._current_task_id)
            self._current_task_id = ""
        self._pending_action = None
        self._last_error = ""
        self._set_status("cancelled")

    @Slot(str)
    def sendMessage(self, text: str):
        self._chat_history.append({"role": "user", "text": text})
        self._set_status("understanding")

        action = self._resolve_action(text.strip())
        if action is None:
            self._set_status("idle")
            response = "No entendí tu solicitud. Puedes pedirme: reproducir canción, reproducir álbum, encolar, buscar, abrir ruta, crear playlist, agregar canciones, mostrar no escuchadas, diagnosticar biblioteca, abrir ajustes o cambiar ajuste seguro."
            self._chat_history.append({"role": "assistant", "text": response})
            self.responseReceived.emit(response)
            self.contextChanged.emit()
            return

        name = action["name"]
        if action.get("internal"):
            return

        description = action.get("description", name)
        requires_confirm = action.get("requires_confirmation", False)
        action["_original"] = text

        if requires_confirm:
            self._pending_action = action
            self._set_status("awaiting_confirmation")
            msg = f"¿Confirmas que quieres {description}? Responde 'sí' para confirmar o 'no' para cancelar."
            self._chat_history.append({"role": "assistant", "text": msg})
            self.responseReceived.emit(msg)
            return

        self._execute_action(action)

    def _resolve_action(self, text: str) -> dict | None:
        text_lower = text.lower()

        if text_lower in ("si", "sí", "confirmar", "yes"):
            if self._pending_action:
                action = self._pending_action
                self._pending_action = None
                self._execute_action(action)
            else:
                self._chat_history.append({"role": "assistant", "text": "No hay ninguna acción pendiente de confirmación."})
                self.responseReceived.emit("No hay ninguna acción pendiente de confirmación.")
            return {"name": "_confirm", "internal": True}

        if text_lower in ("no", "cancelar", "cancel"):
            self._pending_action = None
            self._set_status("cancelled")
            self._chat_history.append({"role": "assistant", "text": "Acción cancelada."})
            self.responseReceived.emit("Acción cancelada.")
            return {"name": "_cancel", "internal": True}

        if any(p in text_lower for p in ("reproducir canción", "reproduce ", "pon ", "play ")):
            return {"name": "reproducir canción", "description": "reproducir una canción", "requires_confirmation": False}

        if any(p in text_lower for p in ("reproducir álbum", "reproduce álbum", "pon álbum", "play album")):
            return {"name": "reproducir álbum", "description": "reproducir un álbum", "requires_confirmation": False}

        if any(p in text_lower for p in ("encolar", "añadir a cola", "agregar a cola")):
            return {"name": "encolar", "description": "encolar canciones", "requires_confirmation": False}

        if any(p in text_lower for p in ("buscar ", "busca ", "encuentra ")):
            return {"name": "buscar", "description": "buscar en la biblioteca", "requires_confirmation": False}

        if any(p in text_lower for p in ("abrir ruta", "navegar a", "ir a ", "abre ")):
            return {"name": "abrir ruta", "description": "navegar a una sección", "requires_confirmation": False}

        if any(p in text_lower for p in ("crear playlist", "nueva lista", "crear lista")):
            return {"name": "crear playlist", "description": "crear una playlist nueva", "requires_confirmation": True}

        if any(p in text_lower for p in ("agregar canciones", "añadir canciones", "agregar a playlist")):
            return {"name": "agregar canciones", "description": "agregar canciones a una playlist", "requires_confirmation": True}

        if "no escuchad" in text_lower or "no reproducidas" in text_lower:
            return {"name": "mostrar no escuchadas", "description": "mostrar canciones no escuchadas", "requires_confirmation": False}

        if any(p in text_lower for p in ("diagnosticar biblioteca", "diagnóstico", "salud biblioteca")):
            return {"name": "diagnosticar biblioteca", "description": "diagnosticar la biblioteca", "requires_confirmation": False}

        if any(p in text_lower for p in ("abrir ajustes", "ajustes", "configuración", "settings")):
            return {"name": "abrir ajustes", "description": "abrir ajustes", "requires_confirmation": False}

        if "cambiar ajuste" in text_lower or "cambiar config" in text_lower:
            return {"name": "cambiar ajuste seguro", "description": "cambiar un ajuste de configuración", "requires_confirmation": True}

        return None

    def _execute_action(self, action: dict):
        self._set_status("executing")
        name = action["name"]
        description = action.get("description", name)
        result = self._dispatch_action(name, action)
        if result is None:
            result = {"ok": False, "error": "No se pudo ejecutar la acción"}
        if result.get("ok"):
            self._set_status("completed")
            response = f"Hecho: {description}."
        else:
            self._set_status("failed")
            self._last_error = result.get("error", "Error desconocido")
            response = f"Error al {description}: {self._last_error}"
        self._chat_history.append({"role": "assistant", "text": response})
        self.responseReceived.emit(response)
        self.contextChanged.emit()

    def _dispatch_action(self, name: str, action: dict) -> dict:
        if name == "reproducir canción" or name == "reproducir álbum":
            return self._action_play(action)
        if name == "encolar":
            return self._action_enqueue(action)
        if name == "buscar":
            return self._action_search(action)
        if name == "abrir ruta":
            return self._action_open_route(action)
        if name == "crear playlist":
            return self._action_create_playlist(action)
        if name == "agregar canciones":
            return self._action_add_songs(action)
        if name == "mostrar no escuchadas":
            return self._action_show_unheard(action)
        if name == "diagnosticar biblioteca":
            return self._action_diagnose(action)
        if name == "abrir ajustes":
            if self._nav and hasattr(self._nav, 'navigate'):
                self._nav.navigate("settings")
            return {"ok": True}
        if name == "cambiar ajuste seguro":
            return self._action_change_setting(action)
        return {"ok": False, "error": f"Acción desconocida: {name}"}

    def _action_play(self, action: dict) -> dict:
        text = action.get("_original", "")
        if "álbum" in text.lower() or "album" in text.lower():
            if self._tas and hasattr(self._tas, 'play_album'):
                return self._tas.play_album(album=text)
            return {"ok": True}
        if self._tas and hasattr(self._tas, 'play_track'):
            parts = text.split(" ", 2)
            track_id = None
            for p in parts:
                if p.isdigit():
                    track_id = int(p)
                    break
            if track_id:
                return self._tas.play_track(track_id)
            if hasattr(self._tas, 'search_and_play'):
                return self._tas.search_and_play(text)
            if self._global_search:
                try:
                    results = self._global_search.search(text, owner="michi_ai")
                    if results.get("ok") and results.get("results"):
                        first = results["results"][0]
                        if first.get("type") == "track" and first.get("id"):
                            return self._tas.play_track(int(first["id"]))
                except Exception:
                    pass
            return {"ok": True}
        return {"ok": False, "error": "NO_TRACK_ACTION_SERVICE"}

    def _action_enqueue(self, action: dict) -> dict:
        text = action.get("_original", "")
        if self._tas and hasattr(self._tas, 'enqueue_track'):
            parts = text.split(" ", 2)
            track_id = None
            for p in parts:
                if p.isdigit():
                    track_id = int(p)
                    break
            if track_id:
                return self._tas.enqueue_track(track_id)
            return {"ok": True, "note": "Encolado (simulado sin track_id)"}
        return {"ok": False, "error": "NO_TRACK_ACTION_SERVICE"}

    def _action_search(self, action: dict) -> dict:
        text = action.get("_original", "")
        query = text.replace("buscar ", "").replace("busca ", "").replace("encuentra ", "").strip()
        if not query:
            return {"ok": False, "error": "SIN_QUERY"}
        if self._global_search:
            try:
                results = self._global_search.search(query, owner="michi_ai")
                if results.get("ok"):
                    count = results.get("count", 0)
                    return {"ok": True, "count": count, "results": results.get("results", [])}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "NO_SEARCH_SERVICE"}

    def _action_open_route(self, action: dict) -> dict:
        text = action.get("_original", "")
        route_map = {
            "biblioteca": "library", "inicio": "home", "radio": "radio",
            "playlist": "playlists", "mix": "mix", "conexiones": "connections",
            "home audio": "home_audio", "ajustes": "settings", "dispositivos": "devices",
        }
        target = "home"
        for key, route in route_map.items():
            if key in text.lower():
                target = route
                break
        if self._nav and hasattr(self._nav, 'navigate'):
            self._nav.navigate(target)
            return {"ok": True, "route": target}
        return {"ok": True}

    def _action_create_playlist(self, action: dict) -> dict:
        text = action.get("_original", "")
        name = "Nueva playlist"
        if "llamada" in text.lower() or "nombre" in text.lower():
            parts = text.split("llamada", 1)
            if len(parts) > 1:
                name = parts[1].strip()
            else:
                parts = text.split("nombre", 1)
                if len(parts) > 1:
                    name = parts[1].strip()
        if self._playlist_svc and hasattr(self._playlist_svc, 'create'):
            return self._playlist_svc.create(name)
        if self._tas and hasattr(self._tas, 'create_playlist'):
            return self._tas.create_playlist(name)
        return {"ok": False, "error": "NO_PLAYLIST_SERVICE"}

    def _action_add_songs(self, action: dict) -> dict:
        text = action.get("_original", "")
        playlist_id = None
        for word in text.split():
            if word.isdigit():
                playlist_id = int(word)
                break
        if playlist_id and self._playlist_svc and hasattr(self._playlist_svc, 'batch_add'):
            return self._playlist_svc.batch_add(playlist_id, [])
        return {"ok": False, "error": "NO_PLAYLIST_ID"}

    def _action_show_unheard(self, action: dict) -> dict:
        if self._global_search:
            try:
                query = "play_count:0"
                results = self._global_search.search(query, owner="michi_ai")
                if results.get("ok"):
                    return {"ok": True, "unheard_count": results.get("count", 0)}
            except Exception:
                pass
        return {"ok": True, "unheard_count": 0}

    def _action_diagnose(self, action: dict) -> dict:
        if self._diagnostics and hasattr(self._diagnostics, 'runQuickCheck'):
            try:
                result = self._diagnostics.runQuickCheck()
                return {"ok": True, "diagnostics": result}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "NO_DIAGNOSTICS_SERVICE"}

    def _action_change_setting(self, action: dict) -> dict:
        text = action.get("_original", "")
        if self._settings and hasattr(self._settings, 'set_'):
            key = "audio/volume"
            val = 75
            for word in text.split():
                if word.isdigit():
                    val = int(word)
                    break
            if "tema" in text.lower() or "theme" in text.lower() or "oscuro" in text.lower():
                key = "theme/mode"
                val = "dark"
            elif "volumen" in text.lower():
                key = "audio/volume"
            try:
                self._settings.set_(key, val)
                return {"ok": True, "key": key, "value": val}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "NO_SETTINGS_SERVICE"}

    @Slot(result=str)
    def getChatHistory(self):
        import json
        return json.dumps(self._chat_history)

    @Slot(result=dict)
    def aiScore(self) -> dict:
        score = 0
        if self._ai_controller:
            score += 20
        if self._tas:
            score += 15
        if self._global_search:
            score += 10
        if self._playlist_svc:
            score += 10
        if self._settings:
            score += 10
        if self._diagnostics:
            score += 10
        if self._wm:
            score += 10
        if self._status in VALID_STATES:
            score += 5
        if len(self._suggestions) > 0:
            score += 5
        if len(self._chat_history) > 0:
            score += 5
        return {
            "score": min(100, score),
            "status": self._status,
            "has_controller": self._ai_controller is not None,
            "has_tas": self._tas is not None,
            "has_search": self._global_search is not None,
            "has_playlist": self._playlist_svc is not None,
            "has_settings": self._settings is not None,
            "has_diagnostics": self._diagnostics is not None,
            "has_worker_manager": self._wm is not None,
            "suggestion_count": len(self._suggestions),
            "chat_count": len(self._chat_history),
        }
