"""Tests: Identifier/Radio context — identification, radio selection."""

import os
from core.context import context_repository as repo
from core.context.context_events import AppEvent
from core.context.context_service import ContextService


class TestIdentifierRadioContext:

    def teardown_method(self):
        repo.close()
        repo.override_db_path(None)

    def _svc(self, tmp_path):
        repo.override_db_path(os.path.join(str(tmp_path), "ctx.sqlite"))
        return ContextService()

    def test_radio_station_selected_not_local_track(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.record_radio_station_selected(station_name="Jazz FM")
        events = svc.recent_events(limit=10)
        radio = [e for e in events if e["event_type"] == AppEvent.RADIO_STATION_SELECTED]
        selected = [e for e in events if e["event_type"] == AppEvent.TRACK_SELECTED]
        assert len(radio) == 1
        assert len(selected) == 0

    def test_identification_matched_no_url_or_token(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.record_identification_matched(title="Song", artist="Artist", confidence=0.95)
        events = svc.recent_events(limit=5)
        ev = next(e for e in events if e["event_type"] == AppEvent.IDENTIFICATION_MATCHED)
        raw = str(ev)
        assert "http" not in raw
        assert "token" not in raw
        assert "key" not in raw

    def test_identification_failed_no_crash(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.record_identification_started()
        svc.record_identification_failed()
        events = svc.recent_events(limit=5)
        types = [e["event_type"] for e in events]
        assert AppEvent.IDENTIFICATION_STARTED in types
        assert AppEvent.IDENTIFICATION_FAILED in types

    def test_radio_played_no_path(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.record_radio_played(station_name="Rock Anthem")
        events = svc.recent_events(limit=5)
        ev = next(e for e in events if e["event_type"] == AppEvent.RADIO_PLAYED)
        raw = str(ev)
        assert "/" not in raw.replace("Rock Anthem", "")
        assert "filepath" not in raw
