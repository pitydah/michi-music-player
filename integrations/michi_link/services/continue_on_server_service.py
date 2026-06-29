"""ContinueOnServerService — handoff playback from Player to Micro Server.

Real implementation: reads the Player's current queue, resolves track_ids,
sends the queue to the Micro Server, and pauses local playback on success.
"""
from __future__ import annotations

import json
import logging
import urllib.request

from integrations.michi_link.client import RemoteServerInfo
from integrations.michi_link.services.result import Result

logger = logging.getLogger("michi.service.continue_on_server")


class ContinueOnServerService:
    """Service for handing off playback queue to a remote Micro Server.

    Requires a queue_provider callable that returns (track_ids, current_index, position_ms)
    and a pause_local callable that pauses local playback.
    """

    def __init__(self, queue_provider=None, pause_local=None,
                 resolve_track=None):
        self._queue_provider = queue_provider
        self._pause_local = pause_local
        self._resolve_track = resolve_track

    def _get_queue(self) -> tuple[list[str], int, float]:
        """Get current queue from provider. Returns (track_ids, index, position_ms)."""
        if self._queue_provider:
            return self._queue_provider()
        return [], -1, 0.0

    def _resolve_track_ids(self, track_ids: list[str]) -> list[str]:
        """Resolve internal track IDs to API-compatible track_ids."""
        if self._resolve_track:
            return [self._resolve_track(t) or t for t in track_ids]
        return track_ids

    def transfer_queue(self, server: RemoteServerInfo,
                       track_ids: list[str] | None = None,
                       position_ms: float = 0.0) -> Result:
        """Send the current Player queue to a Micro Server for continued playback.

        If track_ids is None, reads from the queue_provider.
        """
        if track_ids is None:
            ids, index, pos = self._get_queue()
            track_ids = ids
            if position_ms == 0.0:
                position_ms = pos
        else:
            index = 0

        resolved_ids = self._resolve_track_ids(track_ids)
        body = json.dumps({
            "track_ids": resolved_ids,
            "current_index": index,
            "position_ms": position_ms,
            "source": "michi-music-player",
        }).encode()
        try:
            headers = {"Content-Type": "application/json"}
            if server.device_token:
                headers["Authorization"] = f"Bearer {server.device_token}"
                headers["X-Michi-Device-Id"] = server.device_id
            req = urllib.request.Request(
                f"http://{server.host}:{server.port}/api/v1/queue/transfer",
                data=body, method="POST", headers=headers,
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                resp = json.loads(r.read().decode())
        except Exception as e:
            logger.warning("Queue transfer to %s:%d failed: %s",
                           server.host, server.port, e)
            return Result.fail("TRANSFER_FAILED", str(e))

        # Pause local playback on success
        if self._pause_local:
            try:
                self._pause_local()
                logger.info("Local playback paused after queue transfer")
            except Exception as e:
                logger.warning("Failed to pause local playback: %s", e)

        return Result.success(resp, f"Queue transferred ({len(resolved_ids)} tracks)")

    def start_remote_playback(self, server: RemoteServerInfo) -> Result:
        """Tell the Micro Server to start playing."""
        try:
            headers = {"Content-Type": "application/json"}
            if server.device_token:
                headers["Authorization"] = f"Bearer {server.device_token}"
                headers["X-Michi-Device-Id"] = server.device_id
            req = urllib.request.Request(
                f"http://{server.host}:{server.port}/api/v1/playback/control",
                data=json.dumps({"command": "play"}).encode(),
                method="POST", headers=headers,
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                ok = r.status == 200
        except Exception as e:
            logger.warning("Remote playback start failed: %s", e)
            return Result.fail("REMOTE_PLAY_FAILED", str(e))
        return Result.success({"playing": ok}, "Remote playback started")

    def stop_remote_playback(self, server: RemoteServerInfo) -> Result:
        """Tell the Micro Server to stop playing."""
        try:
            headers = {"Content-Type": "application/json"}
            if server.device_token:
                headers["Authorization"] = f"Bearer {server.device_token}"
                headers["X-Michi-Device-Id"] = server.device_id
            req = urllib.request.Request(
                f"http://{server.host}:{server.port}/api/v1/playback/control",
                data=json.dumps({"command": "stop"}).encode(),
                method="POST", headers=headers,
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                ok = r.status == 200
        except Exception as e:
            logger.warning("Remote playback stop failed: %s", e)
            return Result.fail("REMOTE_STOP_FAILED", str(e))
        return Result.success({"stopped": ok}, "Remote playback stopped")
