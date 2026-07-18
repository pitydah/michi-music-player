from __future__ import annotations

import random
from typing import Any

from michi_ai.v2.core.models import ProviderRequest

_SPANISH_TEMPLATES: dict[str, list[str]] = {
    "greeting": [
        "¡Hola! Soy Michi Calico, tu asistente musical. ¿En qué puedo ayudarte?",
        "Bienvenido. Estoy aquí para ayudarte con tu música y el ecosistema Michi.",
        "Hola. ¿Qué necesitas? Puedo buscar música, darte información de tu biblioteca o ayudarte con diagnósticos.",
    ],
    "search_library": [
        "Buscando en tu biblioteca... He encontrado {count} resultados para '{query}'.",
        "Estoy revisando tu biblioteca. Hay {count} canciones que coinciden con '{query}'.",
    ],
    "no_results": [
        "No encontré resultados para '{query}' en tu biblioteca. ¿Quieres intentar con otro término?",
        "Lo siento, no hay nada en tu biblioteca que coincida con '{query}'.",
    ],
    "playback_info": [
        "Ahora mismo está sonando '{title}' de {artist}.",
        "Reproduciendo '{title}' — {artist}.",
        "Actualmente no hay reproducción activa.",
    ],
    "diagnosis_ok": [
        "El sistema parece estar en buen estado. {detail}",
        "Todo funciona correctamente: {detail}",
    ],
    "diagnosis_warning": [
        "He detectado algunos puntos que requieren atención: {detail}",
        "Hay {count} aspecto(s) que deberías revisar: {detail}",
    ],
    "help": [
        "Puedo ayudarte a: buscar música, controlar la reproducción, consultar información de tu biblioteca, diagnosticar el sistema, y sugerir recomendaciones. ¿Qué deseas hacer?",
        "Mis capacidades incluyen: búsqueda en biblioteca, control de reproducción, información de álbumes y artistas, diagnóstico del sistema, y recomendaciones musicales.",
    ],
    "out_of_scope": [
        "Eso está fuera de mi ámbito. Soy un asistente especializado en música y el ecosistema Michi. ¿Quieres que te ayude con tu biblioteca musical?",
        "No puedo responder a eso. Solo puedo ayudarte con música, tu biblioteca y el ecosistema Michi. ¿Pruebas con algo relacionado?",
    ],
    "error": [
        "Lo siento, ocurrió un error al procesar tu solicitud. Intenta de nuevo.",
        "No pude completar la acción. Verifica que el servicio esté disponible e inténtalo de nuevo.",
    ],
    "success": [
        "Acción completada correctamente.",
        "Listo. La operación se realizó con éxito.",
    ],
    "confirmation_needed": [
        "Esta acción requiere confirmación. ¿Estás seguro de que deseas continuar?",
        "Para continuar necesito tu confirmación. ¿Procedemos?",
    ],
    "suggestion": [
        "¿Qué te parece si exploramos '{suggestion}'?",
        "Podría interesarte '{suggestion}'.",
    ],
}


class ResponseComposer:
    def compose(self, request: ProviderRequest, metadata: dict | None = None) -> str:
        messages = request.messages
        if not messages:
            return self._template("greeting")

        user_msg = messages[-1].get("content", "") if isinstance(messages[-1], dict) else str(messages[-1])

        if metadata is None:
            metadata = {}

        intent = metadata.get("intent", "unknown")
        entities = metadata.get("entities", {})

        composer_map = {
            "search_library": self._compose_search,
            "playback_info": self._compose_playback,
            "diagnosis": self._compose_diagnosis,
            "help": self._compose_help,
            "greeting": self._compose_greeting,
            "out_of_scope": self._compose_out_of_scope,
            "confirmation": self._compose_confirmation,
            "success": self._compose_success,
            "error": self._compose_error,
            "suggestion": self._compose_suggestion,
        }

        composer = composer_map.get(intent, self._compose_fallback)
        return composer(user_msg, entities, metadata)

    def _template(self, key: str, **kwargs: Any) -> str:
        templates = _SPANISH_TEMPLATES.get(key, ["..."])
        tpl = random.choice(templates)
        return tpl.format(**kwargs)

    def _compose_search(self, msg: str, entities: dict, metadata: dict) -> str:
        query = entities.get("query", msg)
        count = metadata.get("result_count", 0)
        if count > 0:
            return self._template("search_library", count=count, query=query)
        return self._template("no_results", query=query)

    def _compose_playback(self, msg: str, entities: dict, metadata: dict) -> str:
        title = metadata.get("title", "")
        artist = metadata.get("artist", "")
        if title and artist:
            return self._template("playback_info", title=title, artist=artist)
        return "Actualmente no hay reproducción activa."

    def _compose_diagnosis(self, msg: str, entities: dict, metadata: dict) -> str:
        issues = metadata.get("issues", [])
        if not issues:
            return self._template("diagnosis_ok", detail=metadata.get("detail", "No se encontraron problemas."))
        detail = "; ".join(issues[:3])
        return self._template("diagnosis_warning", count=len(issues), detail=detail)

    def _compose_help(self, msg: str, entities: dict, metadata: dict) -> str:
        return self._template("help")

    def _compose_greeting(self, msg: str, entities: dict, metadata: dict) -> str:
        return self._template("greeting")

    def _compose_out_of_scope(self, msg: str, entities: dict, metadata: dict) -> str:
        return self._template("out_of_scope")

    def _compose_confirmation(self, msg: str, entities: dict, metadata: dict) -> str:
        return self._template("confirmation_needed")

    def _compose_success(self, msg: str, entities: dict, metadata: dict) -> str:
        return self._template("success")

    def _compose_error(self, msg: str, entities: dict, metadata: dict) -> str:
        return self._template("error")

    def _compose_suggestion(self, msg: str, entities: dict, metadata: dict) -> str:
        suggestion = entities.get("title", metadata.get("suggestion", "música"))
        return self._template("suggestion", suggestion=suggestion)

    def _compose_fallback(self, msg: str, entities: dict, metadata: dict) -> str:
        if any(word in msg.lower() for word in ["hola", "buenas", "hey", "saludos"]):
            return self._template("greeting")
        if any(word in msg.lower() for word in ["ayuda", "qué puedes", "funciones", "capacidades"]):
            return self._template("help")
        if any(word in msg.lower() for word in ["busca", "encuentra", "encuentrame"]):
            query = msg.lower().replace("busca", "").replace("encuentra", "").strip()
            return self._template("no_results", query=query or "...")
        return self._template("out_of_scope")
