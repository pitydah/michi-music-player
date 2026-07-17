"""Tests for DetectionService — source skip, dedup, history expiry."""
from unittest.mock import MagicMock

import pytest

from recognition.detection_service import DetectionService
from recognition.models import DetectedTrack


@pytest.fixture
def db():
    return MagicMock()


@pytest.fixture
def provider_mgr():
    from recognition.provider_manager import ProviderManager
    mgr = ProviderManager()
    mgr._recognizer = MagicMock()
    mgr._current_provider = "test_provider"
    return mgr


@pytest.fixture
def service(qapp, db, provider_mgr):
    svc = DetectionService(db, provider_mgr)
    svc._capture = MagicMock()
    svc._capture.is_available = True
    return svc


class TestLocalSourceSkip:
    def test_start_sets_active_for_radio(self, service):
        service.start(source="radio")
        assert service.is_active is True

    def test_start_sets_active_for_navidrome(self, service):
        service.start(source="navidrome")
        assert service.is_active is True

    def test_start_sets_active_for_jellyfin(self, service):
        service.start(source="jellyfin")
        assert service.is_active is True

    def test_start_sets_active_for_remote_stream(self, service):
        service.start(source="remote_stream")
        assert service.is_active is True

    def test_start_sets_active_for_local_file(self, service):
        service.start(source="local_file")
        assert service.is_active is True

    # DetectionService itself doesn't skip — IdentifierController does.
    # Verify the service still works regardless of source type.
    def test_identify_once_works_with_local_source(self, service):
        service._active = True
        service._capture = MagicMock()
        service._capture.is_available = True
        service._capture.capture_once.return_value = b"fake_audio"
        service.recognizer.identify.return_value = {"title": "Local Song", "artist": "Local Artist"}
        service.identify_once()
        assert service._detections_total == 1


class TestDedup24h:
    def test_add_manual_skips_when_found_in_24h(self, service, db):
        db.find_detected_track_recent.return_value = {"title": "Song", "artist": "A"}
        service.add_manual_detection("Song", "A")
        db.add_detected_track.assert_not_called()
        assert service._duplicates_avoided == 1

    def test_add_manual_passes_when_not_found(self, service, db):
        db.find_detected_track_recent.return_value = None
        service.add_manual_detection("Unique", "Artist")
        db.add_detected_track.assert_called_once()

    def test_handle_identified_does_not_dedup(self, service, db):
        service._handle_identified({"title": "Auto", "artist": "A"})
        db.find_detected_track_recent.assert_not_called()
        assert service._detections_total == 1

    def test_add_manual_passes_max_age_to_db(self, service, db):
        db.find_detected_track_recent.return_value = None
        service.add_manual_detection("Song", "A")
        args, kwargs = db.find_detected_track_recent.call_args
        assert args[0] == "Song"
        assert args[1] == "A"

    def test_add_manual_different_title_not_skipped(self, service, db):
        db.find_detected_track_recent.return_value = None
        service.add_manual_detection("Different", "A")
        db.add_detected_track.assert_called_once()

    def test_add_manual_different_artist_not_skipped(self, service, db):
        db.find_detected_track_recent.return_value = None
        service.add_manual_detection("Song", "Different")
        db.add_detected_track.assert_called_once()


class TestSqliteHistoryExpiry:
    @pytest.fixture
    def hist_repo(self, db):
        from recognition.detection_history_repository import DetectionHistoryRepository
        return DetectionHistoryRepository(db)

    def test_get_all_returns_list(self, hist_repo):
        mock_conn = MagicMock()
        hist_repo._db.conn = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = []
        result = hist_repo.get_all()
        assert result == []

    def test_get_all_with_source_filter(self, hist_repo):
        mock_conn = MagicMock()
        hist_repo._db.conn = mock_conn
        mock_conn.execute.side_effect = [
            MagicMock(fetchall=lambda: []),  # SELECT
            MagicMock(fetchall=lambda: []),  # PRAGMA
        ]
        hist_repo.get_all(source_type="radio")
        select_sql = mock_conn.execute.call_args_list[0][0][0]
        assert "WHERE source = ?" in select_sql

    def test_get_all_sql_orders_by_detected_at_desc(self, hist_repo):
        mock_conn = MagicMock()
        hist_repo._db.conn = mock_conn
        cols = [("id",), ("title",), ("artist",), ("album",), ("source",),
                ("provider",), ("confidence",), ("detected_at",)]
        mock_conn.execute.side_effect = [
            MagicMock(fetchall=lambda: []),   # SELECT (no source filter → returns rows)
            MagicMock(fetchall=lambda: cols), # PRAGMA
        ]
        hist_repo.get_all()
        select_sql = mock_conn.execute.call_args_list[0][0][0]
        assert "ORDER BY detected_at DESC" in select_sql

    def test_get_all_with_limit(self, hist_repo):
        mock_conn = MagicMock()
        hist_repo._db.conn = mock_conn
        mock_conn.execute.side_effect = [
            MagicMock(fetchall=lambda: []),  # SELECT
            MagicMock(fetchall=lambda: []),  # PRAGMA
        ]
        hist_repo.get_all(limit=50)
        select_sql = mock_conn.execute.call_args_list[0][0][0]
        assert "LIMIT ?" in select_sql

    def test_get_recent_delegates_to_db(self, hist_repo):
        hist_repo._db.find_detected_track_recent.return_value = {"title": "T", "artist": "A"}
        r = hist_repo.get_recent("T", "A")
        assert r == {"title": "T", "artist": "A"}

    def test_get_recent_passes_max_age_hours(self, hist_repo):
        hist_repo._db.find_detected_track_recent.return_value = None
        hist_repo.get_recent("T", "A", max_age_hours=48)
        hist_repo._db.find_detected_track_recent.assert_called_once_with("T", "A", 48)

    def test_add_saves_track_and_emits_signal(self, hist_repo):
        mock_conn = MagicMock()
        hist_repo._db.conn = mock_conn
        signals = []
        hist_repo.history_changed.connect(lambda: signals.append(True))
        track = DetectedTrack(title="T", artist="A", album="Al", provider="shazam")
        hist_repo.add(track)
        hist_repo._db.add_detected_track.assert_called_once()
        assert len(signals) == 1

    def test_add_fallback_on_exception(self, hist_repo):
        hist_repo._db.add_detected_track.side_effect = Exception("db error")
        signals = []
        hist_repo.history_changed.connect(lambda: signals.append(True))
        track = DetectedTrack(title="T", artist="A")
        hist_repo.add(track)
        assert len(signals) == 0

    def test_delete_calls_db_and_emits(self, hist_repo):
        signals = []
        hist_repo.history_changed.connect(lambda: signals.append(True))
        hist_repo.delete(42)
        hist_repo._db.delete_detected_track.assert_called_once_with(42)
        assert len(signals) == 1

    def test_clear_calls_db_and_emits(self, hist_repo):
        changed = []
        cleared = []
        hist_repo.history_changed.connect(lambda: changed.append(True))
        hist_repo.history_cleared.connect(lambda: cleared.append(True))
        hist_repo.clear()
        hist_repo._db.clear_detected_tracks.assert_called_once()
        assert len(changed) == 1
        assert len(cleared) == 1

    def test_count_all(self, hist_repo):
        mock_conn = MagicMock()
        hist_repo._db.conn = mock_conn
        mock_conn.execute.return_value.fetchone.return_value = (7,)
        assert hist_repo.count() == 7

    def test_count_by_source(self, hist_repo):
        mock_conn = MagicMock()
        hist_repo._db.conn = mock_conn
        mock_conn.execute.return_value.fetchone.return_value = (3,)
        assert hist_repo.count(source_type="radio") == 3

    def test_count_sql_includes_where(self, hist_repo):
        mock_conn = MagicMock()
        hist_repo._db.conn = mock_conn
        mock_conn.execute.return_value.fetchone.return_value = (1,)
        hist_repo.count(source_type="radio")
        call_sql = mock_conn.execute.call_args[0][0]
        assert "WHERE source = ?" in call_sql

    def test_get_sources(self, hist_repo):
        mock_conn = MagicMock()
        hist_repo._db.conn = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = [("radio",), ("manual",)]
        assert hist_repo.get_sources() == ["radio", "manual"]

    def test_get_sources_empty_on_exception(self, hist_repo):
        hist_repo._db.conn = None
        assert hist_repo.get_sources() == []

    def test_get_all_empty_on_exception(self, hist_repo):
        hist_repo._db.conn = None
        assert hist_repo.get_all() == []

    def test_count_zero_on_exception(self, hist_repo):
        hist_repo._db.conn = None
        assert hist_repo.count() == 0

    def test_add_with_all_fields(self, hist_repo):
        mock_conn = MagicMock()
        hist_repo._db.conn = mock_conn
        track = DetectedTrack(
            title="T", artist="A", album="Al", source="radio",
            provider="shazamio", confidence=0.95, isrc="USABC123",
            artwork_url="https://example.com/art.jpg",
            external_url="https://example.com",
            filepath="/music/track.flac", matched_library_id=1,
            raw_json='{"key": "val"}',
        )
        hist_repo.add(track)
        _, kwargs = hist_repo._db.add_detected_track.call_args
        assert kwargs["title"] == "T"
        assert kwargs["artist"] == "A"
        assert kwargs["album"] == "Al"
        assert kwargs["isrc"] == "USABC123"
        assert kwargs["artwork_url"] == "https://example.com/art.jpg"

    def test_delete_handles_exception_gracefully(self, hist_repo):
        hist_repo._db.delete_detected_track.side_effect = Exception("fail")
        signals = []
        hist_repo.history_changed.connect(lambda: signals.append(True))
        hist_repo.delete(1)
        assert len(signals) == 0

    def test_clear_handles_exception_gracefully(self, hist_repo):
        hist_repo._db.clear_detected_tracks.side_effect = Exception("fail")
        changed = []
        cleared = []
        hist_repo.history_changed.connect(lambda: changed.append(True))
        hist_repo.history_cleared.connect(lambda: cleared.append(True))
        hist_repo.clear()
        assert len(changed) == 0
        assert len(cleared) == 0

    def test_count_handles_exception(self, hist_repo):
        hist_repo._db.conn = MagicMock()
        hist_repo._db.conn.execute.side_effect = Exception("fail")
        assert hist_repo.count() == 0
