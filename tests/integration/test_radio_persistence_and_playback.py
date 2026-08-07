"""Radio persistence + playback integration (Slice 5).

Real canonical RadioService (core/radio/service.py) over a temporary SQLite
database: CRUD persists, favorites persist, history persists across service
re-instantiation.
"""
from __future__ import annotations

import os

import pytest

from core.radio.service import RadioService
from core.radio.models import (
    StationCreateRequest, StationUpdateRequest,
)


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "radio.db")


def _build_service(db_path: str) -> RadioService:
    from infrastructure.radio.station_repository import SqliteStationRepository
    from infrastructure.radio.history_repository import SqliteRadioHistoryRepository

    station_repo = SqliteStationRepository(db_path)
    station_repo.initialize()
    history_repo = SqliteRadioHistoryRepository(db_path)
    history_repo.initialize()
    return RadioService(station_repo=station_repo, history_repo=history_repo)


class TestRadioPersistence:
    def test_add_station_readback(self, db_path):
        svc = _build_service(db_path)
        result = svc.create_station(StationCreateRequest(
            name="Test FM", stream_url="http://test.fm/stream", genre="Test"))
        assert result.ok
        station_id = result.station.id

        stations = svc.list_stations()
        assert any(s.id == station_id and s.name == "Test FM" for s in stations.items)

    def test_favorite_persists(self, db_path):
        svc = _build_service(db_path)
        result = svc.create_station(StationCreateRequest(
            name="Fav FM", stream_url="http://fav.fm/stream"))
        station_id = result.station.id

        assert svc.toggle_favorite(station_id).ok
        favs = svc.list_favorites()
        assert [s.id for s in favs.items] == [station_id]

    def test_delete_persists(self, db_path):
        svc = _build_service(db_path)
        result = svc.create_station(StationCreateRequest(
            name="Gone FM", stream_url="http://gone.fm/stream"))
        station_id = result.station.id

        assert svc.delete_station(station_id).ok
        assert svc.get_station(station_id).ok is False
        assert svc.count() == 0

    def test_update_persists(self, db_path):
        svc = _build_service(db_path)
        result = svc.create_station(StationCreateRequest(
            name="Old FM", stream_url="http://old.fm/stream"))
        station_id = result.station.id

        updated = svc.update_station(station_id, StationUpdateRequest(name="New FM"))
        assert updated.ok and updated.station.name == "New FM"
        assert svc.get_station(station_id).station.name == "New FM"

    def test_history_survives_reinstantiation(self, db_path):
        svc = _build_service(db_path)
        result = svc.create_station(StationCreateRequest(
            name="Hist FM", stream_url="http://hist.fm/stream"))
        station_id = result.station.id
        assert svc.mark_played(station_id).ok
        assert len(svc.history()) == 1

        # New service instance over the SAME database.
        svc2 = _build_service(db_path)
        history = svc2.history()
        assert len(history) == 1
        assert history[0]["station_id"] == station_id

    def test_stations_survive_reinstantiation(self, db_path):
        svc = _build_service(db_path)
        svc.create_station(StationCreateRequest(
            name="Keep FM", stream_url="http://keep.fm/stream"))

        svc2 = _build_service(db_path)
        assert svc2.count() == 1
        assert svc2.list_stations().items[0].name == "Keep FM"

    def test_clear_history_persists(self, db_path):
        svc = _build_service(db_path)
        result = svc.create_station(StationCreateRequest(
            name="Clear FM", stream_url="http://clear.fm/stream"))
        svc.mark_played(result.station.id)
        assert len(svc.history()) == 1

        svc.clear_history()
        assert svc.history() == []
        # Still gone after re-instantiation.
        assert _build_service(db_path).history() == []


class TestRadioPlayback:
    def test_start_station_records_history(self, db_path):
        """Start is accepted (attempt) and PLAYING confirm records a play."""
        from core.radio.models import SessionState, StreamMetadata
        from infrastructure.radio.station_repository import SqliteStationRepository
        from infrastructure.radio.history_repository import SqliteRadioHistoryRepository
        station_repo = SqliteStationRepository(db_path)
        station_repo.initialize()
        history_repo = SqliteRadioHistoryRepository(db_path)
        history_repo.initialize()

        class ConfirmingPlayer:
            state = "playing"

            def play_url(self, url):
                pass

            def stop(self):
                self.state = "stopped"

            def resume(self):
                pass

        from core.radio.playback_adapter import RadioPlaybackAdapter
        from core.radio.service import RadioService
        svc = RadioService(
            station_repo=station_repo,
            history_repo=history_repo,
            playback_adapter=RadioPlaybackAdapter(player_service=ConfirmingPlayer()),
            confirm_interval_ms=50,
        )
        result = svc.create_station(StationCreateRequest(
            name="Play FM", stream_url="http://play.fm/stream"))
        station_id = result.station.id

        started = svc.start_station(station_id)
        assert started.ok and started.accepted  # accepted, not completed
        kinds = [h.get("result") or "" for h in svc.history()]
        assert "attempt" in kinds
        assert "play" not in kinds  # no play until PLAYING is confirmed

        svc._session.update_metadata(StreamMetadata(stream_title="Live"))
        svc.poll_playback()  # player readback says playing
        assert svc.session.state == SessionState.PLAYING
        kinds = [h.get("result") or "" for h in svc.history()]
        assert "play" in kinds
        svc.stop()
        assert svc.session is None  # stop is idempotent

    def test_playback_backend_confirms(self, db_path):
        calls = []

        def fake_backend(url: str) -> bool:
            calls.append(url)
            return True

        from infrastructure.radio.station_repository import SqliteStationRepository
        from infrastructure.radio.history_repository import SqliteRadioHistoryRepository
        station_repo = SqliteStationRepository(db_path)
        station_repo.initialize()
        history_repo = SqliteRadioHistoryRepository(db_path)
        history_repo.initialize()
        svc = RadioService(
            station_repo=station_repo,
            history_repo=history_repo,
            playback_backend=fake_backend,
        )
        result = svc.create_station(StationCreateRequest(
            name="Backend FM", stream_url="http://backend.fm/stream"))
        svc.start_station(result.station.id)
        assert calls == ["http://backend.fm/stream"]
        assert svc.session.state.value == "playing"
        svc.stop()


class TestLegacyFacadePersistence:
    def test_facade_persists_via_canonical(self, tmp_path, monkeypatch):
        import core.paths as paths
        db = tmp_path / "radio.db"
        monkeypatch.setattr(paths, "app_data_dir", lambda: str(tmp_path))

        from core.radio.radio_service import RadioService
        svc = RadioService()
        result = svc.add_station("Facade FM", "http://facade.fm/stream")
        assert result["ok"]
        assert os.path.exists(str(db))

        # New facade instance reads the same persisted stations.
        svc2 = RadioService()
        names = [s["name"] for s in svc2.get_stations()]
        assert "Facade FM" in names

    def test_facade_history_persists(self, tmp_path, monkeypatch):
        import core.paths as paths
        monkeypatch.setattr(paths, "app_data_dir", lambda: str(tmp_path))

        from core.radio.radio_service import RadioService
        svc = RadioService()
        result = svc.add_station("Hist FM", "http://hist.fm/stream")
        # No playback mechanism is wired: play must fail explicitly, never
        # return True (no `return True` fallback).
        assert svc.play_station("http://hist.fm/stream") is False
        assert svc.get_history() == []

        # History persists through mark_played across re-instantiation.
        assert svc.mark_played(result["id"])["ok"]
        assert len(svc.get_history()) == 1

        svc2 = RadioService()
        assert len(svc2.get_history()) == 1
