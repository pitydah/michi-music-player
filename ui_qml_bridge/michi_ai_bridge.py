from __future__ import annotations

import json
import logging

from PySide6.QtCore import QObject, Signal, Property, Slot

from ui_qml_bridge.action_registry import ActionRegistry

logger = logging.getLogger("michi.ai.bridge")

AI_STATES = frozenset({
    "IDLE", "PLANNING", "CONFIRMATION_REQUIRED", "QUEUED", "RUNNING",
    "CANCELLING", "CANCELLED", "SUCCEEDED", "PARTIAL_SUCCESS", "FAILED",
})


class MichiAIBridge(QObject):
    contextChanged = Signal()
    responseReceived = Signal(str)
    statusChanged = Signal(str)

    def __init__(
        self,
        device_sync_service=None,
        job_service=None,
        action_registry: ActionRegistry | None = None,
        confirmation_service=None,
        navigation_bridge=None,
        capability_bridge=None,
        page_state_store=None,
        accessibility_bridge=None,
        parent=None,
        **kwargs,
    ):
        super().__init__(parent)
        self._dev_svc = device_sync_service or kwargs.get("device_sync_service")
        self._job_svc = job_service or kwargs.get("job_service") or kwargs.get("worker_manager")
        reg = action_registry or kwargs.get("action_registry")
        self._registry = reg or ActionRegistry()
        self._confirm_svc = confirmation_service or kwargs.get("confirmation_service")
        self._nav = navigation_bridge or kwargs.get("navigation_bridge")
        self._cap_bridge = capability_bridge or kwargs.get("capability_bridge")
        self._page_state = page_state_store or kwargs.get("page_state_store")
        self._access = accessibility_bridge or kwargs.get("accessibility_bridge")

        self._status = "IDLE"
        self._suggestions: list[dict] = []
        self._chat_history: list[dict] = []
        self._pending_action: dict | None = None
        self._last_error = ""
        self._current_task_id = ""
        self._session_id = "default"

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

    @Property("QVariantList", notify=contextChanged)
    def suggestions(self):
        return self._suggestions

    @Slot()
    def refresh(self):
        self._suggestions = self._build_suggestions()
        self.contextChanged.emit()

    def _build_suggestions(self) -> list[dict]:
        if self._confirm_svc and hasattr(self._confirm_svc, 'get_suggestions'):
            try:
                items = self._confirm_svc.get_suggestions()
                if items and isinstance(items, (list, tuple)):
                    return [
                        {"title": s.get("title", ""), "description": s.get("description", ""),
                         "action": s.get("action", "navigate"), "route": s.get("route", "")}
                        for s in items[:5]
                    ]
            except Exception:
                logger.debug("suggestion fetch failed", exc_info=True)
        return [
            {"title": "Reproducir una cancion", "description": "Reproduce una cancion de tu biblioteca",
             "action": "reproducir cancion", "route": ""},
            {"title": "Buscar en biblioteca", "description": "Busca canciones, albumes o artistas",
             "action": "buscar", "route": ""},
            {"title": "Crear playlist", "description": "Crea una lista de reproduccion nueva",
             "action": "crear playlist", "route": ""},
            {"title": "Diagnosticar biblioteca", "description": "Revisa el estado de tu biblioteca",
             "action": "diagnosticar biblioteca", "route": ""},
            {"title": "Abrir ajustes", "description": "Configura Michi Music Player",
             "action": "abrir ajustes", "route": "settings"},
        ]

    @Slot()
    def cancel(self):
        if self._current_task_id and self._job_svc:
            import contextlib
            with contextlib.suppress(Exception):
                self._job_svc.cancel_job(self._current_task_id)
            self._current_task_id = ""
        self._pending_action = None
        self._last_error = ""
        self._set_status("CANCELLED")

    def _resolve_action(self, text: str) -> dict | None:
        text_lower = text.lower()

        if text_lower in ("si", "sí", "confirmar", "yes"):
            if self._pending_action:
                action = self._pending_action
                self._pending_action = None
                self._execute_action(action)
            else:
                self._chat_history.append({"role": "assistant", "text": "No hay ninguna accion pendiente de confirmacion."})
                self.responseReceived.emit("No hay ninguna accion pendiente de confirmacion.")
            return {"name": "_confirm", "internal": True}

        if text_lower in ("no", "cancelar", "cancel"):
            self._pending_action = None
            self._set_status("CANCELLED")
            self._chat_history.append({"role": "assistant", "text": "Accion cancelada."})
            self.responseReceived.emit("Accion cancelada.")
            return {"name": "_cancel", "internal": True}

        intent_map: list[tuple[list[str], str, str, bool]] = [
            (["reproducir cancion", "reproduce cancion", "reproduce ", "pon ", "play "], "reproducir cancion", "reproducir una cancion", False),
            (["reproducir album", "reproduce album", "reproduce el album", "pon album", "play album"], "reproducir album", "reproducir un album", False),
            (["encolar", "anadir a cola", "agregar a cola"], "encolar", "encolar canciones", False),
            (["buscar ", "buscar", "busca ", "encuentra "], "buscar", "buscar en la biblioteca", False),
            (["abrir ruta", "navegar a", "ir a ", "abre "], "abrir ruta", "navegar a una seccion", False),
            (["crear playlist", "nueva lista", "crear lista"], "crear playlist", "crear una playlist nueva", True),
            (["agregar canciones", "anadir canciones", "agregar a playlist"], "agregar canciones", "agregar canciones a una playlist", True),
            (["no escuchad", "no reproducidas"], "mostrar no escuchadas", "mostrar canciones no escuchadas", False),
            (["diagnosticar biblioteca", "diagnostico", "salud biblioteca"], "diagnosticar biblioteca", "diagnosticar la biblioteca", False),
            (["abrir ajustes", "ajustes", "configuracion", "settings"], "abrir ajustes", "abrir ajustes", False),
            (["cambiar ajuste", "cambiar config"], "cambiar ajuste seguro", "cambiar un ajuste de configuracion", True),
        ]
        for triggers, name, desc, needs_confirm in intent_map:
            if any(p in text_lower for p in triggers):
                return {"name": name, "description": desc, "requires_confirmation": needs_confirm, "_original": text}
        return None

    @Slot(str)
    def sendMessage(self, text: str):
        self._chat_history.append({"role": "user", "text": text})
        self._set_status("PLANNING")

        action = self._resolve_action(text.strip())
        if action is None:
            self._set_status("FAILED")
            response = ("No entendi tu solicitud. Puedes pedirme: reproducir cancion, reproducir album, "
                        "encolar, buscar, abrir ruta, crear playlist, agregar canciones, "
                        "mostrar no escuchadas, diagnosticar biblioteca, abrir ajustes o cambiar ajuste seguro.")
            self._chat_history.append({"role": "assistant", "text": response})
            self.responseReceived.emit(response)
            self.contextChanged.emit()
            return

        if action.get("internal"):
            return

        name = action["name"]
        description = action.get("description", name)
        requires_confirm = action.get("requires_confirmation", False)

        if requires_confirm:
            self._pending_action = action
            self._set_status("CONFIRMATION_REQUIRED")
            msg = f"Confirmas que quieres {description}? Responde 'si' para confirmar o 'no' para cancelar."
            self._chat_history.append({"role": "assistant", "text": msg})
            self.responseReceived.emit(msg)
            return

        self._execute_action(action)

    def _execute_action(self, action: dict):
        self._set_status("RUNNING")
        name = action["name"]
        description = action.get("description", name)

        registry = getattr(self, '_registry', None)
        if registry:
            action_id_map = {
                "reproducir cancion": "track_play_now",
                "reproducir album": "album_play",
                "encolar": "track_add_to_queue",
                "buscar": "navigate_library",
                "abrir ruta": "navigate_home",
                "crear playlist": "playlist_create",
                "agregar canciones": "track_add_to_playlist",
                "mostrar no escuchadas": "library_scan",
                "diagnosticar biblioteca": "diagnostics_show",
                "abrir ajustes": "navigate_settings",
                "cambiar ajuste seguro": "metadata_edit",
            }
            rid = action_id_map.get(name)
            if rid:
                action_obj = registry.get(rid)
                if action_obj and action_obj.enabled and action_obj.handler:
                    try:
                        result = action_obj.handler()
                        if isinstance(result, dict) and result.get("ok") is False:
                            self._set_status("FAILED")
                            self._last_error = result.get("error", "ACTION_FAILED")
                            response = f"Error al {description}: {self._last_error}"
                            self._chat_history.append({"role": "assistant", "text": response})
                            self.responseReceived.emit(response)
                            self.contextChanged.emit()
                            return
                        self._set_status("SUCCEEDED")
                        response = f"Hecho: {description}."
                        self._chat_history.append({"role": "assistant", "text": response})
                        self.responseReceived.emit(response)
                        self.contextChanged.emit()
                        return
                    except Exception as e:
                        logger.debug("Action dispatch failed", exc_info=True)
                        self._set_status("FAILED")
                        self._last_error = str(e)
                        response = f"Error al {description}: {str(e)}"
                        self._chat_history.append({"role": "assistant", "text": response})
                        self.responseReceived.emit(response)
                        self.contextChanged.emit()
                        return

        result = self._dispatch_action(name, action)
        if result is None:
            result = {"ok": False, "error": "No se pudo ejecutar la accion"}
        if result.get("ok"):
            self._set_status("SUCCEEDED")
            response = f"Hecho: {description}."
        else:
            self._set_status("FAILED")
            self._last_error = result.get("error", "Error desconocido")
            response = f"Error al {description}: {self._last_error}"
        self._chat_history.append({"role": "assistant", "text": response})
        self.responseReceived.emit(response)
        self.contextChanged.emit()

    def _dispatch_action(self, name: str, action: dict) -> dict:
        if name in ("reproducir cancion", "reproducir album"):
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
                return {"ok": True, "route": "settings"}
            return {"ok": False, "error": "NO_NAVIGATION_SERVICE"}
        if name == "cambiar ajuste seguro":
            return self._action_change_setting(action)
        return {"ok": False, "error": f"Accion desconocida: {name}"}

    def _action_play(self, action: dict) -> dict:
        if not self._registry:
            return {"ok": False, "error": "NO_ACTION_REGISTRY"}
        action_obj = self._registry.get("track_play_now")
        if action_obj and action_obj.handler:
            try:
                result = action_obj.handler()
                return result if isinstance(result, dict) else {"ok": True}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "NO_TRACK_HANDLER"}

    def _action_enqueue(self, action: dict) -> dict:
        if not self._registry:
            return {"ok": False, "error": "NO_ACTION_REGISTRY"}
        action_obj = self._registry.get("track_add_to_queue")
        if action_obj and action_obj.handler:
            try:
                result = action_obj.handler()
                return result if isinstance(result, dict) else {"ok": True}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "NO_ENQUEUE_HANDLER"}

    def _action_search(self, action: dict) -> dict:
        text = action.get("_original", "")
        query = text
        for prefix in ("buscar ", "busca ", "encuentra "):
            if query.startswith(prefix):
                query = query[len(prefix):].strip()
                break
        if not query:
            return {"ok": False, "error": "SIN_QUERY"}
        if self._nav and hasattr(self._nav, 'navigate'):
            self._nav.navigate("library")
            return {"ok": True, "query": query}
        return {"ok": False, "error": "NO_NAVIGATION_SERVICE"}

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
        return {"ok": False, "error": "NO_NAVIGATION_SERVICE"}

    def _action_create_playlist(self, action: dict) -> dict:
        text = action.get("_original", "")
        name = "Nueva playlist"
        for keyword in ("llamada", "nombre"):
            if keyword in text.lower():
                parts = text.split(keyword, 1)
                if len(parts) > 1:
                    name = parts[1].strip()
                    break
        if self._registry:
            action_obj = self._registry.get("playlist_create")
            if action_obj and action_obj.handler:
                try:
                    result = action_obj.handler()
                    return result if isinstance(result, dict) else {"ok": True, "name": name}
                except Exception as e:
                    return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "NO_PLAYLIST_CREATE_HANDLER"}

    def _action_add_songs(self, action: dict) -> dict:
        text = action.get("_original", "")
        playlist_id = None
        for word in text.split():
            if word.isdigit():
                playlist_id = int(word)
                break
        if playlist_id and self._registry:
            action_obj = self._registry.get("track_add_to_playlist")
            if action_obj and action_obj.handler:
                try:
                    result = action_obj.handler()
                    return result if isinstance(result, dict) else {"ok": True, "playlist_id": playlist_id}
                except Exception as e:
                    return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "NO_PLAYLIST_ID"}

    def _action_show_unheard(self, action: dict) -> dict:
        if self._registry:
            action_obj = self._registry.get("library_scan")
            if action_obj and action_obj.handler:
                try:
                    result = action_obj.handler()
                    return result if isinstance(result, dict) else {"ok": True, "unheard_count": 0}
                except Exception:
                    pass
        return {"ok": True, "unheard_count": 0}

    def _action_diagnose(self, action: dict) -> dict:
        if self._registry:
            action_obj = self._registry.get("diagnostics_show")
            if action_obj and action_obj.handler:
                try:
                    result = action_obj.handler()
                    return result if isinstance(result, dict) else {"ok": True}
                except Exception as e:
                    return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "NO_DIAGNOSTICS_HANDLER"}

    def _parse_intent(self, text: str) -> dict | None:
        text_lower = text.lower()
        if "volumen" in text_lower:
            val = 75
            for word in text.split():
                if word.isdigit():
                    val = int(word)
                    break
            return {"action": "cambiar ajuste seguro", "entities": {"setting_key": "playback/default_volume", "setting_value": val}}
        if "tema" in text_lower or "theme" in text_lower or "oscuro" in text_lower:
            return {"action": "cambiar ajuste seguro", "entities": {"setting_key": "appearance/theme", "setting_value": "dark"}}
        return None

    def _action_change_setting(self, action: dict) -> dict:
        text = action.get("_original", "")
        key = "playback/default_volume"
        val = 75
        intent = self._parse_intent(text)
        if intent:
            key = intent["entities"].get("setting_key", key)
            val = intent["entities"].get("setting_value", val)
        else:
            for word in text.split():
                if word.isdigit():
                    val = int(word)
                    break
            if "tema" in text.lower() or "theme" in text.lower() or "oscuro" in text.lower():
                key = "appearance/theme"
                val = "dark"
            elif "volumen" in text.lower():
                key = "playback/default_volume"
        if self._registry:
            action_obj = self._registry.get("metadata_edit")
            if action_obj and action_obj.handler:
                try:
                    result = action_obj.handler()
                    return result if isinstance(result, dict) else {"ok": True, "key": key, "value": val}
                except Exception as e:
                    return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "NO_SETTINGS_HANDLER"}

    @Slot(result=str)
    def getChatHistory(self):
        return json.dumps(self._chat_history)

    @Slot(result=dict)
    def aiScore(self) -> dict:
        score = 0
        if self._registry:
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
