"""AssistantSuggestionsHomeBuilder — builds AssistantSuggestion list."""
from __future__ import annotations

import logging
import os
from typing import Any

from core.home.home_status import AssistantSuggestion, LibraryHomeStatus, PlaybackHomeStatus

logger = logging.getLogger("michi.home.builders.suggestions")

_DESTRUCTIVE_ROUTES = frozenset({
    "metadata_editor", "audio_lab_artwork", "audio_lab_organize",
    "audio_lab_conversion", "audio_lab_intelligence",
})

_VALID_ROUTES = frozenset({
    "library_hub", "mix_hub", "metadata_editor", "audio_lab_artwork",
    "audio_lab_intelligence", "audio_lab_diagnostics", "connections_hub",
    "devices_page", "assistant",
})


def build_assistant_suggestions(
    library: LibraryHomeStatus,
    playback: PlaybackHomeStatus,
    context_svc: Any = None,
) -> list[AssistantSuggestion]:
    suggestions: list[AssistantSuggestion] = []
    safe_mode = os.environ.get("MICHI_SAFE_MODE") == "1"

    if context_svc is not None:
        try:
            snap = context_svc.get_assistant_snapshot()
            if snap and "suggested_actions" in snap:
                for act in snap["suggested_actions"][:3]:
                    route = act.get("route", "")
                    if safe_mode and route not in _VALID_ROUTES:
                        continue
                    suggestions.append(AssistantSuggestion(
                        title=act.get("label", act.get("title", "")),
                        message=act.get("description", ""),
                        target_route=route if route in _VALID_ROUTES else "assistant",
                        action_kind=act.get("kind", "navigate"),
                        requires_confirmation=route in _DESTRUCTIVE_ROUTES,
                        priority=act.get("priority", 0),
                    ))
                if suggestions:
                    return suggestions[:3]
        except Exception:
            logger.debug("Assistant snapshot unavailable")

    if library.missing_metadata_count > 0:
        suggestions.append(AssistantSuggestion(
            title="Limpiar metadatos",
            message=f"{library.missing_metadata_count} canciones con metadatos incompletos",
            target_route="metadata_editor", action_kind="navigate",
            requires_confirmation=True, priority=10,
        ))

    if library.missing_cover_count > 0 and not safe_mode:
        suggestions.append(AssistantSuggestion(
            title="Buscar caratulas",
            message=f"{library.missing_cover_count} albumes sin caratula",
            target_route="audio_lab_artwork", action_kind="navigate",
            requires_confirmation=True, priority=8,
        ))

    if library.tracks_without_audio_features > 0 and not safe_mode:
        suggestions.append(AssistantSuggestion(
            title="Analizar biblioteca",
            message=f"{library.tracks_without_audio_features} canciones sin perfil acustico",
            target_route="audio_lab_intelligence", action_kind="navigate",
            requires_confirmation=True, priority=7,
        ))

    if library.track_count > 0 and not playback.can_continue:
        suggestions.append(AssistantSuggestion(
            title="Explorar biblioteca",
            message="Descubre nueva musica en tu biblioteca",
            target_route="library_hub", action_kind="navigate", priority=5,
        ))

    if not suggestions and library.track_count > 0:
        suggestions.append(AssistantSuggestion(
            title="Crear mix de novedades",
            message="Genera un mix automatico con canciones recien agregadas",
            target_route="mix_hub", action_kind="navigate", priority=3,
        ))

    if not suggestions:
        suggestions.append(AssistantSuggestion(
            title="Anadir musica",
            message="Agrega carpetas o archivos para comenzar",
            target_route="library_hub", action_kind="navigate", priority=1,
        ))

    return suggestions[:3]
