"""MixBridge adapts generated mixes to canonical queue operations."""
from __future__ import annotations

import contextlib
import json
import logging
from enum import Enum
from typing import Any

from PySide6.QtCore import QObject, Signal, Property, Slot

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
    IDLE = "IDLE"
    CONFIGURING = "CONFIGURING"
    VALIDATING = "VALIDATING"
    QUEUED = "QUEUED"
    GENERATING = "GENERATING"
    CANCELLING = "CANCELLING"
    CANCELLED = "CANCELLED"
    READY = "READY"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"


MIX_CATEGORIES = [
    {"id": "favorites", "title": "Favoritos", "icon": "FV", "desc": "Tus canciones marcadas como favoritas"},
    {"id": "recent", "title": "Escuchadas recientemente", "icon": "RC", "desc": "Canciones reproducidas recientemente"},
    {"id": "most_played", "title": "Mas escuchadas", "icon": "MP", "desc": "Tus canciones con mas reproducciones"},
    {"id": "unplayed", "title": "No escuchadas", "icon": "UN", "desc": "Canciones que aun no has reproducido"},
    {"id": "rediscovery", "title": "Redescubrimiento", "icon": "RD", "desc": "Canciones antiguas que no escuchas hace tiempo"},
    {"id": "daily_mix", "title": "Mix diario", "icon": "MX", "desc": "Recomendaciones basadas en tu historial"},
    {"id": "by_artist", "title": "Por artista", "icon": "AR", "desc": "Mixes centrados en un artista"},
    {"id": "by_genre", "title": "Por genero", "icon": "GN", "desc": "Mixes por genero musical"},
    {"id": "by_decade", "title": "Por decada", "icon": "DC", "desc": "Mixes por decada"},
    {"id": "by_year", "title": "Por ano", "icon": "YR", "desc": "Mixes por ano especifico"},
    {"id": "high_quality", "title": "Alta calidad", "icon": "HQ", "desc": "Solo pistas con bitrate >= 320 kbps"},
    {"id": "custom", "title": "Mix personalizado", "icon": "CS", "desc": "Mix basado en reglas definidas por ti"},
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
                  query_executor: Any = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        # Retained for bridge-factory and caller compatibility; this bridge no longer uses them.
        del action_registry, capability_bridge, accessibility_bridge, playback_service, query_executor
        self._mix_svc = mix_service
        self._job_svc = job_service
        self._nav = navigation_bridge
        self._page_state = page_state_store
        self._playlist_svc = playlist_service
        self._queue_svc = queue_service

        self._state = MixState.IDLE
        self._current_mix_id = ""
        self._current_mix_title = ""
        self._config_params = ""
        self._current_songs: list[dict] = []
        self._error_message = ""
        self._generation = 0
        self._validation_errors: list[str] = []

    @property
    def state(self) -> MixState:
        return self._state

    def _set_state(self, new_state: MixState) -> None:
        if self._state != new_state:
            self._state = new_state
            self.stateChanged.emit(new_state.value)
            self.dataChanged.emit()

    def _can_transition(self, target: MixState) -> bool:
        """Return whether the state machine permits the requested transition."""
        valid = {
            MixState.IDLE: {MixState.CONFIGURING, MixState.GENERATING},
            MixState.CONFIGURING: {MixState.VALIDATING, MixState.IDLE, MixState.FAILED},
            MixState.VALIDATING: {MixState.QUEUED, MixState.CONFIGURING, MixState.FAILED},
            MixState.QUEUED: {MixState.GENERATING, MixState.IDLE, MixState.CANCELLING, MixState.FAILED},
            MixState.GENERATING: {MixState.READY, MixState.PARTIAL_SUCCESS, MixState.FAILED,
                                  MixState.CANCELLING, MixState.CANCELLED},
            MixState.CANCELLING: {MixState.CANCELLED, MixState.IDLE},
            MixState.CANCELLED: {MixState.CONFIGURING, MixState.IDLE},
            MixState.READY: {MixState.CONFIGURING, MixState.IDLE, MixState.GENERATING},
            MixState.PARTIAL_SUCCESS: {MixState.CONFIGURING, MixState.IDLE, MixState.GENERATING},
            MixState.FAILED: {MixState.CONFIGURING, MixState.IDLE},
        }
        return target in valid.get(self._state, set())

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

    @Slot(str, result=dict)
    def configure(self, mix_id: str, params: str = "") -> dict[str, Any]:
        if not self._can_transition(MixState.CONFIGURING):
            return {"ok": False, "error_code": MixErrorCode.INVALID_STATE, "state": self._state.value}
        self._set_state(MixState.CONFIGURING)
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
        if not self._can_transition(MixState.VALIDATING):
            return {"ok": False, "error_code": MixErrorCode.INVALID_STATE, "state": self._state.value}
        self._set_state(MixState.VALIDATING)
        self._validation_errors = []
        if not self._current_mix_id:
            self._validation_errors.append("No se selecciono ningun mix")
            self._set_state(MixState.FAILED)
            return {"ok": False, "error_code": MixErrorCode.NO_MIX_SELECTED, "errors": self._validation_errors}
        if self._mix_svc is None:
            self._validation_errors.append("Servicio de mix no disponible")
            self._set_state(MixState.FAILED)
            return {"ok": False, "error_code": MixErrorCode.SERVICE_UNAVAILABLE, "errors": self._validation_errors}
        self._set_state(MixState.QUEUED)
        return {"ok": True, "valid": True}

    def _run_generation(self, mix_id: str, params: str) -> dict[str, Any]:
        """Load a mix and normalize service failures into the bridge result contract."""
        try:
            songs = self._load_mix_items(mix_id, seed=params)
        except Exception as e:
            logger.debug("Mix generate failed: %s", e, exc_info=True)
            return {"ok": False, "error_code": MixErrorCode.QUERY_FAILED, "detail": str(e)}
        if songs is None:
            return {"ok": False, "error_code": MixErrorCode.SERVICE_UNAVAILABLE, "detail": "Servicio de biblioteca no disponible"}
        if not songs:
            return {"ok": True, "count": 0, "partial": False, "error_code": MixErrorCode.EMPTY_RESULT}
        return {"ok": True, "songs": songs}

    @Slot(result=dict)
    def generate(self) -> dict[str, Any]:
        if not self._can_transition(MixState.GENERATING):
            return {"ok": False, "error_code": MixErrorCode.INVALID_STATE, "state": self._state.value}
        self._set_state(MixState.QUEUED)
        self._generation += 1
        gen = self._generation
        mix_id = self._current_mix_id
        params = self._config_params
        self._set_state(MixState.GENERATING)

        result = self._run_generation(mix_id, params)
        if not result.get("ok"):
            self._error_message = result.get("detail", "Error de generacion")
            self.generationError.emit(self._error_message)
            self._set_state(MixState.FAILED)
            return result

        songs = result.get("songs")
        if songs is None:
            self._current_songs = []
            self._error_message = ""
            self._set_state(MixState.READY)
            return {"ok": True, "count": 0, "partial": False, "error_code": MixErrorCode.EMPTY_RESULT}

        self._current_songs = songs
        self._error_message = ""

        if self._page_state:
            self._page_state.set("mix_last_result", {
                "mix_id": mix_id, "count": len(songs), "generation": gen,
            })

        if self.generationProgress:
            self.generationProgress.emit(len(songs), len(songs))

        self._set_state(MixState.READY)
        return {"ok": True, "count": len(songs), "partial": False}

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
        if self._state not in (MixState.READY, MixState.PARTIAL_SUCCESS, MixState.FAILED):
            return {"ok": False, "error_code": MixErrorCode.INVALID_STATE, "state": self._state.value}
        return self.generate()

    @Slot(result=dict)
    def cancelGeneration(self) -> dict[str, Any]:
        if self._state == MixState.GENERATING:
            self._set_state(MixState.CANCELLING)
        if self._job_svc and hasattr(self._job_svc, 'cancel_all'):
            with contextlib.suppress(Exception):
                self._job_svc.cancel_all(owner="mix_bridge")
        gen = self._generation
        self._generation += 1
        self._current_songs = []
        self._set_state(MixState.CANCELLED)
        return {"ok": True, "cancelled": gen}

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
        self._error_message = ""
        self._validation_errors = []
        self._set_state(MixState.IDLE)
        return {"ok": True}

    def _load_mix_items(self, mix_id: str, seed: str = "") -> list[dict] | None:
        """Dispatch a mix category to its loader and apply common result limits."""
        if self._mix_svc is None:
            return None

        loaders = {
            "favorites": lambda: self._mix_svc.favorites(50),
            "recent": lambda: self._mix_svc.recent(30),
            "most_played": lambda: self._mix_svc.most_played(30),
            "unplayed": lambda: self._mix_svc.unplayed(30),
            "rediscovery": lambda: self._mix_svc.rediscovery(30),
            "daily_mix": lambda: self._build_daily_mix(),
            "by_artist": lambda: self._mix_svc.by_field("artist", limit=30),
            "by_genre": lambda: self._mix_svc.by_field("genre", limit=30),
            "by_decade": lambda: self._mix_svc.by_decade(30),
            "by_year": lambda: self._mix_svc.by_year(30),
            "high_quality": lambda: self._mix_svc.high_quality(30),
            "custom": lambda: self._build_custom_mix(seed),
        }
        loader = loaders.get(mix_id)
        if not loader:
            return []

        try:
            items = loader()
            if items is None:
                return None
            if not items:
                return []
            return self._deduplicate_and_apply_limits(items)
        except Exception as e:
            logger.debug("mix %s failed: %s", mix_id, e)
            return []

    def _deduplicate_and_apply_limits(self, items: list[dict[str, Any]],
                                      artist_limit: int = 5,
                                      max_total: int = 50) -> list[dict[str, Any]]:
        """Deduplicate identified tracks and enforce artist and total limits."""
        seen_ids: set[Any] = set()
        artist_counts: dict[str, int] = {}
        result: list[dict[str, Any]] = []
        for item in items:
            tid = item.get("track_id", 0) or item.get("id", 0)
            if tid and tid in seen_ids:
                continue
            if tid:
                seen_ids.add(tid)
            artist = item.get("artist", "")
            if artist and artist_counts.get(artist, 0) >= artist_limit:
                continue
            if artist:
                artist_counts[artist] = artist_counts.get(artist, 0) + 1
            result.append(item)
            if len(result) >= max_total:
                break
        if len(result) < len(items) and len(result) > 0:
            self._set_state(MixState.PARTIAL_SUCCESS)
        return result

    def _build_daily_mix(self) -> list[dict[str, Any]]:
        """Combine recent and unplayed tracks into a bounded daily mix."""
        if not self._mix_svc:
            return []
        try:
            recent = self._mix_svc.recent(50)
            unplayed = self._mix_svc.unplayed(50)
            if recent is None or unplayed is None:
                return []
            recent_ids = {r.get("track_id", 0) or r.get("id", 0) for r in recent}
            combined = recent[:15]
            for t in unplayed:
                tid = t.get("track_id", 0) or t.get("id", 0)
                if tid not in recent_ids and len(combined) < 25:
                    combined.append(t)
            for t in combined:
                t["reason"] = "Mix diario"
            return combined[:25]
        except Exception as e:
            logger.debug("daily_mix failed: %s", e)
            return []

    def _build_custom_mix(self, params: str = "") -> list[dict[str, Any]]:
        """Build a field-filtered mix from JSON-encoded custom rules."""
        if not params or not self._mix_svc:
            return []
        try:
            rules = json.loads(params) if isinstance(params, str) else params
            artist = rules.get("artist", "")
            genre = rules.get("genre", "")
            limit = int(rules.get("limit", 30))
            if artist:
                result = self._mix_svc.by_field("artist", value=artist, limit=limit)
                return result or []
            if genre:
                result = self._mix_svc.by_field("genre", value=genre, limit=limit)
                return result or []
        except Exception as e:
            logger.debug("custom mix failed: %s", e, exc_info=True)
        return []

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

    def _try_create_playlist(self, name: str) -> Any | None:
        if self._playlist_svc and hasattr(self._playlist_svc, 'create'):
            pid = self._playlist_svc.create(name)
            if pid:
                return pid
        return None

    def _try_add_to_playlist(self, pid: Any, tid: Any) -> bool:
        if self._playlist_svc and hasattr(self._playlist_svc, 'add_track'):
            self._playlist_svc.add_track(pid, tid)
            return True
        return False

    @Slot(str, result=dict)
    def saveMixAsPlaylist(self, name: str) -> dict[str, Any]:
        if not name:
            return {"ok": False, "error_code": MixErrorCode.EMPTY_NAME}
        if not self._current_songs:
            return {"ok": False, "error_code": MixErrorCode.EMPTY_MIX}
        if not self._playlist_svc:
            return {"ok": False, "error_code": MixErrorCode.NO_PLAYLIST_SERVICE}
        try:
            pid = self._try_create_playlist(name)
            if not pid:
                return {"ok": False, "error_code": MixErrorCode.CREATE_FAILED}
            count = 0
            for s in self._current_songs:
                tid = s.get("track_id") or s.get("id")
                if tid:
                    try:
                        if self._try_add_to_playlist(pid, tid):
                            count += 1
                    except Exception as e:
                        logger.debug(
                            "Failed to add track %s to playlist %s: %s",
                            tid, pid, e, exc_info=True,
                        )
            if self._playlist_svc and hasattr(self._playlist_svc, 'refresh'):
                self._playlist_svc.refresh()
            return {"ok": True, "id": pid, "count": count}
        except Exception as e:
            return {"ok": False, "error_code": MixErrorCode.SAVE_FAILED, "detail": str(e)}

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
