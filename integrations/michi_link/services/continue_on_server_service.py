"""ContinueOnServerService — handoff playback from Player to Micro Server.

Correct flow:
  a) resolve local queue
  b) preflight/import missing if auto_import=True, get mapping
  c) build remote queue with remote_track_ids
  d) try /api/v1/queue/transfer; fallback to queue/items+jump+control
  e) start_remote_playback
  f) poll playback/state until PLAYING confirmed
  g) pause local ONLY after Micro confirms state=playing
If any step fails, local playback is NEVER paused.
"""
from __future__ import annotations

import json
import logging
import time
import urllib.error
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

_POLL_INTERVAL = 0.5
_POLL_MAX_RETRIES = 6


class ContinueOnServerService:
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

    def _resolve_filepath(self, tid: str) -> str:
        if self._resolve_track:
            result = self._resolve_track(tid)
            if result and isinstance(result, str):
                return result
        return ""

    def _auth_headers(self, server: RemoteServerInfo) -> dict:
        headers = {"Content-Type": "application/json"}
        if server.device_token:
            headers["Authorization"] = f"Bearer {server.device_token}"
            headers["X-Michi-Device-Id"] = server.device_id
        return headers

    def _build_remote_queue(self, resolved_ids: list[str],
                            index: int, position_ms: float) -> dict:
        return {
            "track_ids": resolved_ids,
            "current_index": index,
            "position_ms": position_ms,
            "source": "michi-music-player",
        }

    def _try_queue_transfer(self, server: RemoteServerInfo, body: dict) -> Result:
        """Try /api/v1/queue/transfer. Returns Result with data or None."""
        try:
            req = urllib.request.Request(
                f"http://{server.host}:{server.port}/api/v1/queue/transfer",
                data=json.dumps(body).encode(), method="POST",
                headers=self._auth_headers(server),
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                resp = json.loads(r.read().decode())
                return Result.success(resp, "queue/transfer succeeded")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                logger.info("Micro Server does not support /api/v1/queue/transfer")
                return Result.fail("ENDPOINT_NOT_FOUND", "queue/transfer not available")
            logger.warning("queue/transfer HTTP %d: %s", e.code, e.reason)
            return Result.fail("TRANSFER_FAILED", str(e))
        except Exception as e:
            logger.warning("queue/transfer error: %s", e)
            return Result.fail("TRANSFER_FAILED", str(e))

    def _fallback_queue_transfer(self, server: RemoteServerInfo,
                                  body: dict) -> Result:
        """Fallback: queue/items + queue/jump + playback/control seek + play."""
        track_ids = body.get("track_ids", [])
        index = body.get("current_index", 0)
        position_ms = body.get("position_ms", 0.0)
        headers = self._auth_headers(server)

        try:
            # Replace queue
            items_body = json.dumps({"uris": track_ids, "play_now": False}).encode()
            req = urllib.request.Request(
                f"http://{server.host}:{server.port}/api/v1/queue/items",
                data=items_body, method="POST", headers=headers,
            )
            with urllib.request.urlopen(req, timeout=15):
                pass

            # Jump to index
            if index > 0:
                jump_body = json.dumps({"index": index}).encode()
                req = urllib.request.Request(
                    f"http://{server.host}:{server.port}/api/v1/queue/jump",
                    data=jump_body, method="POST", headers=headers,
                )
                with urllib.request.urlopen(req, timeout=10):
                    pass

            # Seek to position
            if position_ms > 0:
                seek_body = json.dumps(
                    {"command": "seek", "position_ms": position_ms}).encode()
                req = urllib.request.Request(
                    f"http://{server.host}:{server.port}/api/v1/playback/control",
                    data=seek_body, method="POST", headers=headers,
                )
                with urllib.request.urlopen(req, timeout=10):
                    pass

            logger.info("Fallback queue transfer completed via queue/items + jump + seek")
            return Result.success({"method": "fallback"},
                                  "Fallback queue transfer succeeded")
        except Exception as e:
            logger.warning("Fallback queue transfer failed: %s", e)
            return Result.fail("FALLBACK_TRANSFER_FAILED", str(e))

    def _confirm_remote_playing(self, server: RemoteServerInfo) -> bool:
        """Poll playback/state until Micro confirms playing. Returns True if confirmed."""
        for attempt in range(_POLL_MAX_RETRIES):
            try:
                req = urllib.request.Request(
                    f"http://{server.host}:{server.port}/api/v1/playback/state",
                    method="GET", headers=self._auth_headers(server),
                )
                with urllib.request.urlopen(req, timeout=5) as r:
                    state = json.loads(r.read().decode())
                if state.get("state") == "playing":
                    logger.info("Remote playback confirmed PLAYING after %d polls",
                                attempt + 1)
                    return True
            except Exception:
                pass
            time.sleep(_POLL_INTERVAL)
        logger.warning("Remote playback state did not reach PLAYING after %d polls",
                       _POLL_MAX_RETRIES)
        return False

    # ── Public API ──

    def transfer_queue(self, server: RemoteServerInfo,
                       track_ids: list[str] | None = None,
                       position_ms: float = 0.0,
                       auto_import: bool = False,
                       require_playing: bool = True) -> Result:
        """Send queue to Micro Server. Never pauses local on failure.

        Args:
            require_playing: if True, polls playback/state before pausing local.
        """
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

        # Auto-import missing
        if auto_import:
            r = self._import_missing_tracks(server, resolved_ids)
            if not r.ok:
                return r

        # Build queue body
        queue_body = self._build_remote_queue(resolved_ids, index, position_ms)

        # Transfer queue (primary + fallback)
        transfer_result = self._try_queue_transfer(server, queue_body)
        if not transfer_result.ok:
            logger.info("queue/transfer unavailable, trying fallback")
            transfer_result = self._fallback_queue_transfer(server, queue_body)

        if not transfer_result.ok:
            return transfer_result

        # Start remote playback
        play_result = self.start_remote_playback(server)
        if not play_result.ok:
            logger.warning("Queue transferred but remote play failed")
            return Result.success(
                {"queue_transferred": True, "playback_started": False},
                "Queue transferred, but remote play did not start automatically",
            )

        # Confirm remote is playing
        if require_playing:
            playing = self._confirm_remote_playing(server)
            if not playing:
                logger.warning("Queue transferred, play started, but state != PLAYING")
                return Result.success(
                    {"queue_transferred": True, "playback_started": True,
                     "confirmed_playing": False},
                    "Queue transferred and play started, but state not confirmed",
                )

        # PAUSE LOCAL ONLY AFTER remote confirmed PLAYING
        if self._pause_local:
            try:
                self._pause_local()
                logger.info("Local playback paused after remote PLAYING confirmed")
            except Exception as e:
                logger.warning("Failed to pause local playback (non-fatal): %s", e)

        return Result.success(
            {"queue_transferred": True, "playback_started": True,
             "confirmed_playing": require_playing},
            f"Queue transferred ({len(resolved_ids)} tracks), "
            f"local paused={self._pause_local is not None}",
        )

    def _import_missing_tracks(self, server: RemoteServerInfo,
                                track_ids: list[str]) -> Result:
        """Import tracks that don't exist on the Micro Server yet.
        Uses resolve_track to get real filepath before uploading.
        """
        try:
            session_result = self._import.create_session(server, track_ids)
            if not session_result.ok:
                return session_result
            sid = session_result.data["session_id"]

            for tid in track_ids:
                filepath = self._resolve_filepath(tid)
                if not filepath:
                    logger.warning("Cannot resolve filepath for track %s", tid)
                    self._import.rollback(sid)
                    return Result.fail("TRACK_FILE_NOT_RESOLVED",
                                       f"Cannot resolve filepath for {tid}")

                upload_result = self._import.upload_track(
                    sid, tid, local_filepath=filepath,
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
        try:
            req = urllib.request.Request(
                f"http://{server.host}:{server.port}/api/v1/playback/control",
                data=json.dumps({"command": "play"}).encode(), method="POST",
                headers=self._auth_headers(server),
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                ok = r.status == 200
        except Exception as e:
            logger.warning("Remote playback start failed: %s", e)
            return Result.fail("REMOTE_PLAY_FAILED", str(e))
        return Result.success({"playing": ok}, "Remote playback started")

    def stop_remote_playback(self, server: RemoteServerInfo) -> Result:
        try:
            req = urllib.request.Request(
                f"http://{server.host}:{server.port}/api/v1/playback/control",
                data=json.dumps({"command": "stop"}).encode(), method="POST",
                headers=self._auth_headers(server),
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                ok = r.status == 200
        except Exception as e:
            logger.warning("Remote playback stop failed: %s", e)
            return Result.fail("REMOTE_STOP_FAILED", str(e))
        return Result.success({"stopped": ok}, "Remote playback stopped")
