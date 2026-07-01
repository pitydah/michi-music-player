"""MichiAIInsightService — generate deterministic insights without LLM.

Each insight suggests a tool or plan. Insights are derived from the snapshot.
"""

from __future__ import annotations

from typing import Any


class MichiAIInsightService:
    def generate(self, snapshot: dict[str, Any], audio_intel=None, db=None) -> list[dict[str, Any]]:
        insights: list[dict[str, Any]] = []
        health = snapshot.get("library_health", {})
        playback = snapshot.get("playback", {})
        sync = snapshot.get("sync", {})
        selection = snapshot.get("selection", {})
        if audio_intel is not None:
            ai_insights = audio_intel.generate_audio_intelligence_insights(db=db)
            insights.extend(ai_insights)

        if health.get("track_count", 0) == 0:
            insights.append(self._insight("empty_library", "info", "Biblioteca vacia", "Agrega musica para comenzar.", "library", "search_library"))

        mm = health.get("missing_metadata_count", 0)
        if mm > 0:
            insights.append(self._insight("missing_metadata", "warning", "Metadatos incompletos", f"{mm} canciones con metadatos incompletos.", "library", "list_missing_metadata"))

        mc = health.get("missing_cover_count", 0)
        if mc > 0:
            insights.append(self._insight("missing_covers", "warning", "Caratulas faltantes", f"{mc} albumes sin caratula.", "library", "list_missing_metadata"))

        if not sync.get("active", False):
            insights.append(self._insight("sync_disabled", "info", "Sync desactivado", "Activa la sincronizacion para conectar dispositivos moviles.", "sync", "start_sync"))
        elif sync.get("peers", 0) == 0:
            insights.append(self._insight("no_sync_peers", "info", "Sin dispositivos conectados", "No hay dispositivos emparejados via Sync.", "sync", "prepare_mobile_sync"))

        scope = selection.get("scope")
        if scope in ("track", "album", "artist", "genre", "playlist", "search"):
            insights.append(self._insight("selection_playable", "info", "Seleccion accionable", "Puedes crear una playlist o encolar la seleccion actual.", "library", "create_playlist_from_selection"))

        if playback.get("now_playing"):
            insights.append(self._insight("now_playing", "info", "Reproduciendo", "Hay una pista en reproduccion.", "playback", "summarize_current_selection"))

        return insights

    @staticmethod
    def _insight(insight_id: str, severity: str, title: str, description: str, source: str, suggested_action: str) -> dict[str, Any]:
        return {
            "id": insight_id,
            "severity": severity,
            "title": title,
            "description": description,
            "source": source,
            "suggested_action": suggested_action,
            "requires_confirmation": False,
        }
