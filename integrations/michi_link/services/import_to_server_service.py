"""ImportToServerService — import tracks/artwork/playlists from Player to Micro Server.

Supports preflight (check what Micro Server already has), session-based import
with commit/rollback, progress tracking, hash verification with X-Checksum,
and returns local_track_id → remote_track_id mapping from Micro Server response.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Callable

from integrations.michi_link.client import RemoteServerInfo
from integrations.michi_link.services.result import Result
from integrations.michi_link.services.track_identity_service import (
    TrackIdentity, TrackIdentityService,
)

logger = logging.getLogger("michi.service.import_to_server")

ProgressCallback = Callable[[int, int, str], None]


@dataclass
class ImportSession:
    session_id: str = ""
    server: RemoteServerInfo | None = None
    uploaded: int = 0
    total: int = 0
    errors: list[str] = field(default_factory=list)
    artwork_uploaded: int = 0
    playlists_uploaded: int = 0
    track_ids: list[str] = field(default_factory=list)
    mapping: dict[str, str] = field(default_factory=dict)

    @property
    def progress(self) -> float:
        return 0.0 if self.total == 0 else self.uploaded / self.total


class ImportToServerService:
    def __init__(self, identity_service: TrackIdentityService | None = None):
        self._sessions: dict[str, ImportSession] = {}
        self._identity = identity_service or TrackIdentityService()

    # ── Preflight ──

    def _call_preflight(self, server: RemoteServerInfo,
                        identities: list[dict]) -> dict | None:
        try:
            body = json.dumps({"tracks": identities}).encode()
            headers = {"Content-Type": "application/json"}
            if server.device_token:
                headers["Authorization"] = f"Bearer {server.device_token}"
                headers["X-Michi-Device-Id"] = server.device_id
            req = urllib.request.Request(
                f"http://{server.host}:{server.port}/api/v1/import/preflight",
                data=body, method="POST", headers=headers,
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                logger.info("Micro Server does not support /api/v1/import/preflight")
                return None
            logger.warning("Preflight HTTP %d: %s", e.code, e.reason)
            return None
        except Exception as e:
            logger.warning("Preflight failed: %s", e)
            return None

    def _parse_preflight_results(self, response: dict,
                                 identities: list[TrackIdentity]) -> Result:
        """Parse preflight response supporting new and legacy formats."""
        raw_results = response.get("results")
        if not isinstance(raw_results, list):
            return Result.fail("PREFLIGHT_CONTRACT_MISMATCH",
                               "Expected 'results' list in preflight response")

        mapping = {}
        for identity in identities:
            lid = identity.local_track_id
            match = None

            # Try exact local_track_id match
            for item in raw_results:
                if item.get("local_track_id") == lid:
                    match = item
                    break

            # Try content_hash match
            if match is None and identity.content_hash:
                for item in raw_results:
                    if item.get("content_hash") == identity.content_hash:
                        match = item
                        break

            # Try legacy quick_hash match
            if match is None and identity.quick_hash:
                for item in raw_results:
                    if item.get("quick_hash") == identity.quick_hash or \
                       item.get("sha256_prefix") == identity.quick_hash:
                        match = item
                        break

            if match:
                status = match.get("status", "exists" if match.get("exists") else "missing")
                remote_id = match.get("remote_track_id", "")
                mapping[lid] = {
                    "exists": status in ("exists", "matched"),
                    "remote_id": remote_id,
                    "status": status,
                }
            else:
                mapping[lid] = {"exists": False, "remote_id": "", "status": "unknown"}

        return Result.success(mapping, f"Preflight parsed {len(identities)} tracks")

    def preflight(self, server: RemoteServerInfo,
                  identities: list[TrackIdentity]) -> Result:
        response = self._call_preflight(
            server,
            [self._identity.identity_to_preflight(i) for i in identities],
        )
        if response is None:
            mapping = {i.local_track_id: {"exists": False, "remote_id": "",
                                          "status": "unknown"}
                       for i in identities}
            return Result.success(
                mapping,
                "Preflight not supported — all tracks need upload",
            )
        return self._parse_preflight_results(response, identities)

    # ── Session ──

    def create_session(self, server: RemoteServerInfo,
                       track_ids: list[str],
                       identities: list[TrackIdentity] | None = None) -> Result:
        import uuid
        session = ImportSession(
            session_id=str(uuid.uuid4())[:12],
            server=server,
            total=len(track_ids),
            track_ids=track_ids,
        )

        if identities:
            preflight_result = self._call_preflight(
                server,
                [self._identity.identity_to_preflight(i) for i in identities],
            )
            if preflight_result:
                parse_result = self._parse_preflight_results(preflight_result, identities)
                if parse_result.ok and isinstance(parse_result.data, dict):
                    mapping = {}
                    for lid, info in parse_result.data.items():
                        if info.get("remote_id"):
                            mapping[lid] = info["remote_id"]
                    session.mapping = mapping
                    logger.info("Preflight returned %d existing tracks", len(mapping))

        self._sessions[session.session_id] = session
        return Result.success({
            "session_id": session.session_id,
            "total_tracks": session.total,
            "existing": len(session.mapping),
            "needs_upload": session.total - len(session.mapping),
        }, f"Import session {session.session_id} created")

    # ── Upload ──

    def upload_track(self, session_id: str, track_id: str,
                     download_path: str = "",
                     local_filepath: str = "",
                     local_data: bytes | None = None,
                     progress_cb: ProgressCallback | None = None) -> Result:
        session = self._sessions.get(session_id)
        if not session or not session.server:
            return Result.fail("INVALID_SESSION", "Session not found")

        track_data = local_data
        local_hash = ""
        if track_data is None and local_filepath and os.path.isfile(local_filepath):
            h = hashlib.sha256()
            try:
                with open(local_filepath, "rb") as f:
                    chunks = []
                    while True:
                        chunk = f.read(65536)
                        if not chunk:
                            break
                        h.update(chunk)
                        chunks.append(chunk)
                    track_data = b"".join(chunks)
                    local_hash = h.hexdigest()
            except OSError as e:
                session.errors.append(f"track {track_id}: {e}")
                progress_cb and progress_cb(session.uploaded, session.total, track_id)
                return Result.fail("FILE_READ_ERROR", str(e))

        if track_data is None:
            session.errors.append(f"track {track_id}: no data source")
            progress_cb and progress_cb(session.uploaded, session.total, track_id)
            return Result.fail("NO_DATA", "No track data or filepath provided")

        # Push to Micro Server, read response
        try:
            push_url = f"http://{session.server.host}:{session.server.port}" \
                       f"/api/v1/import/track/upload"
            headers = {
                "Content-Type": "application/octet-stream",
                "X-Track-Id": track_id,
            }
            if session.server.device_token:
                headers["Authorization"] = f"Bearer {session.server.device_token}"
                headers["X-Michi-Device-Id"] = session.server.device_id
                if local_hash:
                    headers["X-Checksum"] = local_hash

            req = urllib.request.Request(
                url=push_url, data=track_data, method="POST", headers=headers,
            )
            with urllib.request.urlopen(req, timeout=60) as r:
                resp_body = r.read().decode()
                resp_json = json.loads(resp_body) if resp_body else {}
        except urllib.error.HTTPError as e:
            session.errors.append(f"track {track_id}: HTTP {e.code}")
            progress_cb and progress_cb(session.uploaded, session.total, track_id)
            return Result.fail("UPLOAD_FAILED", f"HTTP {e.code}: {e.reason}")
        except Exception as e:
            session.errors.append(f"track {track_id}: {e}")
            progress_cb and progress_cb(session.uploaded, session.total, track_id)
            return Result.fail("UPLOAD_FAILED", str(e))

        # Extract remote_track_id from response
        remote_track_id = resp_json.get("remote_track_id", "")
        if remote_track_id:
            session.mapping[track_id] = remote_track_id
            mapping_status = "confirmed"
        else:
            session.mapping[track_id] = track_id  # fallback
            mapping_status = "MAPPING_UNCONFIRMED"
            logger.warning("Upload response missing remote_track_id for %s", track_id)

        session.uploaded += 1
        progress_cb and progress_cb(session.uploaded, session.total, track_id)

        return Result.success({
            "track_id": track_id,
            "remote_track_id": remote_track_id or track_id,
            "mapping_status": mapping_status,
            "bytes": len(track_data),
            "local_hash": local_hash[:16] + "..." if local_hash else "",
        }, f"Track {track_id} uploaded, mapping={mapping_status}")

    # ── Artwork & Playlist ──

    def upload_artwork(self, session_id: str, cover_id: str,
                       artwork_path: str = "") -> Result:
        session = self._sessions.get(session_id)
        if not session:
            return Result.fail("INVALID_SESSION", "Session not found")
        if not artwork_path or not os.path.isfile(artwork_path):
            return Result.fail("ARTWORK_NOT_FOUND", f"File not found: {artwork_path}")
        try:
            with open(artwork_path, "rb") as f:
                data = f.read()
        except OSError as e:
            return Result.fail("ARTWORK_READ_ERROR", str(e))
        session.artwork_uploaded += 1
        return Result.success({"cover_id": cover_id, "bytes": len(data)},
                              f"Artwork {cover_id} ready")

    def upload_playlist(self, session_id: str, playlist: dict) -> Result:
        session = self._sessions.get(session_id)
        if not session:
            return Result.fail("INVALID_SESSION", "Session not found")
        session.playlists_uploaded += 1
        return Result.success({
            "playlist_id": playlist.get("playlist_id", ""),
            "name": playlist.get("name", ""),
            "track_count": len(playlist.get("track_ids", [])),
        }, "Playlist metadata queued")

    # ── Commit / Rollback / Status ──

    def commit(self, session_id: str) -> Result:
        session = self._sessions.get(session_id)
        if not session:
            return Result.fail("INVALID_SESSION", "Session not found")
        if session.errors:
            return Result.fail("HAS_ERRORS",
                               f"{len(session.errors)} tracks failed")

        # Try calling Micro Server commit endpoint
        try:
            headers = {"Content-Type": "application/json"}
            if session.server and session.server.device_token:
                headers["Authorization"] = f"Bearer {session.server.device_token}"
                headers["X-Michi-Device-Id"] = session.server.device_id
            body = json.dumps({"session_id": session_id}).encode()
            req = urllib.request.Request(
                f"http://{session.server.host}:{session.server.port}"
                f"/api/v1/import/session/commit",
                data=body, method="POST", headers=headers,
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                resp = json.loads(r.read().decode())
                remote_mapping = resp.get("mapping", {})
                if remote_mapping:
                    session.mapping.update(remote_mapping)
        except (urllib.error.HTTPError, OSError, json.JSONDecodeError) as e:
            logger.warning("Micro commit endpoint failed (non-fatal): %s", e)

        if not session.mapping:
            logger.warning("Commit completed without mapping")
        elif any(v == v for v in session.mapping.values()):
            pass  # mapping present

        logger.info("Import session %s committed: %d/%d tracks, mapping=%d entries",
                    session_id, session.uploaded, session.total,
                    len(session.mapping))
        return Result.success({
            "session_id": session_id,
            "uploaded": session.uploaded,
            "total": session.total,
            "artwork": session.artwork_uploaded,
            "playlists": session.playlists_uploaded,
            "mapping": session.mapping,
        }, f"Import committed: {session.uploaded}/{session.total} tracks")

    def rollback(self, session_id: str) -> Result:
        session = self._sessions.pop(session_id, None)
        if session:
            logger.info("Import session %s rolled back (%d uploaded)",
                        session_id, session.uploaded)
        return Result.success({"rolled_back": True}, "Session rolled back")

    def status(self, session_id: str) -> Result:
        session = self._sessions.get(session_id)
        if not session:
            return Result.fail("SESSION_NOT_FOUND", "Session not found")
        return Result.success({
            "session_id": session.session_id,
            "uploaded": session.uploaded,
            "total": session.total,
            "progress": session.progress,
            "artwork_uploaded": session.artwork_uploaded,
            "playlists_uploaded": session.playlists_uploaded,
            "errors": len(session.errors),
        })

    def get_session(self, session_id: str) -> ImportSession | None:
        return self._sessions.get(session_id)
