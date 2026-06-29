"""Michi AI Assistant Service — intent detection, tool execution, confirmation flow."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from integrations.ai_assistant.action_confirmation import PendingActionStore
from integrations.ai_assistant.action_log import ActionLog
from integrations.ai_assistant.conversation_store import ConversationStore
from integrations.ai_assistant.ollama_client import (
    OllamaClient,
    OllamaError,
    OllamaNotAvailable,
    ModelNotFound,
    OllamaTimeout,
)
from integrations.ai_assistant.privacy_filter import sanitize_text, sanitize_for_prompt
from integrations.ai_assistant.prompts import SYSTEM_PROMPT
from integrations.ai_assistant.tool_registry import ToolRegistry
from integrations.ai_assistant.tools.library_tools import (
    search_library,
    recommend_local_tracks,
)
from integrations.ai_assistant.tools.stats_tools import get_library_stats
from integrations.ai_assistant.tools.metadata_tools import find_metadata_gaps
from integrations.ai_assistant.tools.playlist_tools import (
    draft_playlist,
    create_playlist_from_draft,
)
from integrations.ai_assistant.tools.queue_tools import (
    add_tracks_to_queue,
    play_track,
)
from integrations.ai_assistant.tools.favorite_tools import (
    mark_favorite,
    unmark_favorite,
)
from integrations.ai_assistant.tools.navigation_tools import (
    open_artist_view,
    open_album_view,
    open_genre_view,
    open_playlist_view,
    show_track_in_library,
)
from integrations.ai_assistant.tools.knowledge_tools import (
    lookup_artist_info,
    lookup_album_info,
    lookup_track_info,
    explain_artist,
    explain_album,
    refresh_artist_metadata,
    refresh_album_metadata,
)
from integrations.ai_assistant.tools.metadata_review_tools import (
    find_metadata_inconsistencies,
    suggest_metadata_for_track,
    suggest_metadata_for_album,
    suggest_metadata_for_artist,
    create_metadata_review,
    apply_metadata_review,
    reject_metadata_review,
    undo_metadata_review,
)
from integrations.ai_assistant.tools.recommendation_tools import (
    recommend_music,
    recommend_from_track,
    recommend_from_artist,
    recommend_from_album,
    recommend_from_genre,
    create_smart_mix,
    explain_recommendation,
    save_recommendation_as_playlist,
)
from integrations.ai_assistant.tools.audio_analysis_tools import (
    get_audio_analysis_status,
    analyze_track_audio,
    analyze_selected_tracks,
    find_sonically_similar,
    create_acoustic_mix,
    explain_acoustic_features,
    list_tracks_missing_features,
)
from integrations.ai_assistant.schemas import PendingAction, ToolResult


def _inject_context_snapshot(messages: list) -> list:
    """Inject app context snapshot if ContextService is available."""
    try:
        from core.context.context_service import ContextService
        svc = ContextService()
        snap = svc.get_assistant_snapshot()
        if snap:
            import json
            context_text = (
                "Contexto actual de la aplicacion:\n"
                f"{json.dumps(snap, ensure_ascii=False, default=str)}"
            )
            messages.insert(0, {"role": "system", "content": context_text})
    except Exception:
        pass
    return messages


logger = logging.getLogger("michi.ai_assistant.service")


class AIAssistantService:
    def __init__(self, db: Any, model: str = "llama3.1:8b",
                 base_url: str = "http://127.0.0.1:11434",
                 save_history: bool = False, max_results: int = 30,
                 allow_write: bool = False, offline_strict: bool = True,
                 ollama_timeout: int = 30,
                 playback: Any = None,
                 allow_reversible: bool = True,
                 require_confirmation: bool = True,
                 action_log_enabled: bool = True,
                 max_action_tracks: int = 100,
                 max_playlist_tracks: int = 50):
        self._db = db
        self._model = model
        self._max_results = max_results
        self._allow_write = allow_write
        self._allow_reversible = allow_reversible
        self._require_confirmation = require_confirmation
        self._max_action_tracks = max_action_tracks
        self._max_playlist_tracks = max_playlist_tracks
        self._playback = playback
        self._ollama = OllamaClient(base_url=base_url, timeout=ollama_timeout,
                                     offline_strict=offline_strict)
        self._conversation = ConversationStore(save_history=save_history)
        self._conversation.add("system", SYSTEM_PROMPT)
        self._tools = ToolRegistry()
        self._pending = PendingActionStore(ttl_seconds=120)
        self._action_log = ActionLog(enabled=action_log_enabled)
        self._drafts: dict[str, list] = {}
        self._last_tool_result: ToolResult | None = None
        self._last_metadata_review_id = ""
        self._register_tools()

    def _register_tools(self):
        self._tools.register("search_library", search_library)
        self._tools.register("recommend_local_tracks", recommend_local_tracks)
        self._tools.register("get_library_stats", get_library_stats)
        self._tools.register("find_metadata_gaps", find_metadata_gaps)
        self._tools.register("draft_playlist", draft_playlist)
        self._tools.register("create_playlist_from_draft", create_playlist_from_draft)
        self._tools.register("add_tracks_to_queue", add_tracks_to_queue)
        self._tools.register("play_track", play_track)
        self._tools.register("mark_favorite", mark_favorite)
        self._tools.register("unmark_favorite", unmark_favorite)
        self._tools.register("open_artist_view", open_artist_view)
        self._tools.register("open_album_view", open_album_view)
        self._tools.register("open_genre_view", open_genre_view)
        self._tools.register("open_playlist_view", open_playlist_view)
        self._tools.register("show_track_in_library", show_track_in_library)
        self._tools.register("lookup_artist_info", lookup_artist_info)
        self._tools.register("lookup_album_info", lookup_album_info)
        self._tools.register("lookup_track_info", lookup_track_info)
        self._tools.register("explain_artist", explain_artist)
        self._tools.register("explain_album", explain_album)
        self._tools.register("refresh_artist_metadata", refresh_artist_metadata)
        self._tools.register("refresh_album_metadata", refresh_album_metadata)
        self._tools.register("find_metadata_inconsistencies", find_metadata_inconsistencies)
        self._tools.register("suggest_metadata_for_track", suggest_metadata_for_track)
        self._tools.register("suggest_metadata_for_album", suggest_metadata_for_album)
        self._tools.register("suggest_metadata_for_artist", suggest_metadata_for_artist)
        self._tools.register("create_metadata_review", create_metadata_review)
        self._tools.register("apply_metadata_review", apply_metadata_review)
        self._tools.register("reject_metadata_review", reject_metadata_review)
        self._tools.register("undo_metadata_review", undo_metadata_review)
        self._tools.register("recommend_music", recommend_music)
        self._tools.register("recommend_from_track", recommend_from_track)
        self._tools.register("recommend_from_artist", recommend_from_artist)
        self._tools.register("recommend_from_album", recommend_from_album)
        self._tools.register("recommend_from_genre", recommend_from_genre)
        self._tools.register("create_smart_mix", create_smart_mix)
        self._tools.register("explain_recommendation", explain_recommendation)
        self._tools.register("save_recommendation_as_playlist", save_recommendation_as_playlist)
        self._tools.register("get_audio_analysis_status", get_audio_analysis_status)
        self._tools.register("analyze_track_audio", analyze_track_audio)
        self._tools.register("analyze_selected_tracks", analyze_selected_tracks)
        self._tools.register("find_sonically_similar", find_sonically_similar)
        self._tools.register("create_acoustic_mix", create_acoustic_mix)
        self._tools.register("explain_acoustic_features", explain_acoustic_features)
        self._tools.register("list_tracks_missing_features", list_tracks_missing_features)

    @property
    def ollama_available(self) -> bool:
        return self._ollama.check_health()

    def process_message(self, text: str) -> dict:
        """Process a user message. Returns {"reply": str, "pending": dict|None}."""
        try:
            tool_name, tool_args, query_text = self._detect_intent(text)
        except Exception:
            tool_name, tool_args, query_text = None, {}, text

        self._conversation.add("user", text)

        tool_result = None
        if tool_name:
            tool_result = self._tools.execute(
                tool_name, db=self._db, limit=self._max_results, **tool_args,
            )
            if tool_result.success:
                self._conversation.add(
                    "assistant", "",
                    tool_name=tool_name,
                    tool_result=tool_result.data,
                )
                self._last_tool_result = tool_result
                if tool_name == "draft_playlist":
                    self._store_draft(tool_result)
                if tool_name == "create_metadata_review" and tool_result.data:
                    rid = tool_result.data.get("review_id", "") if isinstance(tool_result.data, dict) else ""
                    if rid:
                        self._last_metadata_review_id = rid
            elif tool_result.permission_denied and self._allow_reversible:
                pending = self._create_pending_for(tool_name, tool_args, tool_result, text)
                return {"reply": pending.description or pending.title, "pending": pending}

        try:
            reply = self._call_ollama(tool_result, query_text)
        except OllamaNotAvailable:
            reply = self._format_tool_result(tool_result) if tool_result else (
                "Ollama no esta disponible. Verifica que el servicio este "
                "ejecutandose en el equipo."
            )
        except ModelNotFound:
            reply = self._format_tool_result(tool_result) if tool_result else (
                f"El modelo '{self._model}' no se encontro en Ollama. "
                f"Ejecuta 'ollama pull {self._model}' para descargarlo."
            )
        except OllamaTimeout:
            reply = self._format_tool_result(tool_result) if tool_result else (
                "Ollama tardo demasiado en responder. Intentalo de nuevo."
            )
        except OllamaError as e:
            reply = self._format_tool_result(tool_result) if tool_result else (
                f"Error al comunicarse con Ollama: {e}"
            )

        self._conversation.add("assistant", reply)

        result: dict[str, Any] = {"reply": reply, "pending": None}

        if tool_result and tool_result.success:
            pending = self._suggest_action(tool_name, tool_result)
            if pending:
                result["pending"] = _pending_to_dict(pending)

        return result

    def confirm_action(self, action_id: str) -> dict:
        pending = self._pending.get(action_id)
        if not pending:
            return {"reply": "La accion ha expirado o no existe.", "pending": None}

        result = self._tools.execute_direct(
            pending.tool_name, db=self._db,
            playback=self._playback,
            **pending.arguments,
        )
        self._pending.remove(action_id)

        if result.success:
            self._action_log.register(
                tool_name=pending.tool_name,
                summary=pending.title,
                status="confirmed",
                affected_count=result.data.get("track_count", result.data.get("changed_count", result.data.get("queued_count", 0))) if isinstance(result.data, dict) else 0,
                permission_level=pending.permission_level,
                metadata=result.data if isinstance(result.data, dict) else {},
            )
            reply = self._format_confirmed_result(pending.tool_name, result)
        else:
            reply = f"No se pudo completar: {result.error}"

        self._conversation.add("assistant", reply)
        return {"reply": reply, "pending": None}

    def cancel_action(self, action_id: str) -> dict:
        pending = self._pending.get(action_id)
        if pending:
            self._pending.remove(action_id)
            reply = f"Accion cancelada: {pending.title}"
        else:
            reply = "Accion no encontrada."
        self._conversation.add("assistant", reply)
        return {"reply": reply, "pending": None}

    def list_pending_actions(self) -> list[dict]:
        return [_pending_to_dict(a) for a in self._pending.list_all()]

    def clear_pending_actions(self):
        self._pending.clear()

    def clear(self):
        self._conversation.clear()
        self._conversation.add("system", SYSTEM_PROMPT)
        self._pending.clear()
        self._drafts.clear()
        self._last_tool_result = None

    @property
    def conversation_count(self) -> int:
        return self._conversation.count()

    @property
    def model(self) -> str:
        return self._model

    @property
    def base_url(self) -> str:
        return self._ollama.base_url

    def _store_draft(self, result: ToolResult):
        if result.data and isinstance(result.data, dict):
            draft_id = result.data.get("draft_id", "")
            tracks = result.data.get("tracks", [])
            if draft_id and tracks:
                self._drafts[draft_id] = tracks

    def _suggest_action(self, tool_name: str,
                        result: ToolResult) -> PendingAction | None:
        if tool_name == "draft_playlist" and result.data and isinstance(result.data, dict):
            draft_id = result.data.get("draft_id", "")
            title = result.data.get("title", "Nueva playlist")
            count = result.data.get("count", 0)
            if not draft_id or not count:
                return None
            if not self._allow_reversible:
                return None
            return self._pending.create(
                tool_name="create_playlist_from_draft",
                title=f"Crear playlist: {title}",
                description=f"Se creara la playlist '{title}' con {count} canciones.",
                arguments={
                    "draft_id": draft_id,
                    "playlist_name": title,
                    "draft_tracks": self._drafts.get(draft_id, []),
                    "max_tracks": self._max_playlist_tracks,
                },
                preview={"title": title, "count": count},
                permission_level="REVERSIBLE",
                requires_confirmation=self._require_confirmation,
            )
        return None

    def _create_pending_for(self, tool_name: str, tool_args: dict,
                            result: ToolResult, user_text: str) -> PendingAction:
        titles = {
            "mark_favorite": "Marcar favoritos",
            "unmark_favorite": "Desmarcar favoritos",
            "add_tracks_to_queue": "Añadir a la cola",
            "play_track": "Reproducir cancion",
            "create_playlist_from_draft": "Crear playlist",
        }
        title = titles.get(tool_name, tool_name)

        if tool_name in ("mark_favorite", "unmark_favorite", "add_tracks_to_queue"):
            track_ids = tool_args.get("track_ids", [])
            if not track_ids and self._last_tool_result:
                track_ids = self._last_tool_result.data.get("results", []) if isinstance(self._last_tool_result.data, dict) else []
                track_ids = [t.get("id") for t in track_ids if isinstance(t, dict) and t.get("id")]
            tool_args["track_ids"] = track_ids[:self._max_action_tracks]

        return self._pending.create(
            tool_name=tool_name,
            title=title,
            arguments=tool_args,
            preview={"tool": tool_name, "args": tool_args},
            permission_level="REVERSIBLE",
            requires_confirmation=self._require_confirmation,
        )

    def _call_ollama(self, tool_result: ToolResult | None,
                     query_text: str) -> str:
        if tool_result and tool_result.success:
            safe_data = sanitize_for_prompt(tool_result.data) if isinstance(tool_result.data, (dict, list)) else tool_result.data
            tool_data = json.dumps(safe_data, ensure_ascii=False,
                                   default=str)
            user_context = (
                f"Consulta del usuario: {query_text}\n\n"
                f"Resultados de la herramienta {tool_result.name}:\n"
                f"{tool_data}\n\n"
                f"Por favor, responde en lenguaje natural basandote en estos datos. "
                f"Se conciso y directo."
            )
        else:
            user_context = sanitize_text(query_text)

        messages = self._conversation.get_for_ollama()
        msg_texts = [m.get("content", "") for m in messages]
        if SYSTEM_PROMPT not in "\n".join(msg_texts):
            messages.insert(0, {"role": "system", "content": SYSTEM_PROMPT})
        messages = _inject_context_snapshot(messages)
        messages.append({"role": "user", "content": user_context})

        return self._ollama.chat(self._model, messages)

    def _format_tool_result(self, tool_result: ToolResult) -> str:
        if not tool_result:
            return "No se pudo obtener informacion."
        if not tool_result.success:
            return tool_result.error or "Error al ejecutar la herramienta."
        if not tool_result.data:
            return "La herramienta no devolvio datos."
        return json.dumps(tool_result.data, ensure_ascii=False, indent=2,
                          default=str)

    def _format_confirmed_result(self, tool_name: str,
                                 result: ToolResult) -> str:
        if not result.success:
            return f"Error: {result.error}"
        data = result.data or {}
        if isinstance(data, dict):
            if tool_name == "create_playlist_from_draft":
                return (
                    f"Playlist creada: '{data.get('playlist_name', '')}' "
                    f"con {data.get('track_count', 0)} canciones."
                )
            if tool_name in ("mark_favorite", "unmark_favorite"):
                return f"Favoritos actualizados: {data.get('changed_count', 0)} canciones."
            if tool_name in ("add_tracks_to_queue",):
                return f"Añadidas {data.get('queued_count', 0)} canciones a la cola."
            if tool_name in ("play_track",):
                return "Reproduciendo cancion."
        return json.dumps(data, ensure_ascii=False, indent=2, default=str)

    def _detect_intent(self, text: str
                       ) -> tuple[str | None, dict, str]:
        t = text.lower().strip()

        if re.search(
            r"\b(cu[aá]nt[ao]s?\b.*\b(cancion|tema|pista|archivo|artista|album|albumes|genero|formato|duraci[oó]n|hora|minuto)|"
            r"\b(estad[ií]stica|resumen|totales?\b.*\b(biblioteca|librer[ií]a|colecci[oó]n)|"
            r"\b(qu[eé] (tan grande|tama[ñn]o|tanto|tantas)|balance)(\b|$))",
            t,
        ):
            return ("get_library_stats", {}, text)

        # Knowledge broker intents
        if re.search(
            r"\b(quien (es|fue|fueron)|(dame|dime|busca|buscar)\s+(info|informacion)\s+(de|sobre|del)\s+|"
            r"\b(explicame|expl[ií]came|cu[eé]ntame\s+(sobre|de))\s+|"
            r"\b(conoces\s+(a|al)\s+|sabes\s+(de|quien\s+es|algo\s+de))\b)",
            t,
        ):
            name = _extract_search_query(text)
            if name:
                return ("explain_artist", {"artist_name": name}, text)
            return ("lookup_artist_info", {"artist_name": _extract_entity_name(text)}, text)

        if re.search(
            r"\b(refresca|actualiza|actualizar|refresh)\s+.*\b(artista|artist|info|informacion|metadata|metadatos)\b",
            t,
        ):
            name = _extract_search_query(text)
            return ("refresh_artist_metadata", {"artist_name": name}, text)

        if re.search(
            r"\b(refresca|actualiza|actualizar|refresh)\s+.*\b(album|albumes|disco)\b",
            t,
        ):
            name = _extract_search_query(text)
            return ("refresh_album_metadata", {"album_title": name}, text)

        # Metadata review patterns
        if re.search(
            r"\b(metadata|metadatos)\s+(incomplet[oa]|faltante|vac[ií][oa]|ausente|mal[oa]|err[oó]ne[oa]|incorrect[oa]|inconsistente)\b|"
            r"\b(inconsistencias?\s+(de |en |en la |en el )?metadata)|"
            r"\b(canciones\s+(con|sin)\s+metadata)|"
            r"\b(probl[eé]mas?\s+(de |con )?(metadata|metadatos|tags|etiquetas))\b",
            t,
        ):
            return ("find_metadata_inconsistencies", {}, text)

        if re.search(
            r"\b(prop[oó]n|sugiere|revisa|corrige|completa|arregla|mejora)\s+(la\s+)?(metadata|metadatos|tags|etiquetas)\s+(de|para|del|de esta|de estas)\b|"
            r"\b(analiza|revisa|examina)\s+(la\s+)?(metadata|metadatos|tags)\s+(de|del|para)\b",
            t,
        ):
            track_ids = self._extract_track_ids_from_context()
            if track_ids:
                return ("create_metadata_review", {"track_ids": track_ids}, text)
            return ("find_metadata_inconsistencies", {}, text)

        if re.search(
            r"\b(aplica|aplicar|guardar|escribir)\s+(los|cambios|revision|metadata|metadatos)\b.*\b(confirmad[oa]|aprobad[oa]|aceptad[oa])\b|"
            r"\b(aplica\s+(los\s+)?cambios\s+(de\s+)?(metadata|metadatos|tags))\b",
            t,
        ):
            if self._last_metadata_review_id:
                return ("apply_metadata_review", {"review_id": self._last_metadata_review_id, "accepted_fields": {}}, text)
            return ("apply_metadata_review", {"review_id": "", "accepted_fields": {}}, text)

        if re.search(
            r"\b(deshaz|deshacer|revertir|revierte|undo)\s+(el|la|los)\s+(cambio|revision|metadata|metadatos)\b",
            t,
        ):
            return ("undo_metadata_review", {"review_id": ""}, text)

        # Recommendation patterns
        if re.search(
            r"\b(recomi[eé]nda(me)?|sugiere(me)?|hazme un mix|crea un mix|genera (un |una )?(mix|playlist|lista)|"
            r"\b(quiero|busco|dame|ponme)\s+(algo\s+)?(parecido|similar|como|del estilo|del tipo|que suene)\b)",
            t,
        ):
            query = _extract_search_query(text)
            if "mix" in t or "playlist" in t or "lista" in t:
                strategy = _detect_mix_strategy(t)
                return ("create_smart_mix", {"strategy": strategy, "seed": {"type": "text", "value": query}}, text)
            return ("recommend_music", {"description": query}, text)

        if re.search(
            r"\b(por qu[eé]|explica|explicame|porque)\s+(me\s+)?recomiendas\b",
            t,
        ):
            return ("explain_recommendation", {"recommendation_id": "", "track_id": 0}, text)

        if re.search(
            r"\b(guarda|guardar|crea|crear)\s+(el|la|este|esta|los|las)\s+(mix|recomendacion|playlist|lista)\b",
            t,
        ):
            return ("save_recommendation_as_playlist", {"recommendation_id": ""}, text)

        # Audio analysis patterns
        if re.search(
            r"\b(busca|buscar|encuentra)\s+(canciones?\s+)?(que\s+)?(suenen?|suena[nr]?)\s+(parecido|similar|como|igual)\b|"
            r"\b(simili?tud|parecido)\s+(sonor[ao]|ac[uú]stic[ao]|audio)\b|"
            r"\b(sonicamente\s+similar|por\s+sonido|por\s+audio)\b",
            t,
        ):
            track_ids = self._extract_track_ids_from_context()
            if track_ids:
                return ("find_sonically_similar", {"track_id": track_ids[0]}, text)
            return ("find_sonically_similar", {"track_id": 0}, text)

        if re.search(
            r"\b(analiza|analizar|examina|extrae)\s+(el\s+)?(audio|sonido|acustic[oa])\s+(de\s+)?(esta|la|el)\b|"
            r"\b(analiza\s+(esta|la)\s+cancion)\b",
            t,
        ):
            track_ids = self._extract_track_ids_from_context()
            if track_ids:
                return ("analyze_track_audio", {"track_id": track_ids[0]}, text)
            return ("analyze_track_audio", {"track_id": 0}, text)

        if re.search(
            r"\b(qu[eé]\s+)?(canciones|temas|pistas)\s+(sin\s+analizar|sin\s+features|faltan?\s+analizar|faltan?\s+features)\b|"
            r"\b(que\s+(canciones|temas)\s+faltan?\s+(por\s+)?analizar)\b",
            t,
        ):
            return ("list_tracks_missing_features", {}, text)

        if re.search(
            r"\b(qu[eé]\s+)?features\s+(tiene|hay|ac[uú]stic[ao]s?)\b|"
            r"\b(explica\s+(el\s+)?(perfil|analisis|features)\s+(ac[uú]stic[oa]|de\s+audio))\b|"
            r"\b(estado\s+(del\s+)?(analisis|audio)\s+ac[uú]stico)\b",
            t,
        ):
            return ("get_audio_analysis_status", {}, text)

        if re.search(
            r"\b(info|informacion)\s+(del|de la|del album|del disco|sobre el album|sobre el disco)\s+",
            t,
        ):
            name = _extract_search_query(text)
            return ("lookup_album_info", {"album_title": name}, text)

        if re.search(
            r"\b(sin |faltan? |falta[nr]? )(artista|album|genero|g[eé]nero|a[ñn]o|titulo|car[aá]tula|portada)\b|"
            r"\b(metadatos? (faltante|incompleto|vac[ií]o|ausente|sin))|"
            r"\b(qu[eé] (canciones|temas|pistas) (no |))tienen (artista|album|genero|a[ñn]o)\b|"
            r"\b(hay|tengo) (canciones|temas|pistas) sin\b",
            t,
        ):
            return ("find_metadata_gaps", {}, text)

        if re.search(
            r"\b(col[ao]|agreg[ao]|a[ñn]ad[ie]|pon|mete|encola)\b.*\b(col[ao]|lista|reproduccion|playback)\b|"
            r"\b(a la cola|en cola|en la cola)\b",
            t,
        ):
            track_ids = self._extract_track_ids_from_context()
            return ("add_tracks_to_queue", {"track_ids": track_ids, "play_now": False}, text)

        if re.search(
            r"\b(favoritos?|favorita|marcar|desmarc[ao]|guardar|like|corazon|estrella)\b.*\b(cancion|tema|pista)\b|"
            r"\b(marc[ao] como fav|agreg[ao] a fav|quitar de fav|desmarca)\b",
            t,
        ):
            track_ids = self._extract_track_ids_from_context()
            if "desmarca" in t or "quitar" in t or "unmark" in t:
                return ("unmark_favorite", {"track_ids": track_ids}, text)
            return ("mark_favorite", {"track_ids": track_ids}, text)

        if re.search(
            r"\b(abre|abrir|anda a|ve a|mu[eé]stra|navega|ir a|ir al|ver)\b.*\b(artista|album|albumes|genero|playlist|vista)\b|"
            r"\b(muestra (el |la |los |las ))(artista|album|genero|playlist)\b",
            t,
        ):
            if "artista" in t:
                name = _extract_search_query(text)
                return ("open_artist_view", {"artist_name": name}, text)
            if "album" in t:
                name = _extract_search_query(text)
                return ("open_album_view", {"album_name": name}, text)
            if "genero" in t or "género" in t:
                name = _extract_search_query(text)
                return ("open_genre_view", {"genre_name": name}, text)
            if "playlist" in t:
                return ("open_playlist_view", {}, text)
            return ("show_track_in_library", {}, text)

        if re.search(
            r"\b(busca[r]?|encuentra[r]?|mu[eé]stra(me)?|lista[r]?|dame|quiero (ver|escuchar|oir)|tienes? (algo|algun|alguna|musica|temas|canciones)|hay (algo|algun|alguna|musica))\b",
            t,
        ):
            query = _extract_search_query(text)
            return ("search_library", {"query": query}, text)

        if re.search(
            r"\b(playlist|lista|crea[r]?|arma[r]?|genera[r]?|haz|prepara[r]?|sugiere|recomi[eé]nda(me)?)\b.*\b(m[uú]sica|cancion|tema|pista|playlist|lista|colecci[oó]n|selecci[oó]n)\b|"
            r"\b(una (playlist|lista) (de |)([a-z]+|para)|"
            r"\b(quiero|quisiera|me gustar[ií]a) (un|una) (mix|playlist|lista|selecci[oó]n|colecci[oó]n)\b|"
            r"\b(sugiere|recomienda|dame|haz) (algo|musica|canciones|temas|pistas)\b",
            t,
        ):
            filters = {}
            for genre_keyword in [
                "rock", "pop", "jazz", "classical", "electronica",
                "electro", "techno", "house", "metal", "hip hop", "rap",
                "latin", "ambient", "folk", "blues", "reggae", "soul",
                "funk", "punk", "indie", "alternativo", "acustico",
            ]:
                if genre_keyword in t:
                    filters["genre"] = genre_keyword
                    break
            return ("draft_playlist", {"description": text, "filters": filters}, text)

        if re.search(
            r"\b(recomi[eé]nda|sugiere|similar|parecid[oa]|como |estilo de)\b",
            t,
        ):
            query = _extract_search_query(text)
            return ("recommend_local_tracks", {"seed_text": query}, text)

        return (None, {}, text)

    def _extract_track_ids_from_context(self) -> list[int]:
        ids: list[int] = []
        if self._last_tool_result and self._last_tool_result.success:
            data = self._last_tool_result.data
            if isinstance(data, dict):
                results = data.get("results", [])
                for item in results:
                    if isinstance(item, dict) and item.get("id"):
                        ids.append(item["id"])
        return ids[:self._max_action_tracks]


def _extract_search_query(text: str) -> str:
    prefixes = [
        "buscar", "busca", "encuentra", "muestrame", "muéstrame",
        "dame", "lista", "listar", "que tengo de", "quiero escuchar",
        "quiero ver", "quiero oir", "hay algo de", "tienes de",
        "busca canciones de", "busca musica de", "abre", "abrir",
        "anda a", "ve a", "muestra", "navega a", "ir a",
        "refresca", "actualiza", "refresh", "explicame", "cuentame",
        "cuentame sobre", "cuentame de", "dame info de", "informacion de",
        "informacion sobre", "info de", "info del", "info sobre",
    ]
    lower = text.lower()
    for prefix in prefixes:
        idx = lower.find(prefix)
        if idx >= 0:
            return text[idx + len(prefix):].strip().rstrip("?.,!")
    return text.strip().rstrip("?.,!")


def _extract_entity_name(text: str) -> str:
    """Extract artist/album name from knowledge queries."""
    lower = text.lower()
    patterns = [
        r"(?:quien (?:es|fue|fueron) )(.+)",
        r"(?:explicame|expl[ií]came) (?:sobre |de |a |al )?(.+)",
        r"(?:dame|dime|busca|buscar) (?:info|informacion) (?:de |sobre |del )(.+)",
        r"(?:cu[eé]ntame) (?:sobre |de )(.+)",
        r"(?:refresca|actualiza|refresh) (?:el |la |los |las |info de |informacion de )?(.+)",
    ]
    for pat in patterns:
        m = re.search(pat, lower)
        if m:
            return m.group(1).strip().rstrip("?.,!")
    return _extract_search_query(text)


def _detect_mix_strategy(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ("viaje", "journey", "genero", "género")):
        return "genre_journey"
    if any(w in t for w in ("decada", "década", "años", "anos", "90", "80", "70")):
        return "decade_mix"
    if any(w in t for w in ("flac", "lossless", "alta calidad", "calidad")):
        return "lossless_showcase"
    if any(w in t for w in ("favorito", "favorita", "favoritos")):
        return "favorites_neighbors"
    if any(w in t for w in ("perdiste", "olvidada", "hace tiempo", "no escucho")):
        return "recently_missed"
    if any(w in t for w in ("profund", "ocult", "escondid", "rareza")):
        return "deep_cuts"
    if any(w in t for w in ("descubr", "nuevo", "nueva", "explor")):
        return "discovery"
    return "balanced_mix"


def _pending_to_dict(p: PendingAction) -> dict:
    return {
        "action_id": p.action_id,
        "tool_name": p.tool_name,
        "title": p.title,
        "description": p.description,
        "preview": p.preview,
        "permission_level": p.permission_level,
        "requires_confirmation": p.requires_confirmation,
    }
