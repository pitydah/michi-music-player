import pytest
from unittest.mock import MagicMock

from core.radio.service import RadioService
from core.radio.models import (
    Station, StationCreateRequest, StationUpdateRequest,
    RadioError,
    SessionState,
)
from core.radio.events import EventBus


@pytest.fixture
def service():
    station_repo = MagicMock()
    station_repo.add.return_value = Station(
        id=1, name="Test", stream_url="https://example.com/stream",
    )
    station_repo.get.return_value = Station(
        id=1, name="Test", stream_url="https://example.com/stream",
    )
    station_repo.update.return_value = Station(
        id=1, name="Updated", stream_url="https://example.com/stream",
    )
    station_repo.delete.return_value = True
    station_repo.set_favorite.return_value = True
    station_repo.count.return_value = 5
    station_repo.list_all.return_value = MagicMock(items=[], total=0, page=1, page_size=50, pages=1)
    station_repo.list_favorites.return_value = MagicMock(items=[], total=0, page=1, page_size=50, pages=1)
    station_repo.search.return_value = MagicMock(items=[], total=0, page=1, page_size=50, pages=1)
    station_repo.list_recent.return_value = []
    station_repo.get_all_for_export.return_value = []
    station_repo.find_by_url.return_value = None
    station_repo.update_probe.return_value = None

    history_repo = MagicMock()
    event_bus = EventBus()

    from core.radio.stream_probe import StreamProbeService
    from core.radio.models import ProbeStatus, StreamProbeResult
    mock_probe = MagicMock(spec=StreamProbeService)
    result = StreamProbeResult(
        requested_url="https://example.com/stream",
        final_url="https://example.com/stream",
        status=ProbeStatus.VALID,
    )
    mock_probe.probe.return_value = result

    svc = RadioService(
        station_repo=station_repo,
        history_repo=history_repo,
        event_bus=event_bus,
        probe_service=mock_probe,
        playback_backend=lambda url: True,
    )
    return svc, station_repo, history_repo, event_bus


class TestRadioService:
    def test_create_station(self, service):
        svc, repo, hist, bus = service
        req = StationCreateRequest(name="Test", stream_url="https://example.com/stream")
        result = svc.create_station(req)
        assert result.ok is True
        assert result.station is not None

    def test_create_station_invalid_url(self, service):
        svc, repo, hist, bus = service
        req = StationCreateRequest(name="Test", stream_url="")
        result = svc.create_station(req)
        assert result.ok is False

    def test_get_station(self, service):
        svc, repo, hist, bus = service
        result = svc.get_station(1)
        assert result.ok is True
        repo.get.assert_called_with(1)

    def test_get_station_not_found(self, service):
        svc, repo, hist, bus = service
        repo.get.return_value = None
        result = svc.get_station(999)
        assert result.ok is False
        assert result.error == RadioError.NOT_FOUND

    def test_update_station(self, service):
        svc, repo, hist, bus = service
        result = svc.update_station(1, StationUpdateRequest(name="Updated"))
        assert result.ok is True

    def test_delete_station(self, service):
        svc, repo, hist, bus = service
        result = svc.delete_station(1)
        assert result.ok is True
        repo.delete.assert_called_with(1)

    def test_set_favorite(self, service):
        svc, repo, hist, bus = service
        result = svc.set_favorite(1, True)
        assert result.ok is True

    def test_list_stations(self, service):
        svc, repo, hist, bus = service
        result = svc.list_stations()
        assert result is not None

    def test_search_stations(self, service):
        svc, repo, hist, bus = service
        svc.search_stations("rock")
        repo.search.assert_called_with("rock", 1, 50)

    def test_list_favorites(self, service):
        svc, repo, hist, bus = service
        svc.list_favorites()
        repo.list_favorites.assert_called()

    def test_list_recent(self, service):
        svc, repo, hist, bus = service
        svc.list_recent()
        repo.list_recent.assert_called()

    def test_count(self, service):
        svc, repo, hist, bus = service
        assert svc.count() == 5

    def test_probe_station(self, service):
        svc, repo, hist, bus = service
        result = svc.probe_station(1)
        assert result.ok is True

    def test_probe_station_not_found(self, service):
        svc, repo, hist, bus = service
        repo.get.return_value = None
        result = svc.probe_station(999)
        assert result.ok is False

    def test_start_and_stop_station(self, service):
        svc, repo, hist, bus = service
        result = svc.start_station(1)
        assert result.ok is True
        svc.stop()
        assert svc.session is None or svc.session.state != SessionState.PLAYING

    def test_start_nonexistent_station(self, service):
        svc, repo, hist, bus = service
        repo.get.return_value = None
        result = svc.start_station(999)
        assert result.ok is False

    def test_export_playlist(self, service):
        svc, repo, hist, bus = service
        import tempfile as tf
        import os as os_mod
        tmp = tf.mkstemp(suffix=".m3u8")
        os_mod.close(tmp[0])
        svc.export_playlist("m3u8", tmp[1])
        os_mod.unlink(tmp[1])

    def test_clear_history(self, service):
        svc, repo, hist, bus = service
        svc.clear_history()
        hist.clear_history.assert_called()

    def test_event_bus_is_accessible(self, service):
        svc, repo, hist, bus = service
        assert svc.event_bus is bus

    def test_double_start_station_stops_first(self, service):
        svc, repo, hist, bus = service
        svc.start_station(1)
        svc.start_station(1)
        assert svc.session is not None
