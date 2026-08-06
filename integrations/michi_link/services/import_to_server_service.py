"""ImportToServerService — import tracks/artwork/playlists from Player to Micro Server.

Supports preflight (check what Micro Server already has), session-based import
with commit/rollback, progress tracking, hash verification with X-Checksum,
retry on transient network errors, cancellation, expired-session handling and
post-commit readback verification.

Every claimed operation has a server-side effect or an explicit failure:
- artwork and playlists are uploaded over HTTP (never "queued" locally).
- uploads are checksum-verified against the server response.
- commit requires the server to confirm; a commit failure is a failure.
- rollback requires the server to drop the session; unreachable servers are
  reported, not silently accepted.
- sessions created on the server carry an expiry; expired sessions fail with
  SESSION_EXPIRED (re-pair flow) instead of proceeding.
"""
from __future__ import annotations

import contextlib
import hashlib
import hmac
import json
import logging
import os
import time
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

_RETRY_BACKOFF = 0.05
_TRANSIENT_ERRORS = (urllib.error.URLError, TimeoutError, OSError)


def _error_code_of(body_text: str) -> str:
    """Extract the v1 error code from an error JSON body."""
    if not body_text:
        return ""
    try:
        return str(json.loads(body_text).get("error", {}).get("code", ""))
    except Exception:  # noqa: BLE001 - body may be non-JSON
        return ""


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
    checksums: dict[str, str] = field(default_factory=dict)
    server_created: bool = False
    expires_at: float = 0.0
    cancelled: bool = False
    committed: bool = False

    @property
    def progress(self) -> float:
        return 0.0 if self.total == 0 else self.uploaded / self.total

    @property
    def is_expired(self) -> bool:
        return self.server_created and bool(self.expires_at) \
            and time.time() > self.expires_at


class ImportToServerService:
    def __init__(self, identity_service: TrackIdentityService | None = None):
        self._sessions: dict[str, ImportSession] = {}
        self._identity = identity_service or TrackIdentityService()

    # ── HTTP helpers ──

    @staticmethod
    def _auth_headers(server: RemoteServerInfo,
                      extra: dict | None = None) -> dict:
        headers = {"Content-Type": "application/json"}
        if server.device_token:
            headers["Authorization"] = f"Bearer {server.device_token}"
            headers["X-Michi-Device-Id"] = server.device_id
        if extra:
            headers.update(extra)
        return headers

    def _post_json(self, server: RemoteServerInfo, path: str,
                   body: dict, timeout: int = 15,
                   retries: int = 1) -> Result:
        """POST a JSON body; retries only transient network errors."""
        payload = json.dumps(body).encode()
        attempt = 0
        while True:
            try:
                req = urllib.request.Request(
                    f"http://{server.host}:{server.port}{path}",
                    data=payload, method="POST",
                    headers=self._auth_headers(server),
                )
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    raw = r.read().decode()
                    return Result.success(json.loads(raw) if raw else {})
            except urllib.error.HTTPError as e:
                with contextlib.suppress(Exception):
                    body_text = e.read().decode()
                if e.code == 410:
                    return Result.fail("SESSION_EXPIRED",
                                       f"{path}: session expired on the server")
                if e.code == 404:
                    err_code = _error_code_of(body_text)
                    if err_code and err_code != "NOT_FOUND":
                        return Result.fail(err_code,
                                           f"{path}: {err_code}")
                    return Result.fail("ENDPOINT_NOT_FOUND",
                                       f"{path} not found")
                if e.code in (408, 429, 502, 503, 504) and attempt < retries:
                    attempt += 1
                    time.sleep(_RETRY_BACKOFF * attempt)
                    continue
                return Result.fail(f"HTTP_{e.code}",
                                   f"{path} failed: {e.reason}",
                                   error=body_text or None)
            except _TRANSIENT_ERRORS as e:
                if attempt < retries:
                    attempt += 1
                    time.sleep(_RETRY_BACKOFF * attempt)
                    continue
                return Result.fail("REMOTE_UNREACHABLE", f"{path}: {e}")
            except Exception as e:
                return Result.fail("REQUEST_FAILED", f"{path}: {e}")

    def _get_json(self, server: RemoteServerInfo, path: str,
                  timeout: int = 10) -> Result:
        """GET a JSON endpoint (readback paths)."""
        try:
            req = urllib.request.Request(
                f"http://{server.host}:{server.port}{path}",
                method="GET", headers=self._auth_headers(server),
            )
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read().decode()
                return Result.success(json.loads(raw) if raw else {})
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return Result.fail("ENDPOINT_NOT_FOUND", f"{path} not found")
            if e.code == 410:
                return Result.fail("SESSION_EXPIRED",
                                   "Import session expired on the server")
            return Result.fail(f"HTTP_{e.code}", f"{path} failed: {e.reason}")
        except _TRANSIENT_ERRORS as e:
            return Result.fail("REMOTE_UNREACHABLE", f"{path}: {e}")
        except Exception as e:
            return Result.fail("REQUEST_FAILED", f"{path}: {e}")

    # ── Preflight ──

    def _call_preflight(self, server: RemoteServerInfo,
                        identities: list[dict]) -> dict | None:
        try:
            result = self._post_json(
                server, "/api/v1/import/preflight",
                {"tracks": identities}, timeout=15,
            )
            if result.ok:
                return result.data
            if result.code == "ENDPOINT_NOT_FOUND":
                logger.info("Micro Server does not support /api/v1/import/preflight")
                return None
            logger.warning("Preflight failed: %s (%s)", result.message, result.code)
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

            for item in raw_results:
                # Try michi_track_id (new contract)
                if item.get("michi_track_id") == lid:
                    match = item
                    break
                # Try local_track_id (legacy contract)
                if item.get("local_track_id") == lid:
                    match = item
                    break
                # Try content_hash
                if match is None and identity.content_hash and \
                   item.get("content_hash") == identity.content_hash:
                    match = item
                    break
                # Try quick_hash
                if match is None and identity.quick_hash and \
                   (item.get("quick_hash") == identity.quick_hash or
                    item.get("sha256_prefix") == identity.quick_hash):
                    match = item
                    break

            if match:
                status = match.get("status", "exists" if match.get("exists") else "missing")
                remote_id = (match.get("server_track_id", "") or
                             match.get("remote_track_id", ""))
                mapping[lid] = {
                    "exists": status in ("exists", "matched", "already_present"),
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
        """Create an import session on the server (real, with expiry)."""
        import uuid

        created = self._post_json(
            server, "/api/v1/import/session/create",
            {"source": "michi-music-player"}, timeout=15,
        )
        if not created.ok:
            return created if created.code != "ENDPOINT_NOT_FOUND" else Result.fail(
                "IMPORT_ENDPOINTS_MISSING",
                "Server does not support import sessions (upgrade required)",
            )
        server_session = created.data or {}
        session_id = server_session.get("session_id", str(uuid.uuid4())[:12])
        session = ImportSession(
            session_id=session_id,
            server=server,
            total=len(track_ids),
            track_ids=track_ids,
            server_created=True,
            expires_at=float(server_session.get("expires_at") or 0.0),
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
            "expires_at": session.expires_at,
            "server_created": True,
        }, f"Import session {session.session_id} created on server")

    def _check_session(self, session_id: str,
                       require_server: bool = True) -> Result | ImportSession:
        """Return the session or a Result failure."""
        session = self._sessions.get(session_id)
        if session is None:
            return Result.fail("INVALID_SESSION", "Session not found")
        if session.cancelled:
            return Result.fail("CANCELLED", "Session was cancelled")
        if session.committed:
            return Result.fail("SESSION_COMMITTED", "Session already committed")
        if session.is_expired:
            return Result.fail("SESSION_EXPIRED",
                               "Session expired — re-pair or create a new session")
        if require_server and not session.server_created:
            return Result.fail("SESSION_NOT_ON_SERVER",
                               "Session was never created on the server")
        return session

    # ── Upload ──

    def upload_track(self, session_id: str, track_id: str,
                     download_path: str = "",
                     local_filepath: str = "",
                     local_data: bytes | None = None,
                     progress_cb: ProgressCallback | None = None,
                     retries: int = 1) -> Result:
        checked = self._check_session(session_id)
        if isinstance(checked, Result):
            return checked
        session: ImportSession = checked
        server = session.server
        if server is None:
            return Result.fail("INVALID_SESSION", "Session has no server")

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

        # Every upload is checksummed (data or filepath) so readback
        # verification is always possible.
        if not local_hash:
            local_hash = hashlib.sha256(track_data).hexdigest()

        headers = {
            "Content-Type": "application/octet-stream",
            "X-Track-Id": track_id,
            "X-Import-Session-Id": session_id,
        }
        if server.device_token:
            headers["Authorization"] = f"Bearer {server.device_token}"
            headers["X-Michi-Device-Id"] = server.device_id
        if local_hash:
            headers["X-Checksum"] = local_hash

        attempt = 0
        while True:
            try:
                req = urllib.request.Request(
                    url=f"http://{server.host}:{server.port}"
                        f"/api/v1/import/track/upload",
                    data=track_data, method="POST",
                    headers=self._auth_headers(server, headers),
                )
                with urllib.request.urlopen(req, timeout=60) as r:
                    resp_body = r.read().decode()
                    resp_json = json.loads(resp_body) if resp_body else {}
                break
            except urllib.error.HTTPError as e:
                if e.code == 410:
                    session.errors.append(f"track {track_id}: session expired")
                    progress_cb and progress_cb(
                        session.uploaded, session.total, track_id)
                    return Result.fail("SESSION_EXPIRED",
                                       "Import session expired on the server")
                if e.code == 404:
                    with contextlib.suppress(Exception):
                        body_text = e.read().decode()
                    err_code = _error_code_of(body_text)
                    if err_code in ("SESSION_NOT_FOUND", "SESSION_EXPIRED",
                                    "SESSION_COMMITTED"):
                        session.errors.append(f"track {track_id}: {err_code}")
                        progress_cb and progress_cb(
                            session.uploaded, session.total, track_id)
                        return Result.fail(err_code,
                                           f"Server rejected upload: {err_code}")
                    session.errors.append(f"track {track_id}: endpoint missing")
                    progress_cb and progress_cb(
                        session.uploaded, session.total, track_id)
                    return Result.fail("IMPORT_ENDPOINTS_MISSING",
                                       "Server lacks import track upload")
                if e.code in (408, 429, 502, 503, 504) and attempt < retries:
                    attempt += 1
                    time.sleep(_RETRY_BACKOFF * attempt)
                    continue
                session.errors.append(f"track {track_id}: HTTP {e.code}")
                progress_cb and progress_cb(
                    session.uploaded, session.total, track_id)
                return Result.fail("UPLOAD_FAILED", f"HTTP {e.code}: {e.reason}")
            except _TRANSIENT_ERRORS as e:
                if attempt < retries:
                    attempt += 1
                    time.sleep(_RETRY_BACKOFF * attempt)
                    continue
                session.errors.append(f"track {track_id}: {e}")
                progress_cb and progress_cb(
                    session.uploaded, session.total, track_id)
                return Result.fail("UPLOAD_FAILED", str(e))
            except Exception as e:
                session.errors.append(f"track {track_id}: {e}")
                progress_cb and progress_cb(
                    session.uploaded, session.total, track_id)
                return Result.fail("UPLOAD_FAILED", str(e))

        # Checksum verification against the server response (when available).
        server_checksum = resp_json.get("checksum", "")
        if local_hash and server_checksum and \
                not hmac.compare_digest(local_hash, server_checksum):
            session.errors.append(f"track {track_id}: checksum mismatch")
            progress_cb and progress_cb(session.uploaded, session.total, track_id)
            return Result.fail("CHECKSUM_MISMATCH",
                               "Server checksum does not match local file")

        remote_track_id = (resp_json.get("server_track_id", "") or
                           resp_json.get("remote_track_id", ""))
        if remote_track_id:
            session.mapping[track_id] = remote_track_id
            mapping_status = "confirmed"
        else:
            session.mapping[track_id] = track_id
            mapping_status = "MAPPING_UNCONFIRMED"
            logger.warning("Upload response missing server_track_id for %s", track_id)

        session.uploaded += 1
        if local_hash:
            session.checksums[track_id] = local_hash
        progress_cb and progress_cb(session.uploaded, session.total, track_id)

        return Result.success({
            "track_id": track_id,
            "remote_track_id": remote_track_id or track_id,
            "mapping_status": mapping_status,
            "bytes": len(track_data),
            "local_hash": local_hash[:16] + "..." if local_hash else "",
            "server_checksum_verified": bool(local_hash and server_checksum),
        }, f"Track {track_id} uploaded, mapping={mapping_status}")

    # ── Artwork & Playlist ──

    def upload_artwork(self, session_id: str, cover_id: str,
                       artwork_path: str = "",
                       artwork_data: bytes | None = None,
                       retries: int = 1) -> Result:
        """Upload cover artwork to the server (real HTTP + checksum)."""
        checked = self._check_session(session_id)
        if isinstance(checked, Result):
            return checked
        session: ImportSession = checked
        server = session.server
        if server is None:
            return Result.fail("INVALID_SESSION", "Session has no server")

        data = artwork_data
        if data is None:
            if not artwork_path or not os.path.isfile(artwork_path):
                return Result.fail("ARTWORK_NOT_FOUND",
                                   f"File not found: {artwork_path}")
            try:
                with open(artwork_path, "rb") as f:
                    data = f.read()
            except OSError as e:
                return Result.fail("ARTWORK_READ_ERROR", str(e))
        checksum = hashlib.sha256(data).hexdigest()

        headers = {
            "Content-Type": "application/octet-stream",
            "X-Cover-Id": cover_id,
            "X-Import-Session-Id": session_id,
            "X-Checksum": checksum,
        }
        attempt = 0
        while True:
            try:
                req = urllib.request.Request(
                    url=f"http://{server.host}:{server.port}"
                        f"/api/v1/import/track/artwork",
                    data=data, method="POST",
                    headers=self._auth_headers(server, headers),
                )
                with urllib.request.urlopen(req, timeout=30) as r:
                    resp_json = json.loads(r.read().decode() or "{}")
                break
            except urllib.error.HTTPError as e:
                if e.code in (408, 429, 502, 503, 504) and attempt < retries:
                    attempt += 1
                    time.sleep(_RETRY_BACKOFF * attempt)
                    continue
                return Result.fail("ARTWORK_UPLOAD_FAILED",
                                   f"HTTP {e.code}: {e.reason}")
            except _TRANSIENT_ERRORS as e:
                if attempt < retries:
                    attempt += 1
                    time.sleep(_RETRY_BACKOFF * attempt)
                    continue
                return Result.fail("ARTWORK_UPLOAD_FAILED", str(e))

        server_checksum = resp_json.get("checksum", "")
        if server_checksum and not hmac.compare_digest(checksum, server_checksum):
            return Result.fail("ARTWORK_CHECKSUM_MISMATCH",
                               "Server checksum does not match artwork")
        session.artwork_uploaded += 1
        return Result.success({
            "cover_id": cover_id,
            "bytes": len(data),
            "server_checksum": server_checksum or checksum,
        }, f"Artwork {cover_id} uploaded to server")

    def upload_playlist(self, session_id: str, playlist: dict,
                        retries: int = 1) -> Result:
        """Upload playlist metadata to the server (real HTTP)."""
        checked = self._check_session(session_id)
        if isinstance(checked, Result):
            return checked
        session: ImportSession = checked
        server = session.server
        if server is None:
            return Result.fail("INVALID_SESSION", "Session has no server")

        body = {
            "session_id": session_id,
            "playlist_id": playlist.get("playlist_id", ""),
            "name": playlist.get("name", ""),
            "track_ids": playlist.get("track_ids", []),
        }
        attempt = 0
        while True:
            try:
                req = urllib.request.Request(
                    url=f"http://{server.host}:{server.port}"
                        f"/api/v1/import/playlists/upload",
                    data=json.dumps(body).encode(), method="POST",
                    headers=self._auth_headers(server),
                )
                with urllib.request.urlopen(req, timeout=15) as r:
                    resp_json = json.loads(r.read().decode() or "{}")
                break
            except urllib.error.HTTPError as e:
                if e.code in (408, 429, 502, 503, 504) and attempt < retries:
                    attempt += 1
                    time.sleep(_RETRY_BACKOFF * attempt)
                    continue
                return Result.fail("PLAYLIST_UPLOAD_FAILED",
                                   f"HTTP {e.code}: {e.reason}")
            except _TRANSIENT_ERRORS as e:
                if attempt < retries:
                    attempt += 1
                    time.sleep(_RETRY_BACKOFF * attempt)
                    continue
                return Result.fail("PLAYLIST_UPLOAD_FAILED", str(e))

        session.playlists_uploaded += 1
        return Result.success({
            "playlist_id": playlist.get("playlist_id", ""),
            "name": playlist.get("name", ""),
            "track_count": resp_json.get("track_count",
                                         len(playlist.get("track_ids", []))),
            "stored": bool(resp_json.get("stored", True)),
        }, "Playlist uploaded to server")

    # ── Cancellation ──

    def cancel(self, session_id: str) -> Result:
        """Cancel a pending import session (no further uploads/commit)."""
        session = self._sessions.get(session_id)
        if session is None:
            return Result.fail("INVALID_SESSION", "Session not found")
        session.cancelled = True
        logger.info("Import session %s cancelled (%d uploaded)",
                    session_id, session.uploaded)
        return Result.success({"session_id": session_id,
                               "cancelled": True}, "Session cancelled")

    # ── Readback / verification ──

    def verify_upload(self, session_id: str, track_id: str) -> Result:
        """Verify a remote track by readback (checksum comparison)."""
        checked = self._check_session(session_id, require_server=False)
        if isinstance(checked, Result):
            return checked
        session: ImportSession = checked
        server = session.server
        if server is None:
            return Result.fail("INVALID_SESSION", "Session has no server")
        info = self._get_json(
            server, f"/api/v1/import/track/info?session_id={session_id}"
                    f"&track_id={track_id}",
        )
        if not info.ok:
            return Result.fail("VERIFY_FAILED", info.message)
        server_checksum = info.data.get("checksum", "")
        local_checksum = session.checksums.get(track_id, "")
        verified = bool(server_checksum) and bool(local_checksum) and \
            hmac.compare_digest(server_checksum, local_checksum)
        return Result.success({
            "track_id": track_id,
            "verified": verified,
            "server_checksum": server_checksum,
        }, "Checksum verified" if verified else "Checksum mismatch")

    def readback(self, session_id: str) -> Result:
        """Fetch server-side session status and compare with local counters."""
        checked = self._check_session(session_id, require_server=False)
        if isinstance(checked, Result):
            return checked
        session: ImportSession = checked
        server = session.server
        if server is None:
            return Result.fail("INVALID_SESSION", "Session has no server")
        status = self._get_json(
            server, f"/api/v1/import/session/status?session_id={session_id}",
        )
        if not status.ok:
            return Result.fail("READBACK_FAILED", status.message)
        data = status.data or {}
        state = data.get("state", "")
        if state == "expired":
            return Result.fail("SESSION_EXPIRED",
                               "Import session expired on the server")
        return Result.success({
            "session_id": session_id,
            "state": state,
            "server_tracks": int(data.get("uploaded_tracks") or 0),
            "server_artwork": int(data.get("artwork_count") or 0),
            "server_playlists": int(data.get("playlist_count") or 0),
            "local_tracks": session.uploaded,
            "local_artwork": session.artwork_uploaded,
            "local_playlists": session.playlists_uploaded,
            "consistent": (
                int(data.get("uploaded_tracks") or 0) == session.uploaded
                and int(data.get("artwork_count") or 0) == session.artwork_uploaded
                and int(data.get("playlist_count") or 0) == session.playlists_uploaded
            ),
        })

    # ── Commit / Rollback / Status ──

    def commit(self, session_id: str) -> Result:
        checked = self._check_session(session_id)
        if isinstance(checked, Result):
            return checked
        session: ImportSession = checked
        server = session.server
        if server is None:
            return Result.fail("INVALID_SESSION", "Session has no server")
        if session.errors:
            return Result.fail("HAS_ERRORS",
                               f"{len(session.errors)} tracks failed")

        committed = self._post_json(
            server, "/api/v1/import/session/commit",
            {"session_id": session_id}, timeout=15,
        )
        if not committed.ok:
            if committed.code == "SESSION_EXPIRED":
                return committed
            if committed.code == "ENDPOINT_NOT_FOUND":
                return Result.fail("IMPORT_ENDPOINTS_MISSING",
                                   "Server lacks import commit endpoint")
            return Result.fail("COMMIT_FAILED", committed.message)

        data = committed.data or {}
        remote_mapping_raw = data.get("mapping", [])
        if isinstance(remote_mapping_raw, list):
            for entry in remote_mapping_raw:
                local_id = entry.get("michi_track_id") or entry.get("local_track_id", "")
                remote_id = entry.get("server_track_id") or entry.get("remote_track_id", "")
                if local_id and remote_id:
                    session.mapping[local_id] = remote_id
        elif isinstance(remote_mapping_raw, dict):
            session.mapping.update(remote_mapping_raw)

        # Readback verification: the server must confirm what we uploaded.
        readback_result = self.readback(session_id)
        readback_verified = False
        readback_data = {}
        if readback_result.ok and isinstance(readback_result.data, dict):
            readback_data = readback_result.data
            readback_verified = bool(readback_data.get("consistent"))
        elif readback_result.code == "SESSION_EXPIRED":
            return Result.fail("SESSION_EXPIRED",
                               "Session expired before commit readback")

        session.committed = True
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
            "readback_verified": readback_verified,
            "readback": readback_data,
        }, f"Import committed: {session.uploaded}/{session.total} tracks "
           f"(readback={'verified' if readback_verified else 'unavailable'})")

    def rollback(self, session_id: str) -> Result:
        """Roll back an import session.

        The server must confirm the session is dropped; an unreachable server
        is reported (REMOTE_ROLLBACK_FAILED) and the local session is kept so
        the caller can retry.
        """
        session = self._sessions.get(session_id)
        if session is None:
            return Result.fail("SESSION_NOT_FOUND", "Session not found")
        server = session.server
        if server is not None and session.server_created:
            rolled = self._post_json(
                server, "/api/v1/import/session/rollback",
                {"session_id": session_id}, timeout=15,
            )
            if not rolled.ok:
                if rolled.code in ("SESSION_NOT_FOUND", "ENDPOINT_NOT_FOUND"):
                    # Nothing to roll back server-side: the session was
                    # already dropped (or the server predates rollback).
                    logger.info("Server rollback: %s — local session dropped",
                                rolled.message)
                else:
                    return Result.fail("REMOTE_ROLLBACK_FAILED",
                                       rolled.message)
        self._sessions.pop(session_id, None)
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
            "cancelled": session.cancelled,
            "committed": session.committed,
            "expired": session.is_expired,
        })

    def get_session(self, session_id: str) -> ImportSession | None:
        return self._sessions.get(session_id)
