from __future__ import annotations

import time
import uuid

from core.lyrics.models import TrackIdentity


class LyricsTraceRecorder:
    def __init__(self):
        self._current: dict | None = None
        self._history: list[dict] = []

    def begin(self, request_id: str, identity: TrackIdentity):
        self._current = {
            "trace_id": str(uuid.uuid4())[:8],
            "request_id": request_id,
            "track_title": identity.title,
            "track_artist": identity.artist,
            "started_at": time.monotonic(),
            "sources": [],
            "result_code": "",
            "duration_ms": 0,
        }

    def record_source(self, source: str, result_code: str):
        if self._current:
            self._current["sources"].append({
                "source": source,
                "result_code": result_code,
                "timestamp": time.monotonic(),
            })

    def end(self, result_code: str):
        if self._current:
            self._current["duration_ms"] = (time.monotonic() - self._current["started_at"]) * 1000
            self._current["result_code"] = result_code
            trace = dict(self._current)
            self._history.append(trace)
            if len(self._history) > 100:
                self._history.pop(0)
            self._current = None

    @property
    def current_trace_id(self) -> str:
        if self._current:
            return self._current.get("trace_id", "")
        return ""

    def report(self) -> list[dict]:
        return list(self._history[-50:])

    def sanitized_report(self) -> list[dict]:
        return [
            {k: v for k, v in t.items() if k not in ("track_title", "track_artist")}
            for t in self._history[-50:]
        ]
