from __future__ import annotations

import time
from datetime import datetime, timezone

from michi_ai.v2.core.models import ContextSnapshot, Suggestion


class SuggestionEngineV2:
    def __init__(self) -> None:
        self._dismissed: dict[str, float] = {}

    def generate(self, snapshot: ContextSnapshot, available_capabilities: dict[str, bool] | None = None) -> list[Suggestion]:
        caps = available_capabilities or {}
        suggestions: list[Suggestion] = []
        datetime.now(timezone.utc)

        lib = snapshot.library or {}
        playback = snapshot.playback or {}
        queue = snapshot.queue or {}
        devices = snapshot.devices or {}

        track_count = lib.get("track_count", 0)
        missing_meta = lib.get("missing_metadata_count", 0)
        now_playing = playback.get("now_playing")
        queue_count = queue.get("count", 0)

        if track_count == 0 and caps.get("library_doctor.scan", False):
            suggestions.append(self._make(
                "library_empty", "Biblioteca vacía",
                "Agrega música escaneando tus carpetas de música.",
                reason="No hay archivos en la biblioteca",
                priority=1, action="scan_library_health",
            ))

        if missing_meta > 0 and caps.get("metadata.read", False):
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

        missing_features = lib.get("tracks_without_audio_features", 0)
        if missing_features and missing_features > 0 and caps.get("audio_lab.analyze", False):
            suggestions.append(self._make(
                "audio_features_missing", f"Análisis pendiente ({missing_features})",
                f"Hay {missing_features} pistas sin analizar.",
                reason="Audio Lab pendiente",
                priority=6, action="list_tracks_missing_features",
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
