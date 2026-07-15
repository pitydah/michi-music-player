from __future__ import annotations

import time

from michi_ai.v2.core.models import ContextSnapshot, Suggestion


class SuggestionEngineV2:
    def __init__(self) -> None:
        self._dismissed: dict[str, float] = {}

    def generate(self, snapshot: ContextSnapshot, available_capabilities: dict[str, bool] | None = None) -> list[Suggestion]:
        caps = available_capabilities or {}
        suggestions: list[Suggestion] = []

        lib = snapshot.library or {}
        playback = snapshot.playback or {}
        queue = snapshot.queue or {}
        devices = snapshot.devices or {}
        selection = snapshot.selection or {}
        jobs = snapshot.jobs or {}

        track_count = lib.get("track_count", 0)
        missing_meta = lib.get("missing_metadata_count", 0)
        now_playing = playback.get("now_playing")
        queue_count = queue.get("count", 0)
        active_section = snapshot.active_section
        active_entity = snapshot.active_entity or {}
        selection_tracks = selection.get("track_ids", [])
        active_jobs = jobs.get("active", [])

        if track_count == 0 and caps.get("library_doctor.scan", False):
            suggestions.append(self._make(
                "library_empty", "Biblioteca vacía",
                "Agrega música escaneando tus carpetas de música.",
                reason="No hay archivos en la biblioteca",
                priority=1, action="scan_library_health",
            ))

        if selection_tracks and caps.get("playlist.modify", False):
            suggestions.append(self._make(
                "selection_to_playlist", f"{len(selection_tracks)} seleccionados",
                f"Crear playlist con {len(selection_tracks)} canciones seleccionadas.",
                reason="Selección activa",
                priority=2, action="create_playlist",
            ))

        if missing_meta and missing_meta > 0 and caps.get("metadata.read", False):
            suggestions.append(self._make(
                "metadata_gaps", f"Metadatos incompletos ({missing_meta})",
                f"Hay {missing_meta} archivos con metadatos faltantes.",
                reason="Calidad de biblioteca",
                priority=3, action="find_metadata_gaps",
            ))

        if devices and devices.get("device_count", 0) > 0:
            suggestions.append(self._make(
                "device_connected", "Dispositivo conectado",
                "Hay un dispositivo disponible para sincronización.",
                reason="Dispositivo detectado",
                priority=5, action="list_devices",
            ))

        if not now_playing and track_count > 0:
            suggestions.append(self._make(
                "nothing_playing", "Nada en reproducción",
                "Tu biblioteca tiene música lista para reproducir.",
                reason="Reproducción inactiva",
                priority=4, action="play_track",
            ))

        if queue_count == 0 and now_playing:
            suggestions.append(self._make(
                "queue_empty", "Cola vacía",
                "Agrega más canciones a la cola para reproducción continua.",
                reason="Cola vacía",
                priority=5, action="add_to_queue",
            ))

        if active_entity and active_entity.get("type") in ("album", "artist") and caps.get("playback.control", False):
            suggestions.append(self._make(
                "play_active_entity", f"Reproducir {active_entity['type']}",
                f"Reproducir {active_entity.get('name', 'selección actual')}.",
                reason="Entidad activa",
                priority=4, action="play_album" if active_entity["type"] == "album" else "play_artist",
            ))

        if active_jobs and caps.get("diagnostics.read", False):
            count = len(active_jobs) if isinstance(active_jobs, list) else 1
            suggestions.append(self._make(
                "active_jobs", f"{count} trabajo(s) activo(s)",
                "Hay trabajos en ejecución. Revisa su progreso.",
                reason="Trabajos activos",
                priority=5, action="list_jobs",
            ))

        missing_features = lib.get("tracks_without_audio_features", 0)
        if missing_features and missing_features > 0 and caps.get("audio_lab.analyze", False):
            suggestions.append(self._make(
                "audio_features_missing", f"Análisis pendiente ({missing_features})",
                f"Hay {missing_features} pistas sin analizar.",
                reason="Audio Lab pendiente",
                priority=6, action="list_tracks_missing_features",
            ))

        if active_section and caps.get("navigation.request", False):
            suggestions.append(self._make(
                "navigate_back", "Volver",
                f"Volver desde {active_section.replace('_', ' ')}.",
                reason="Navegación",
                priority=7, action="navigate",
            ))

        suggestions.sort(key=lambda s: s.priority)
        return self._filter_dismissed(suggestions)

    def dismiss(self, suggestion_id: str, ttl_seconds: int = 3600) -> bool:
        self._dismissed[suggestion_id] = time.monotonic() + ttl_seconds
        return True

    def is_dismissed(self, suggestion_id: str) -> bool:
        expiry = self._dismissed.get(suggestion_id, 0)
        if expiry == 0:
            return False
        if time.monotonic() > expiry:
            del self._dismissed[suggestion_id]
            return False
        return True

    def clear_dismissed(self) -> None:
        self._dismissed.clear()

    def _make(self, id: str, title: str, description: str, reason: str = "", priority: int = 5, action: str = "") -> Suggestion:
        dedup_key = f"{id}:{action}" if action else id
        return Suggestion(
            id=id, title=title, description=description,
            reason=reason, priority=priority, action=action,
            deduplication_key=dedup_key,
        )

    def _filter_dismissed(self, suggestions: list[Suggestion]) -> list[Suggestion]:
        return [s for s in suggestions if not self.is_dismissed(s.id)]
