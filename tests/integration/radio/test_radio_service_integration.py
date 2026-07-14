import pytest
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from core.radio.service import RadioService
from core.radio.models import (
    StationCreateRequest, StationUpdateRequest,
    SessionState,
)
from core.radio.events import EventBus
from core.radio.stream_probe import StreamProbeService
from core.radio.reconnect import RadioScheduler
from infrastructure.radio.station_repository import SqliteStationRepository
from infrastructure.radio.history_repository import SqliteRadioHistoryRepository


class _StreamHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/stream":
            self.send_response(200)
            self.send_header("Content-Type", "audio/mpeg")
            self.send_header("icy-name", "Integration Radio")
            self.send_header("icy-genre", "Test")
            self.send_header("icy-br", "128")
            self.send_header("icy-metaint", "8192")
            self.end_headers()
            self.wfile.write(b"X" * 4096)
        elif self.path == "/invalid":
            self.send_response(404)
            self.end_headers()
        elif self.path == "/radio":
            self.send_response(200)
            self.send_header("Content-Type", "audio/mpeg")
            self.end_headers()
            self.wfile.write(b"Y" * 4096)
        else:
            self.send_response(404)
            self.end_headers()

    def log_request(self, *args):
        pass


@pytest.fixture(scope="module")
def server():
    srv = HTTPServer(("127.0.0.1", 0), _StreamHandler)
    port = srv.server_address[1]
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield port
    srv.shutdown()


@pytest.fixture
def radio_service(tmp_path):
    db_path = os.path.join(tmp_path, "radio.db")
    station_repo = SqliteStationRepository(db_path, clock=lambda: "2024-01-01T00:00:00")
    station_repo.initialize()
    history_repo = SqliteRadioHistoryRepository(db_path, clock=lambda: "2024-01-01T00:00:00")
    history_repo.initialize()
    bus = EventBus()
    probe = StreamProbeService(None)
    sched = RadioScheduler()
    svc = RadioService(
        station_repo=station_repo,
        history_repo=history_repo,
        event_bus=bus,
        probe_service=probe,
        scheduler=sched,
        playback_backend=lambda url: True,
    )
    return svc, station_repo, history_repo, bus


class TestRadioServiceIntegration:
    def test_full_workflow(self, radio_service, server):
        svc, repo, hist, bus = radio_service

        result = svc.create_station(StationCreateRequest(
            name="Integration Radio",
            stream_url=f"http://127.0.0.1:{server}/stream",
        ))
        assert result.ok is True
        station_id = result.station.id

        got = svc.get_station(station_id)
        assert got.ok is True
        assert got.station.name == "Integration Radio"

        updated = svc.update_station(station_id, StationUpdateRequest(genre="Rock"))
        assert updated.ok is True

        probe_result = svc.probe_station(station_id)
        assert probe_result.ok is True

        start_result = svc.start_station(station_id)
        assert start_result.ok is True

        svc.stop()

        fav_result = svc.set_favorite(station_id, True)
        assert fav_result.ok is True

        favs = svc.list_favorites()
        assert favs.total == 1

        stations = svc.list_stations()
        assert stations.total >= 1

    def test_create_and_delete(self, radio_service, server):
        svc, repo, hist, bus = radio_service
        result = svc.create_station(StationCreateRequest(
            name="Temp Radio",
            stream_url=f"http://127.0.0.1:{server}/radio",
        ))
        station_id = result.station.id
        del_result = svc.delete_station(station_id)
        assert del_result.ok is True
        assert repo.count() == 0

    def test_search(self, radio_service, server):
        svc, repo, hist, bus = radio_service
        svc.create_station(StationCreateRequest(
            name="Rock FM", stream_url=f"http://127.0.0.1:{server}/radio",
            genre="Rock",
        ))
        svc.create_station(StationCreateRequest(
            name="Jazz FM", stream_url=f"http://127.0.0.2:{server}/radio",
            genre="Jazz",
        ))
        found = svc.search_stations("Rock")
        assert found.total == 1

    def test_import_export_workflow(self, radio_service, tmp_path):
        svc, repo, hist, bus = radio_service
        m3u_content = "#EXTM3U\n#EXTINF:-1,Import Radio\nhttp://example.com/import\n"
        imp_result = svc.import_playlist(m3u_content)
        assert imp_result.total_entries == 1

        export_path = os.path.join(tmp_path, "export.m3u8")
        exp_result = svc.export_playlist("m3u8", export_path)
        assert exp_result.ok is True

    def test_history_after_play(self, radio_service, server):
        svc, repo, hist, bus = radio_service
        result = svc.create_station(StationCreateRequest(
            name="History Radio",
            stream_url=f"http://127.0.0.1:{server}/stream",
        ))
        station_id = result.station.id
        svc.start_station(station_id)
        svc.stop()
        history = svc.history()
        assert len(history) >= 1

    def test_clear_history(self, radio_service, server):
        svc, repo, hist, bus = radio_service
        result = svc.create_station(StationCreateRequest(
            name="Clear Radio",
            stream_url=f"http://127.0.0.1:{server}/stream",
        ))
        station_id = result.station.id
        svc.start_station(station_id)
        svc.stop()
        svc.clear_history()
        history = svc.history()
        assert len(history) == 0

    def test_probe_invalid_url(self, radio_service, server):
        svc, repo, hist, bus = radio_service
        result = svc.create_station(StationCreateRequest(
            name="Bad URL",
            stream_url=f"http://127.0.0.1:{server}/invalid",
        ))
        station_id = result.station.id
        probe_result = svc.probe_station(station_id)
        assert probe_result.ok is False

    def test_events_emitted(self, radio_service, server):
        svc, repo, hist, bus = radio_service
        events = []
        bus.subscribe("station_created", lambda e: events.append(e.type))

        svc.create_station(StationCreateRequest(
            name="Event Radio",
            stream_url=f"http://127.0.0.1:{server}/stream",
        ))
        assert "station_created" in events

    def test_cancel_session(self, radio_service, server):
        svc, repo, hist, bus = radio_service
        result = svc.create_station(StationCreateRequest(
            name="Cancel Radio",
            stream_url=f"http://127.0.0.1:{server}/stream",
        ))
        station_id = result.station.id
        svc.start_station(station_id)
        svc.cancel()
        assert svc.session is None or svc.session.state in (SessionState.CANCELLED, SessionState.STOPPED, SessionState.IDLE)
