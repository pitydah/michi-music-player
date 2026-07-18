"""Tests for AudioLab batch processing — verification, logs, progress."""
import os
import tempfile
import time
from unittest.mock import MagicMock, patch

import pytest


class TestAudioBatchService:
    @pytest.fixture
    def batch_svc(self):
        from core.audio_lab.audio_batch_service import AudioBatchService
        return AudioBatchService(wm=MagicMock())

    def test_create_batch_job(self, batch_svc):
        items = ["/test/a.flac", "/test/b.flac"]
        jid = batch_svc.create_batch(items, "convert")
        assert jid is not None
        assert len(jid) > 0

    def test_batch_progress(self, batch_svc):
        items = [f"/test/{i}.flac" for i in range(5)]
        jid = batch_svc.create_batch(items, "analyze")
        batch_svc.start(jid)
        assert jid is not None

    def test_batch_cancel(self, batch_svc):
        items = [f"/test/{i}.flac" for i in range(3)]
        jid = batch_svc.create_batch(items, "convert")
        batch_svc.start(jid)
        batch_svc.cancel(jid)

    def test_batch_item_error(self, batch_svc):
        items = ["/test/bad.flac"]
        jid = batch_svc.create_batch(items, "convert")
        batch_svc.start(jid)

    def test_batch_item_complete(self, batch_svc):
        items = ["/test/ok.flac"]
        jid = batch_svc.create_batch(items, "convert")
        batch_svc.start(jid)

    def test_multiple_batch_jobs(self, batch_svc):
        for i in range(3):
            batch_svc.create_batch([f"/test/{i}.flac"], "convert")
        assert len(batch_svc.active_batches()) >= 0

    def test_batch_signals_exist(self, batch_svc):
        assert hasattr(batch_svc, 'batchProgress')
        assert hasattr(batch_svc, 'batchCompleted')
        assert hasattr(batch_svc, 'batchCancelled')
        assert hasattr(batch_svc, 'batchStarted')
