from __future__ import annotations

import os
import tempfile

from michi_ai.v2.core.models import AssistantTrace
from michi_ai.v2.trace.trace_recorder import TraceRecorder


class TestTraceRecorder:
    def setup_method(self):
        self.tmp_name = tempfile.mktemp(suffix=".db")
        self.recorder = TraceRecorder(db_path=self.tmp_name)

    def teardown_method(self):
        self.recorder.close()
        os.unlink(self.tmp_name)

    def test_record_and_get_trace(self):
        trace = AssistantTrace(
            trace_id="trace_001", session_id="session_1",
            intent="play_album", provider="rules",
            tools=("play_track",),
            timestamp="2025-01-01T00:00:00",
        )
        self.recorder.record(trace)
        retrieved = self.recorder.get_trace("trace_001")
        assert retrieved is not None
        assert retrieved["trace_id"] == "trace_001"
        assert retrieved["intent"] == "play_album"

    def test_get_nonexistent_trace(self):
        result = self.recorder.get_trace("nonexistent")
        assert result is None

    def test_get_recent(self):
        for i in range(3):
            trace = AssistantTrace(
                trace_id=f"trace_{i:03d}",
                session_id="s1", intent=f"intent_{i}",
                provider="rules", timestamp="2025-01-01T00:00:00",
            )
            self.recorder.record(trace)
        recent = self.recorder.get_recent(limit=2)
        assert len(recent) <= 2

    def test_record_event(self):
        self.recorder.record_event("trace_001", "step_start", {"step": 1})
        # No direct getter for events, but we verify no crash

    def test_export_sanitized(self):
        trace = AssistantTrace(
            trace_id="trace_001", session_id="secret_session",
            request_id="req_1", intent="test", provider="rules",
            timestamp="2025-01-01T00:00:00",
        )
        self.recorder.record(trace)
        exported = self.recorder.export_sanitized(limit=10)
        assert len(exported) > 0
        for t in exported:
            assert "request_id" not in t
            assert "session_id" not in t

    def test_cleanup_old(self):
        trace = AssistantTrace(
            trace_id="old_trace", session_id="s1", intent="test",
            provider="rules", timestamp="2020-01-01T00:00:00",
        )
        self.recorder.record(trace)
        count = self.recorder.cleanup_old(max_age_days=1)
        assert count > 0

    def test_sanitize_payload(self):
        payload = {
            "token": "secret123",
            "api_key": "abc",
            "password": "hunter2",
            "safe_field": "visible",
        }
        sanitized = self.recorder._sanitize_payload(payload)
        assert "token" not in sanitized
        assert "api_key" not in sanitized
        assert "password" not in sanitized
        assert sanitized.get("safe_field") == "visible"
