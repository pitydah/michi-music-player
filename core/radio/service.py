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
        playback_adapter=None,
        reconnect_config: ReconnectPolicyConfig | None = None,
        confirm_interval_ms: int = 300,
        connect_timeout_s: int = 10,
        monotonic_clock: Callable[[], float] | None = None,
    ):
        self._station_repo = station_repo
        self._history_repo = history_repo
        self._event_bus = event_bus or EventBus()
        self._probe_service = probe_service or StreamProbeService()
        self._scheduler = scheduler or RadioScheduler()
        self._clock = clock or (lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
        self._playback_backend = playback_backend
        self._playback_adapter = playback_adapter
        self._reconnect_config = reconnect_config or ReconnectPolicyConfig()
        self._confirm_interval_ms = confirm_interval_ms
        self._connect_timeout_s = connect_timeout_s
        self._monotonic_clock = monotonic_clock
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

    def get_state(self) -> SessionState:
        """Effective playback state: the adapter (PlayerService) is the truth.

        When no adapter is wired, fall back to the session state so legacy
        (backend-callable) playback remains observable.
        """
        if self._playback_adapter is not None:
            return self._playback_adapter.get_state()
        if self._session:
            return self._session.state.state
        return SessionState.IDLE

    def poll_playback(self):
        """One confirmation step against the playback adapter.

        Tests drive this deterministically; the session self-schedules the
        same step in production via its scheduler.
        """
        if self._session:
            self._session.poll_playback()

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

    def toggle_favorite(self, station_id: StationId) -> RadioOperationResult:
        """Toggle the favorite flag for a station (single authority).

        Added as the canonical home of the toggle semantics that the legacy
        facade and the QML bridge expose through ``favorite_station``.
        """
        station = self._station_repo.get(station_id)
        if station is None:
            return RadioOperationResult(
                ok=False, error=RadioError.NOT_FOUND,
                message=f"Station {station_id} not found",
            )
        return self.set_favorite(station_id, not station.favorite)

    def mark_played(self, station_id: StationId) -> RadioOperationResult:
        """Record a play: bump the station counters and append to history.

        Kept as a public operation so the legacy bridge API can report a play
        that was confirmed through the playback path without owning a
        StreamSession. The playback flow itself records plays on PLAYING via
        :meth:`_on_session_state_change` — this method is NOT called at
        connection start.
        """
        station = self._station_repo.get(station_id)
        if station is None:
            return RadioOperationResult(
                ok=False, error=RadioError.NOT_FOUND,
                message=f"Station {station_id} not found",
            )
        self._station_repo.mark_played(station_id)
        self._history_repo.record_event(station_id, "play")
        return RadioOperationResult(ok=True)

    def bulk_import(self, stations: list[StationCreateRequest],
                    mode: AtomicMode = AtomicMode.BEST_EFFORT) -> RadioOperationResult:
        """Import a list of stations (upsert by URL) into the repository."""
        imported = self._station_repo.bulk_add(stations, mode.value)
        self._event_bus.emit("stations_imported", {"imported": imported})
        return RadioOperationResult(ok=True, details={"imported": imported})

    def export_stations(self) -> list[dict]:
        """All stations as plain dicts (name/url/genre/country/codec)."""
        return [
            {
                "name": s.name,
                "url": s.stream_url,
                "genre": s.genre,
                "country": s.country,
                "codec": s.codec,
                "id": s.id,
                "favorite": s.favorite,
                "bitrate": s.bitrate,
            }
            for s in self._station_repo.get_all_for_export()
        ]

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

    def play_station(self, url: str, name: str = "") -> RadioOperationResult:
        """Start playback by URL (or id) — the entry point used by the bridge.

        Resolves the station and delegates to :meth:`start_station`. The
        result is *accepted* (status CONNECTING/BUFFERING), never a completed
        operation: effective success is only emitted on PLAYING.
        """
        station = self._station_repo.find_by_url(url)
        if station is None:
            try:
                station = self._station_repo.get(int(url))
            except (TypeError, ValueError):
                station = None
        if station is None:
            return RadioOperationResult(
                ok=False, accepted=False, error=RadioError.NOT_FOUND,
                status="failed", message=f"Station {url} not found",
            )
        return self.start_station(station.id)

    def start_station(self, station_id: StationId) -> RadioOperationResult:
        station = self._station_repo.get(station_id)
        if station is None:
            return RadioOperationResult(
                ok=False, accepted=False, error=RadioError.NOT_FOUND,
                status="failed", message=f"Station {station_id} not found",
            )

        if self._playback_adapter is None and self._playback_backend is None:
            return RadioOperationResult(
                ok=False, accepted=False, error=RadioError.BACKEND_UNAVAILABLE,
                status="failed",
                message="No playback adapter is available — cannot start playback",
            )

        self.stop()

        self._session_generation += 1
        gen = self._session_generation
        self._session = self._create_session(station.id, station.stream_url, gen)

        self._session.start()
        state = self._session.state.state
        if state == SessionState.FAILED:
            # Synchronous failure (e.g. load_stream rejected): this is an
            # explicit failure, never an accepted operation.
            session_error = self._session.state.error or RadioError.CONNECTION_FAILED
            return RadioOperationResult(
                ok=False, accepted=False, station=station,
                error=session_error, status="failed",
                message=self._session.state.error_message or "Playback failed to start",
            )
        self._event_bus.emit("session_state_changed", {
            "station_id": station_id,
            "state": state.value,
            "generation": gen,
        })
        return RadioOperationResult(
            ok=True, accepted=True, station=station,
            status=state.value,
            details={"state": state.value, "generation": gen},
        )

    def stop(self) -> RadioOperationResult:
        if self._session:
            old_session = self._session
            self._session = None
            old_session.stop()
        return RadioOperationResult(ok=True)

    def retry(self):
        if self._session:
            self._session.retry()

    def cancel(self) -> RadioOperationResult:
        if self._session:
            old_session = self._session
            self._session = None
            old_session.cancel()
        return RadioOperationResult(ok=True)

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
        return StreamSession(
            station_id=station_id,
            stream_url=stream_url,
            event_bus=self._event_bus,
            generation=generation,
            reconnect_config=self._reconnect_config,
            confirm_interval_ms=self._confirm_interval_ms,
            connect_timeout_ms=self._connect_timeout_s * 1000,
            monotonic=self._monotonic_clock,
            on_state_change=self._on_session_state_change,
            playback_backend=self._playback_backend,
            playback_adapter=self._playback_adapter,
            scheduler=self._scheduler,
        )

    def _on_session_state_change(self, state: StreamSessionState):
        self._event_bus.emit("session_state_changed", {
            "station_id": state.station_id,
            "state": state.state.value,
            "metadata": state.metadata,
            "error": state.error.value,
            "error_message": state.error_message,
            "generation": state.generation,
            "attempt": state.reconnect_attempt,
        })
        if state.state == SessionState.REQUESTED:
            self._history_repo.record_event(state.station_id, "attempt")
        if state.state == SessionState.PLAYING:
            self._station_repo.mark_played(state.station_id)
            self._history_repo.record_event(
                state.station_id, "play",
                title=state.metadata.stream_title,
            )
        if state.state == SessionState.RECONNECTING:
            self._history_repo.record_event(
                state.station_id, "reconnect",
                error_code=state.error.value,
            )
            self._event_bus.emit("reconnect_scheduled", {
                "station_id": state.station_id,
                "attempt": state.reconnect_attempt,
            })
        if state.state == SessionState.STOPPED:
            self._history_repo.record_event(state.station_id, "stopped")
        if state.state == SessionState.FAILED:
            self._history_repo.record_event(
                state.station_id, "failure",
                error_code=state.error.value,
            )
            self._event_bus.emit("playback_failed", {
                "station_id": state.station_id,
                "error": state.error.value,
                "message": state.error_message,
            })
