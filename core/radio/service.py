from __future__ import annotations

import datetime
from typing import Callable

from core.radio.events import EventBus
from core.radio.models import (
    Station, StationId, StationCreateRequest, StationUpdateRequest,
    StreamSessionState, SessionState,
    ImportResult, ExportResult, RadioOperationResult, PaginatedResult,
    RadioError, ReconnectPolicyConfig, AtomicMode,
)
from core.radio.reconnect import RadioScheduler
from core.radio.stream_probe import StreamProbeService
from core.radio.session import StreamSession
from core.radio.import_export import (
    RadioImportService, RadioExportService, detect_playlist_format,
)
from core.radio.url_utils import validate_and_normalize_url, UrlNormalizationError


class RadioService:
    def __init__(
        self,
        station_repo,
        history_repo,
        event_bus: EventBus | None = None,
        probe_service: StreamProbeService | None = None,
        scheduler: RadioScheduler | None = None,
        clock: Callable[[], str] | None = None,
        playback_backend: Callable[[str], bool] | None = None,
        reconnect_config: ReconnectPolicyConfig | None = None,
    ):
        self._station_repo = station_repo
        self._history_repo = history_repo
        self._event_bus = event_bus or EventBus()
        self._probe_service = probe_service or StreamProbeService()
        self._scheduler = scheduler or RadioScheduler()
        self._clock = clock or (lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
        self._playback_backend = playback_backend
        self._reconnect_config = reconnect_config or ReconnectPolicyConfig()
        self._import_service = RadioImportService(self._station_repo)
        self._export_service = RadioExportService(self._station_repo)

        self._session: StreamSession | None = None
        self._session_generation = 0

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus

    @property
    def session(self) -> StreamSessionState | None:
        if self._session:
            return self._session.state
        return None

    def list_stations(self, page: int = 1, page_size: int = 50,
                      sort_by: str = "name", sort_dir: str = "asc") -> PaginatedResult:
        return self._station_repo.list_all(page, page_size, sort_by, sort_dir)

    def search_stations(self, query: str, page: int = 1, page_size: int = 50) -> PaginatedResult:
        return self._station_repo.search(query, page, page_size)

    def get_station(self, station_id: StationId) -> RadioOperationResult:
        station = self._station_repo.get(station_id)
        if station is None:
            return RadioOperationResult(
                ok=False, error=RadioError.NOT_FOUND,
                message=f"Station {station_id} not found",
            )
        return RadioOperationResult(ok=True, station=station)

    def create_station(self, req: StationCreateRequest) -> RadioOperationResult:
        try:
            req.stream_url = validate_and_normalize_url(req.stream_url)
        except UrlNormalizationError as e:
            return RadioOperationResult(
                ok=False, error=e.error, message=str(e),
            )
        station = self._station_repo.add(req)
        self._event_bus.emit("station_created", {"station_id": station.id})
        return RadioOperationResult(ok=True, station=station)

    def update_station(self, station_id: StationId, req: StationUpdateRequest) -> RadioOperationResult:
        if req.stream_url is not None:
            try:
                req.stream_url = validate_and_normalize_url(req.stream_url)
            except UrlNormalizationError as e:
                return RadioOperationResult(
                    ok=False, error=e.error, message=str(e),
                )
        station = self._station_repo.update(station_id, req)
        if station is None:
            return RadioOperationResult(
                ok=False, error=RadioError.NOT_FOUND,
                message=f"Station {station_id} not found",
            )
        self._event_bus.emit("station_updated", {"station_id": station_id})
        return RadioOperationResult(ok=True, station=station)

    def delete_station(self, station_id: StationId) -> RadioOperationResult:
        if self._session and self._session.state.station_id == station_id:
            self.stop()
        ok = self._station_repo.delete(station_id)
        if not ok:
            return RadioOperationResult(
                ok=False, error=RadioError.NOT_FOUND,
                message=f"Station {station_id} not found",
            )
        self._event_bus.emit("station_deleted", {"station_id": station_id})
        return RadioOperationResult(ok=True)

    def set_favorite(self, station_id: StationId, favorite: bool) -> RadioOperationResult:
        ok = self._station_repo.set_favorite(station_id, favorite)
        if not ok:
            return RadioOperationResult(
                ok=False, error=RadioError.NOT_FOUND,
                message=f"Station {station_id} not found",
            )
        self._event_bus.emit("favorite_changed", {"station_id": station_id, "favorite": favorite})
        return RadioOperationResult(ok=True)

    def list_favorites(self, page: int = 1, page_size: int = 50) -> PaginatedResult:
        return self._station_repo.list_favorites(page, page_size)

    def list_recent(self, limit: int = 20) -> list[Station]:
        return self._station_repo.list_recent(limit)

    def probe_station(self, station_id: StationId) -> RadioOperationResult:
        station = self._station_repo.get(station_id)
        if station is None:
            return RadioOperationResult(
                ok=False, error=RadioError.NOT_FOUND,
                message=f"Station {station_id} not found",
            )
        self._event_bus.emit("probe_started", {"station_id": station_id})
        result = self._probe_service.probe(station.stream_url)
        now = self._clock()
        self._station_repo.update_probe(
            station_id, result.status.value, now,
        )
        self._event_bus.emit("probe_completed", {
            "station_id": station_id,
            "status": result.status.value,
            "result": result,
        })
        return RadioOperationResult(ok=result.status.value == "valid", details={
            "probe_result": result,
        })

    def start_station(self, station_id: StationId) -> RadioOperationResult:
        station = self._station_repo.get(station_id)
        if station is None:
            return RadioOperationResult(
                ok=False, error=RadioError.NOT_FOUND,
                message=f"Station {station_id} not found",
            )

        self.stop()

        self._session_generation += 1
        gen = self._session_generation
        self._session = self._create_session(station.id, station.stream_url, gen)

        self._session.start()
        self._station_repo.mark_played(station_id)
        self._history_repo.record_play(station_id)
        self._event_bus.emit("session_state_changed", {
            "station_id": station_id,
            "state": SessionState.CONNECTING.value,
            "generation": gen,
        })
        return RadioOperationResult(ok=True, station=station)

    def stop(self):
        if self._session:
            old_session = self._session
            self._session = None
            old_session.stop()

    def retry(self):
        if self._session:
            self._session.retry()

    def cancel(self):
        if self._session:
            old_session = self._session
            self._session = None
            old_session.cancel()

    def import_playlist(self, content: str, fmt: str = "",
                        mode: AtomicMode = AtomicMode.BEST_EFFORT) -> ImportResult:
        if not fmt or fmt == "auto":
            fmt = detect_playlist_format(content)
        if fmt in ("m3u", "m3u8"):
            return self._import_service.import_m3u(content, mode)
        elif fmt == "pls":
            return self._import_service.import_pls(content, mode)
        return ImportResult(total_entries=0, errors=[f"Unsupported format: {fmt}"])

    def export_playlist(self, fmt: str = "m3u8", path: str = "") -> ExportResult:
        stations = self._station_repo.get_all_for_export()
        if fmt == "m3u8":
            return self._export_service.export_m3u8(stations, path)
        elif fmt == "pls":
            return self._export_service.export_pls(stations, path)
        elif fmt == "json":
            return self._export_service.export_json(stations, path)
        return ExportResult(error=f"Unsupported format: {fmt}")

    def clear_history(self, retention_days: int | None = None):
        self._history_repo.clear_history(retention_days)

    def history(self, limit: int = 50, offset: int = 0) -> list[dict]:
        return self._history_repo.list_history(limit, offset)

    def count(self) -> int:
        return self._station_repo.count()

    def _create_session(self, station_id: StationId, stream_url: str, generation: int) -> StreamSession:
        def playback_backend_wrapper(url: str) -> bool:
            if self._playback_backend:
                return self._playback_backend(url)
            return True

        return StreamSession(
            station_id=station_id,
            stream_url=stream_url,
            event_bus=self._event_bus,
            generation=generation,
            reconnect_config=self._reconnect_config,
            on_state_change=self._on_session_state_change,
            playback_backend=playback_backend_wrapper,
            scheduler=self._scheduler,
        )

    def _on_session_state_change(self, state: StreamSessionState):
        self._event_bus.emit("session_state_changed", {
            "station_id": state.station_id,
            "state": state.state.value,
            "metadata": state.metadata,
            "error": state.error.value,
            "generation": state.generation,
        })
        if state.state == SessionState.PLAYING and state.metadata.stream_title:
            self._history_repo.record_play(
                state.station_id, title=state.metadata.stream_title,
            )
        if state.state == SessionState.FAILED:
            self._event_bus.emit("playback_failed", {
                "station_id": state.station_id,
                "error": state.error.value,
                "message": state.error_message,
            })
        if state.state == SessionState.RECONNECTING:
            self._event_bus.emit("reconnect_scheduled", {
                "station_id": state.station_id,
                "attempt": state.reconnect_attempt,
            })
