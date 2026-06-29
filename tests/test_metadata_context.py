"""Tests: Metadata context events — METADATA_SAVED, COVER_UPDATED, LYRICS_UPDATED, etc."""

import os
from core.context import context_repository as repo
from core.context.context_events import AppEvent
from core.context.context_service import ContextService


class TestMetadataContext:

    def teardown_method(self):
        repo.close()
        repo.override_db_path(None)

    def _svc(self, tmp_path):
        repo.override_db_path(os.path.join(str(tmp_path), "ctx.sqlite"))
        return ContextService()

    def test_metadata_saved_not_scan_finished(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.record_metadata_saved(count=3)
        events = svc.recent_events(limit=10)
        saved = [e for e in events if e["event_type"] == AppEvent.METADATA_SAVED]
        scanned = [e for e in events if e["event_type"] == AppEvent.SCAN_FINISHED]
        assert len(saved) == 1
        assert len(scanned) == 0

    def test_cover_updated_no_filepath(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.record_cover_updated(scope="album", count=1)
        events = svc.recent_events(limit=5)
        ev = next(e for e in events if e["event_type"] == AppEvent.COVER_UPDATED)
        raw = str(ev)
        assert "/home/" not in raw
        assert "/tmp/" not in raw

    def test_tags_batch_updated_registers_count(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.record_tags_batch_updated(count=10)
        events = svc.recent_events(limit=5)
        ev = next(e for e in events if e["event_type"] == AppEvent.TAGS_BATCH_UPDATED)
        assert ev["payload"].get("count") == 10

    def test_metadata_review_opened(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.record_metadata_review_opened(scope="album", count=5)
        events = svc.recent_events(limit=5)
        ev = next(e for e in events if e["event_type"] == AppEvent.METADATA_REVIEW_OPENED)
        assert ev["payload"].get("scope") == "album"

    def test_lyrics_updated_no_path(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.record_lyrics_updated(count=2)
        events = svc.recent_events(limit=5)
        ev = next(e for e in events if e["event_type"] == AppEvent.LYRICS_UPDATED)
        raw = str(ev)
        assert "filepath" not in raw
        assert "/" not in raw.split("count")[0]
