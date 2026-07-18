"""MicroServerService — import tracks/albums/artists to Michi Micro Server."""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger("michi.micro_server")

_DEFAULT_TIMEOUT = 10


class MicroServerService:
    def __init__(self, db=None):
        self._db = db

    def import_tracks(self, filepaths: list[str], server_url: str = "") -> dict:
        if not server_url:
            return {"ok": False, "error": "NO_SERVER_URL", "imported": 0}
        if not filepaths:
            return {"ok": True, "imported": 0, "server": server_url}

        ok_count = 0
        fail_count = 0
        errors = []

        for fp in filepaths:
            if not os.path.isfile(fp):
                fail_count += 1
                errors.append({"path": fp, "error": "FILE_NOT_FOUND"})
                continue
            try:
                result = self._send_file(server_url, fp)
                if result.get("ok"):
                    ok_count += 1
                else:
                    fail_count += 1
                    errors.append({"path": fp, "error": result.get("error", "UNKNOWN")})
            except Exception as e:
                fail_count += 1
                errors.append({"path": fp, "error": str(e)})

        return {
            "ok": fail_count == 0,
            "imported": ok_count,
            "failed": fail_count,
            "total": len(filepaths),
            "errors": errors[:10],
            "server": server_url,
        }

    def _send_file(self, server_url: str, filepath: str) -> dict:
        try:
            with open(filepath, "rb") as f:
                data = f.read()
            url = f"{server_url.rstrip('/')}/api/import"
            req = urllib.request.Request(
                url, data=data,
                headers={"Content-Type": "audio/flac",
                         "X-Filename": os.path.basename(filepath)},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=_DEFAULT_TIMEOUT) as resp:
                body = resp.read().decode()
                return json.loads(body) if body else {"ok": True}
        except urllib.error.HTTPError as e:
            return {"ok": False, "error": f"HTTP {e.code}: {e.reason}"}
        except urllib.error.URLError as e:
            return {"ok": False, "error": f"Connection failed: {e.reason}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _tracks_for_album_key(self, album_key: str) -> list[str]:
        if not self._db:
            return []
        try:
            rows = self._db.conn.execute(
                "SELECT filepath FROM media_items WHERE deleted_at IS NULL "
                "AND album_key=?",
                (album_key,)).fetchall()
            return [r[0] for r in rows]
        except Exception:
            return []

    def import_album(self, album_key: str, server_url: str = "") -> dict:
        return self.import_tracks(self._tracks_for_album_key(album_key), server_url)

    def import_artist(self, artist: str, server_url: str = "") -> dict:
        if not self._db:
            return {"ok": False, "error": "NO_DB"}
        try:
            rows = self._db.conn.execute(
                "SELECT filepath FROM media_items WHERE deleted_at IS NULL AND artist=?",
                (artist,)).fetchall()
            return self.import_tracks([r[0] for r in rows], server_url)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def check_compatibility(self, server_url: str = "") -> dict:
        return {"ok": True, "compatible": False, "message": "DEFERRED_PHYSICAL"}

    def health(self) -> dict:
        return {"available": self._db is not None}

    def shutdown(self):
        pass
