"""MixBridge — thin QML adapter over MixService generation via durable jobs.

The bridge owns NO generation business logic: strategies, deduplication,
limits and statuses live in ``MixService`` (single facade).  The bridge
converts QML params into a durable job payload (``mix_generate``,
owner ``mix``), exposes the job lifecycle as a state, and adapts the
canonical result to the QML shape.  Cancellation is scoped to the bridge's
OWN current job id — never ``cancel_all`` (Fase Jobs / Fase Mix).
"""
from __future__ import annotations

import json
import logging
from enum import Enum
from typing import Any

from PySide6.QtCore import QObject, Signal, Property, Slot

from core.mix.models import MixGenerationStatus

logger = logging.getLogger("michi.mix")


class MixErrorCode:
    EMPTY_RESULT = "EMPTY_RESULT"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    QUERY_FAILED = "QUERY_FAILED"
    CANCELLED = "CANCELLED"
    INVALID_STATE = "INVALID_STATE"
    UNKNOWN_CATEGORY = "UNKNOWN_CATEGORY"
    NO_MIX_SELECTED = "NO_MIX_SELECTED"
    EMPTY_MIX = "EMPTY_MIX"
    NO_PLAYBACK = "NO_PLAYBACK"
    EMPTY_NAME = "EMPTY_NAME"
    NO_PLAYLIST_SERVICE = "NO_PLAYLIST_SERVICE"
    CREATE_FAILED = "CREATE_FAILED"
    SAVE_FAILED = "SAVE_FAILED"
    INVALID_INDEX = "INVALID_INDEX"
    NAVIGATION_UNAVAILABLE = "NAVIGATION_UNAVAILABLE"


class MixState(Enum):
    """Bridge lifecycle + canonical generation outcomes (single machine).

    The outcome states are EXACTLY the canonical MixGenerationStatus
    values: the QML-visible state is 1:1 with the service result
    (``status_to_qml_state``), so an empty outcome is never shown as ok.
    """

    IDLE = "IDLE"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED_WITH_TRACKS = "COMPLETED_WITH_TRACKS"
    PARTIAL_RECOMMENDATION = "PARTIAL_RECOMMENDATION"
    NO_MATCHES = "NO_MATCHES"
    EMPTY_LIBRARY = "EMPTY_LIBRARY"
    INVALID_STRATEGY = "INVALID_STRATEGY"
    GENERATOR_UNAVAILABLE = "GENERATOR_UNAVAILABLE"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


_CANONICAL_STATUSES = frozenset(s.value for s in MixGenerationStatus)


def status_to_qml_state(status: str) -> str:
    """Map a canonical MixGenerationStatus to the QML-visible state (1:1).

    Every canonical status maps to exactly one QML state and no two
    statuses share a state; unknown/empty statuses are FAILED.
    """
    if status in _CANONICAL_STATUSES:
        return status
    return MixState.FAILED.value


MIX_CATEGORIES = [
    {"id": "favorites", "title": "Favoritos", "icon": "FV",
     "desc": "Tus canciones marcadas como favoritas",
     "reason": "Reúne lo que marcaste con corazón para volver a ello rápido",
     "origin": "Michi", "updated": "Se actualiza al marcar favoritos",
     "action": "Reproducir favoritos"},
    {"id": "recent", "title": "Escuchadas recientemente", "icon": "RC",
     "desc": "Canciones reproducidas recientemente",
     "reason": "Para retomar lo que escuchaste en los últimos días",
     "origin": "Michi", "updated": "Se actualiza con cada reproducción",
     "action": "Reproducir recientes"},
    {"id": "most_played", "title": "Mas escuchadas", "icon": "MP",
     "desc": "Tus canciones con mas reproducciones",
     "reason": "Tu historia de escucha ordenada por reproducciones",
     "origin": "Michi", "updated": "Se actualiza con tu historial",
     "action": "Reproducir más escuchadas"},
    {"id": "unplayed", "title": "No escuchadas", "icon": "UN",
     "desc": "Canciones que aun no has reproducido",
     "reason": "Descubre lo que tienes en la biblioteca y nunca sonó",
     "origin": "Michi", "updated": "Se actualiza al reproducir",
     "action": "Descubrir pendientes"},
    {"id": "rediscovery", "title": "Redescubrimiento", "icon": "RD",
     "desc": "Canciones antiguas que no escuchas hace tiempo",
     "reason": "Rescata joyas olvidadas de tu propia colección",
     "origin": "Michi", "updated": "Se actualiza con tu historial",
     "action": "Redescubrir"},
    {"id": "daily_mix", "title": "Mix diario", "icon": "MX",
     "desc": "Recomendaciones basadas en tu historial",
     "reason": "Combina lo reciente con lo pendiente para cada día",
     "origin": "Michi", "updated": "Se regenera cada día",
     "action": "Escuchar mix diario"},
    {"id": "by_artist", "title": "Por artista", "icon": "AR",
     "desc": "Mixes centrados en un artista",
     "reason": "Profundiza en un artista concreto de tu colección",
     "origin": "Tú", "updated": "Se genera al elegir artista",
     "action": "Elegir artista"},
    {"id": "by_genre", "title": "Por genero", "icon": "GN",
     "desc": "Mixes por genero musical",
     "reason": "Explora un género de tu biblioteca en profundidad",
     "origin": "Tú", "updated": "Se genera al elegir género",
     "action": "Elegir género"},
    {"id": "by_decade", "title": "Por decada", "icon": "DC",
     "desc": "Mixes por decada",
     "reason": "Viaja por las épocas de tu colección",
     "origin": "Tú", "updated": "Se genera al elegir década",
     "action": "Elegir década"},
    {"id": "by_year", "title": "Por ano", "icon": "YR",
     "desc": "Mixes por ano especifico",
     "reason": "Escucha todo lo que tienes de un año concreto",
     "origin": "Tú", "updated": "Se genera al elegir año",
     "action": "Elegir año"},
    {"id": "high_quality", "title": "Alta calidad", "icon": "HQ",
     "desc": "Solo pistas con bitrate >= 320 kbps",
     "reason": "Para escucha crítica con tu mejor equipo",
     "origin": "Michi", "updated": "Se actualiza al indexar",
     "action": "Escuchar en alta calidad"},
    {"id": "custom", "title": "Mix personalizado", "icon": "CS",
     "desc": "Mix basado en reglas definidas por ti",
     "reason": "Tú defines artista, género, década o carpeta",
     "origin": "Tú", "updated": "Se genera con tus reglas",
     "action": "Crear mix personalizado"},
]


class MixBridge(QObject):
    """Expose mix generation while delegating playback to QueueService."""

    dataChanged = Signal()
    generationProgress = Signal(int, int)
    generationError = Signal(str)
    stateChanged = Signal(str)

    def __init__(self, mix_service: Any = None, job_service: Any = None,
                 action_registry: Any = None, navigation_bridge: Any = None,
                 page_state_store: Any = None, capability_bridge: Any = None,
                 accessibility_bridge: Any = None, playlist_service: Any = None,
                  playback_service: Any = None, queue_service: Any = None,
                  query_executor: Any = None, parent: QObject | None = None,
                  **legacy_kwargs) -> None:
        super().__init__(parent)
        # Retained for bridge-factory and caller compatibility; generation
        # runs through the durable job service, never through these.
        self._mix_svc = mix_service
        if self._mix_svc is None and "query_service" in legacy_kwargs:
            self._mix_svc = legacy_kwargs["query_service"]
        self._job_svc = job_service
        self._nav = navigation_bridge
        self._page_state = page_state_store
        self._playlist_svc = playlist_service
        if self._playlist_svc is None and "playlist_bridge" in legacy_kwargs:
            self._playlist_svc = legacy_kwargs["playlist_bridge"]
        self._queue_svc = queue_service

        self._state = MixState.IDLE
        self._current_mix_id = ""
        self._current_mix_title = ""
        self._config_params = ""
        self._current_songs: list[dict] = []
        self._result_mix_id = ""
        self._error_message = ""
        self._generation = 0
        self._validation_errors: list[str] = []
        # The only durable job this bridge may cancel: its own current
        # generation job (never other domains' jobs — no cancel_all).
        self._job_id = ""

        if self._job_svc is not None:
            self._job_svc.jobCompleted.connect(self._on_job_completed)
            self._job_svc.jobFailed.connect(self._on_job_failed)
            self._job_svc.jobCancelled.connect(self._on_job_cancelled)

    @property
    def state(self) -> MixState:
        return self._state

    def _set_state(self, new_state: MixState) -> None:
        if self._state != new_state:
            self._state = new_state
            self.stateChanged.emit(new_state.value)
            self.dataChanged.emit()

    @Property(str, notify=stateChanged)
    def stateName(self):
        return self._state.value

    @Property("QVariantList", notify=dataChanged)
    def categories(self):
        return list(MIX_CATEGORIES)

    @Property("QVariantList", notify=dataChanged)
    def currentSongs(self):
        return self._current_songs

    @Property(str, notify=dataChanged)
    def currentMixTitle(self):
        return self._current_mix_title

    @Property(str, notify=dataChanged)
    def errorMessage(self):
        return self._error_message

    @Property(str, notify=dataChanged)
    def currentMixId(self):
        return self._current_mix_id

    @Property("QVariantList", notify=dataChanged)
    def validationErrors(self):
        return self._validation_errors

    # ── Configuration (param conversion only) ─────────────────────────────

    @Slot(str, result=dict)
    def configure(self, mix_id: str, params: str = "") -> dict[str, Any]:
        """Select a category and store the raw QML params (converted later)."""
        category = next((c for c in MIX_CATEGORIES if c["id"] == mix_id), None)
        if not category:
            self._error_message = f"Categoria '{mix_id}' no encontrada"
            self._set_state(MixState.FAILED)
            return {"ok": False, "error_code": MixErrorCode.UNKNOWN_CATEGORY}
        self._current_mix_id = mix_id
        self._current_mix_title = category["title"]
        self._config_params = params
        self._error_message = ""
        self._validation_errors = []
        self.dataChanged.emit()
        return {"ok": True, "mix_id": mix_id, "title": category["title"]}

    @Slot(result=dict)
    def validate(self) -> dict[str, Any]:
        self._validation_errors = []
        if not self._current_mix_id:
            self._validation_errors.append("No se selecciono ningun mix")
            self._set_state(MixState.FAILED)
            return {"ok": False, "error_code": MixErrorCode.NO_MIX_SELECTED,
                    "errors": self._validation_errors}
        if self._mix_svc is None:
            self._validation_errors.append("Servicio de mix no disponible")
            self._set_state(MixState.FAILED)
            return {"ok": False, "error_code": MixErrorCode.SERVICE_UNAVAILABLE,
                    "errors": self._validation_errors}
        return {"ok": True, "valid": True}

    def _to_job_params(self, mix_id: str, params: str) -> dict[str, Any]:
        """Convert the raw QML params into the job payload (seed + limit).

        Pure param conversion: the strategy is the category id itself —
        MixService owns every strategy (single facade).
        """
        seed: dict[str, Any] = {}
        limit = 30
        if params:
            try:
                data = json.loads(params) if isinstance(params, str) else params
                if isinstance(data, dict):
                    seed = {k: v for k, v in data.items() if k != "limit"}
                    try:
                        limit = int(data.get("limit") or 30)
                    except (TypeError, ValueError):
                        limit = 30
            except Exception:
                seed = {}
        return {"strategy": mix_id, "seed": seed, "limit": limit}

    # ── Generation (durable job) ──────────────────────────────────────────

    @Slot(result=dict)
    def generate(self) -> dict[str, Any]:
        """Submit a durable mix_generate job and return {ok, job_id, state}.

        NEVER runs generation synchronously: the job service executes the
        MixService port; completion arrives through jobCompleted.
        """
        if not self._current_mix_id:
            return {"ok": False, "error_code": MixErrorCode.NO_MIX_SELECTED,
                    "state": self._state.value}
        if self._job_svc is None:
            self._error_message = "Servicio de jobs no disponible"
            self._set_state(MixState.FAILED)
            return {"ok": False, "error_code": MixErrorCode.SERVICE_UNAVAILABLE,
                    "state": self._state.value}
        payload = self._to_job_params(self._current_mix_id, self._config_params)
        self._generation += 1
        gen = self._generation
        self._current_songs = []
        self._result_mix_id = ""
        self._error_message = ""
        self._set_state(MixState.QUEUED)
        try:
            job_id = self._job_svc.create_job(
                "mix_generate", owner="mix", payload=payload)
        except Exception as e:
            self._error_message = f"No se pudo crear el job de generación: {e}"
            self._set_state(MixState.FAILED)
            return {"ok": False, "error_code": MixErrorCode.QUERY_FAILED,
                    "detail": self._error_message, "state": self._state.value}
        self._job_id = job_id
        self._set_state(MixState.RUNNING)
        try:
            started = self._job_svc.start_job(job_id)
        except Exception as e:
            self._error_message = f"No se pudo iniciar el job de generación: {e}"
            self._job_id = ""
            self._set_state(MixState.FAILED)
            return {"ok": False, "error_code": MixErrorCode.QUERY_FAILED,
                    "detail": self._error_message, "state": self._state.value}
        if not started:
            self._set_state(MixState.QUEUED)
        return {"ok": True, "job_id": job_id, "state": self._state.value,
                "generation": gen}

    @Slot(str, result=dict)
    @Slot(str, str, result=dict)
    def loadMix(self, mix_id: str, seed: str = "") -> dict[str, Any]:
        cfg = self.configure(mix_id, seed)
        if not cfg.get("ok"):
            return cfg
        val = self.validate()
        if not val.get("ok"):
            return val
        return self.generate()

    @Slot(result=dict)
    def regenerate(self) -> dict[str, Any]:
        if not self._current_mix_id:
            return {"ok": False, "error_code": MixErrorCode.NO_MIX_SELECTED,
                    "state": self._state.value}
        return self.generate()

    @Slot(result=dict)
    def cancelGeneration(self) -> dict[str, Any]:
        # Scope: cancel ONLY this bridge's current job id — never jobs of
        # other domains (P0 Fase Jobs: cancel_all was collateral damage).
        if self._job_svc is not None and self._job_id:
            if self._job_svc.get_job(self._job_id) is not None:
                self._job_svc.cancel_job(self._job_id)
            self._job_id = ""
        gen = self._generation
        self._generation += 1
        self._current_songs = []
        self._error_message = ""
        self._set_state(MixState.CANCELLED)
        return {"ok": True, "cancelled": gen}

    # ── Job event handlers (stale-guarded by the current job id) ──────────

    def _on_job_completed(self, job_id: str, result: Any) -> None:
        if job_id != self._job_id:
            return
        self._job_id = ""
        result = result if isinstance(result, dict) else {}
        status = str(result.get("status", "") or "")
        state = status_to_qml_state(status)
        tracks = list(result.get("tracks") or [])
        ok = bool(result.get("ok"))
        self._current_songs = tracks
        self._result_mix_id = str(result.get("mix_id", "") or "")
        if ok and tracks:
            self._error_message = ""
            if self._page_state:
                self._page_state.set("mix_last_result", {
                    "mix_id": self._current_mix_id,
                    "count": len(tracks),
                    "generation": self._generation,
                })
            if self.generationProgress:
                self.generationProgress.emit(len(tracks), len(tracks))
        else:
            self._error_message = str(result.get("message", "") or "")
            if self._error_message:
                self.generationError.emit(self._error_message)
        try:
            self._set_state(MixState(state))
        except ValueError:
            self._set_state(MixState.FAILED)

    def _on_job_failed(self, job_id: str, error: str) -> None:
        if job_id != self._job_id:
            return
        self._job_id = ""
        self._current_songs = []
        self._error_message = str(error) or "Error de generación"
        self.generationError.emit(self._error_message)
        self._set_state(MixState.FAILED)

    def _on_job_cancelled(self, job_id: str) -> None:
        if job_id != self._job_id:
            return
        self._job_id = ""
        self._current_songs = []
        self._error_message = "Generación cancelada"
        self._set_state(MixState.CANCELLED)

    # ── Rules (delegated to the service) ──────────────────────────────────

    @Slot(str, result=dict)
    def saveRules(self, rules_json: str) -> dict[str, Any]:
        if self._mix_svc is None:
            return {"ok": False, "error": "SERVICE_UNAVAILABLE"}
        mix_id = self._current_mix_id or "custom"
        return self._mix_svc.save_rules(mix_id, rules_json)

    @Slot(str, result=dict)
    def previewRules(self, rules_json: str) -> dict[str, Any]:
        if self._mix_svc is None:
            return {"ok": False, "error": "SERVICE_UNAVAILABLE"}
        return self._mix_svc.preview_rules(rules_json, limit=10)

    @Slot(str, result=dict)
    def loadRules(self, mix_id: str) -> dict[str, Any]:
        if self._mix_svc is None:
            return {"ok": False, "error": "SERVICE_UNAVAILABLE"}
        return self._mix_svc.load_rules(mix_id)

    @Slot(result=dict)
    def listRules(self) -> dict[str, Any]:
        if self._mix_svc is None:
            return {"ok": False, "error": "SERVICE_UNAVAILABLE", "mixes": []}
        return self._mix_svc.list_rules()

    @Slot(str, result=dict)
    def deleteRules(self, mix_id: str) -> dict[str, Any]:
        if self._mix_svc is None:
            return {"ok": False, "error": "SERVICE_UNAVAILABLE"}
        return self._mix_svc.delete_rules(mix_id)

    @Slot(result=dict)
    def reset(self) -> dict[str, Any]:
        self._current_mix_id = ""
        self._current_mix_title = ""
        self._current_songs = []
        self._result_mix_id = ""
        self._error_message = ""
        self._validation_errors = []
        self._set_state(MixState.IDLE)
        return {"ok": True}

    # ── Playback / queue (delegated) ──────────────────────────────────────

    @Slot(result=dict)
    def playMix(self) -> dict[str, Any]:
        if not self._current_songs:
            return {"ok": False, "error_code": MixErrorCode.EMPTY_MIX}
        if not self._queue_svc:
            return {"ok": False, "error_code": MixErrorCode.NO_PLAYBACK}
        return self._queue_svc.replace_and_play(self._current_songs, 0)

    @Slot(result=dict)
    def enqueueMix(self) -> dict[str, Any]:
        if not self._current_songs:
            return {"ok": False, "error_code": MixErrorCode.EMPTY_MIX}
        if not self._queue_svc:
            return {"ok": False, "error_code": MixErrorCode.NO_PLAYBACK}
        return self._queue_svc.enqueue(self._current_songs, play_now=False)

    @Slot(str, result=dict)
    def saveMixAsPlaylist(self, name: str) -> dict[str, Any]:
        """Save the generated mix as a playlist via MixService (single owner).

        Falls back to the direct playlist service only when no MixService
        is wired; both paths use the REAL playlist id from
        ``create()["id"]`` — never a dict — and never report an empty save
        as a full success.
        """
        if not name:
            return {"ok": False, "error_code": MixErrorCode.EMPTY_NAME}
        if not self._current_songs:
            return {"ok": False, "error_code": MixErrorCode.EMPTY_MIX}
        if self._mix_svc is not None and hasattr(self._mix_svc,
                                                 "save_mix_as_playlist"):
            mix_id = self._result_mix_id or self._current_mix_id
            return self._mix_svc.save_mix_as_playlist(mix_id, name)
        if not self._playlist_svc:
            return {"ok": False, "error_code": MixErrorCode.NO_PLAYLIST_SERVICE}
        try:
            created = self._playlist_svc.create(name)
        except Exception as e:
            return {"ok": False, "error_code": MixErrorCode.CREATE_FAILED,
                    "detail": str(e)}
        if isinstance(created, dict):
            if not created.get("ok"):
                return {"ok": False, "error_code": MixErrorCode.CREATE_FAILED}
            playlist_id = created.get("id")
        else:
            playlist_id = created
        if playlist_id is None or isinstance(playlist_id, dict):
            return {"ok": False, "error_code": MixErrorCode.CREATE_FAILED,
                    "detail": "Id de playlist inválido"}
        added = 0
        failed = 0
        for s in self._current_songs:
            tid = s.get("track_id") or s.get("id")
            if not tid:
                failed += 1
                continue
            try:
                add_result = self._playlist_svc.add_track(playlist_id, tid)
                if isinstance(add_result, dict) and not add_result.get("ok"):
                    failed += 1
                else:
                    added += 1
            except Exception:
                failed += 1
        if added == 0:
            return {"ok": False, "error_code": MixErrorCode.SAVE_FAILED,
                    "requested": len(self._current_songs), "added": 0,
                    "failed": len(self._current_songs)}
        status = "PARTIAL_SUCCESS" if failed else "COMPLETED"
        return {"ok": True, "status": status, "playlist_id": playlist_id,
                "count": added, "requested": len(self._current_songs),
                "added": added, "failed": failed}

    @Slot(int, result=dict)
    def playFromIndex(self, index: int) -> dict[str, Any]:
        if not self._current_songs or index < 0 or index >= len(self._current_songs):
            return {"ok": False, "error_code": MixErrorCode.INVALID_INDEX}
        if not self._queue_svc:
            return {"ok": False, "error_code": MixErrorCode.NO_PLAYBACK}
        return self._queue_svc.replace_and_play(self._current_songs, index)

    @Slot(int, result=dict)
    def enqueueTrack(self, index: int) -> dict[str, Any]:
        if not self._current_songs or index < 0 or index >= len(self._current_songs):
            return {"ok": False, "error_code": MixErrorCode.INVALID_INDEX}
        if not self._queue_svc:
            return {"ok": False, "error_code": MixErrorCode.NO_PLAYBACK}
        return self._queue_svc.enqueue(self._current_songs[index], play_now=False)

    @Slot(result=dict)
    def explainCurrentMix(self) -> dict[str, Any]:
        if not self._current_songs:
            return {"ok": False, "error_code": MixErrorCode.EMPTY_MIX}
        reasons = set()
        for s in self._current_songs[:10]:
            r = s.get("reason", "")
            if r:
                reasons.add(r)
        return {"ok": True, "reasons": list(reasons)[:5],
                "total": len(self._current_songs),
                "has_reasons": len(reasons) > 0}

    @Slot(result=dict)
    def partialFailureReport(self) -> dict[str, Any]:
        failures = [s.get('_error', '') for s in (self._current_songs or []) if s.get('_error', '')]
        if not failures:
            return {"ok": True, "has_failures": False, "failures": []}
        return {"ok": True, "has_failures": True, "failures": failures[:10], "total": len(failures)}

    @Slot(result=dict)
    def refresh(self) -> dict[str, Any]:
        if self._current_mix_id:
            return self.loadMix(self._current_mix_id)
        self.dataChanged.emit()
        return {"ok": bool(self._current_mix_id), "has_mix": bool(self._current_mix_id)}

    @Slot(str, result=dict)
    def navigateTo(self, route: str) -> dict[str, Any]:
        if self._nav:
            return self._nav.navigate(route)
        return {"ok": False, "error_code": MixErrorCode.NAVIGATION_UNAVAILABLE}
