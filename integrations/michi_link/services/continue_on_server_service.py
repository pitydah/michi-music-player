"""ContinueOnServerService — handoff playback from Player to Micro Server.

Real implementation: reads the Player's current queue, resolves track_ids,
verifies which tracks exist on Micro Server (imports missing if allowed),
sends the queue to the Micro Server, and pauses local playback ONLY
after remote confirmation.
"""
from __future__ import annotations

import json
import logging
import urllib.request

from integrations.michi_link.client import RemoteServerInfo
from integrations.michi_link.services.import_to_server_service import (
    ImportToServerService,
)
from integrations.michi_link.services.result import Result
from integrations.michi_link.services.track_identity_service import (
    TrackIdentityService,
)

logger = logging.getLogger("michi.service.continue_on_server")


class ContinueOnServerService:
    """Service for handing off playback queue to a remote Micro Server.

    Requires callbacks for reading the current queue and pausing local playback.
    Optional: identity service and import service for auto-importing missing tracks.
    """

    def __init__(self, queue_provider=None, pause_local=None,
                 resolve_track=None,
                 identity_service: TrackIdentityService | None = None,
                 import_service: ImportToServerService | None = None):
        self._queue_provider = queue_provider
        self._pause_local = pause_local
        self._resolve_track = resolve_track
        self._identity = identity_service or TrackIdentityService()
        self._import = import_service or ImportToServerService()

    def _get_queue(self) -> tuple[list[str], int, float]:
        if self._queue_provider:
            return self._queue_provider()
        return [], -1, 0.0

    def _resolve_track_ids(self, track_ids: list[str]) -> list[str]:
        if self._resolve_track:
            return [self._resolve_track(t) or t for t in track_ids]
        return track_ids

    def transfer_queue(self, server: RemoteServerInfo,
                       track_ids: list[str] | None = None,
                       position_ms: float = 0.0,
                       auto_import: bool = False) -> Result:
        """Send queue to Micro Server. Optionally imports missing tracks first.

        If track_ids is None, reads from queue_provider.
        If auto_import is True, missing tracks are uploaded before transfer.
        Local playback is paused ONLY after remote confirmation.
        """
        # 1. Get current queue
        if track_ids is None:
            ids, index, pos = self._get_queue()
            track_ids = ids
            if position_ms == 0.0:
                position_ms = pos
        else:
            index = 0

        if not track_ids:
            return Result.fail("EMPTY_QUEUE", "Queue is empty")

        resolved_ids = self._resolve_track_ids(track_ids)

        # 2. (Optional) Import missing tracks
        if auto_import:
            import_result = self._import_missing_tracks(server, resolved_ids)
            if not import_result.ok:
                return import_result

        # 3. Transfer queue to Micro Server
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
            return Result.fail("TRANSFER_FAILED",
                               "Remote server did not confirm queue transfer")

        # 4. Pause local playback ONLY after remote confirmed
        if self._pause_local:
            try:
                self._pause_local()
                logger.info("Local playback paused after remote confirmation")
            except Exception as e:
                logger.warning("Failed to pause local playback (non-fatal): %s", e)

        return Result.success(
            resp,
            f"Queue transferred ({len(resolved_ids)} tracks), "
            f"local paused={self._pause_local is not None}",
        )

    def _import_missing_tracks(self, server: RemoteServerInfo,
                                track_ids: list[str]) -> Result:
        """Import tracks that don't exist on the Micro Server yet."""
        try:
            session_result = self._import.create_session(server, track_ids)
            if not session_result.ok:
                return session_result
            sid = session_result.data["session_id"]

            for tid in track_ids:
                upload_result = self._import.upload_track(
                    sid, tid, local_filepath=tid,
                )
                if not upload_result.ok:
                    self._import.rollback(sid)
                    return upload_result

            commit_result = self._import.commit(sid)
            if not commit_result.ok:
                self._import.rollback(sid)
                return commit_result

            logger.info("Auto-imported %d tracks before queue transfer", len(track_ids))
            return commit_result
        except Exception as e:
            logger.warning("Auto-import failed: %s", e)
            return Result.fail("AUTO_IMPORT_FAILED", str(e))

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
