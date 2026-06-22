"""AcoustIDProvider — real AcoustID fingerprinting via fpcalc.

Requirements:
    - fpcalc (Chromaprint) in PATH
    - AcoustID API key (optional; anonymous/limited without)
    - Set via settings: identifier/api_key_acoustid
"""
import json
import logging
import subprocess
import urllib.request
import urllib.parse

from recognition.base_recognizer import BaseRecognizer

logger = logging.getLogger("michi.recognition.acoustid")

ACOUSTID_API_URL = "https://api.acoustid.org/v2/lookup"
ACOUSTID_CLIENT_KEY = "8XaBELgH"  # Default demo key


class AcoustIDProvider(BaseRecognizer):
    """Acoustic fingerprinting via AcoustID + libchromaprint (fpcalc)."""

    name = "acoustid"
    requires_api_key = False  # works with demo key, better with own

    def __init__(self):
        super().__init__()
        self._fpcalc_path = self._find_fpcalc()
        self._client_key = self.api_key or ACOUSTID_CLIENT_KEY

    def configure(self, api_key: str = ""):
        super().configure(api_key)
        self._client_key = api_key or ACOUSTID_CLIENT_KEY

    def is_configured(self) -> bool:
        return self._fpcalc_path is not None

    def identify(self, sample_bytes=None, source="", filepath=""):
        """Identify audio via AcoustID fingerprint.

        Requires filepath (AcoustID fingerprints from files, not raw bytes).
        """
        if not self._fpcalc_path:
            logger.warning("AcoustID: fpcalc not found")
            return None

        target = filepath
        if not target:
            # Can't process raw bytes without writing to a temp file
            if sample_bytes:
                import tempfile
                import os
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    tmp.write(sample_bytes)
                    target = tmp.name
            else:
                return None

        try:
            # Step 1: Generate fingerprint via fpcalc
            fingerprint, duration = self._fingerprint(target)
            if not fingerprint:
                return None

            # Step 2: Query AcoustID API
            params = {
                "client": self._client_key,
                "duration": str(int(duration)),
                "fingerprint": fingerprint,
                "meta": "recordings+releases+compress",
                "format": "json",
            }
            url = ACOUSTID_API_URL + "?" + urllib.parse.urlencode(params)

            req = urllib.request.Request(url, headers={"User-Agent": "Astra/2.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = json.loads(resp.read().decode())

            if body.get("status") != "ok":
                return None

            results = body.get("results", [])
            if not results:
                return None

            best = results[0]
            score = best.get("score", 0.0)
            if score < 0.7:
                return None

            recordings = best.get("recordings", [])
            if not recordings:
                return None

            rec = recordings[0]
            title = rec.get("title", "")
            artists = rec.get("artists", [])
            artist = artists[0].get("name", "") if artists else ""

            release_groups = rec.get("releasegroups", [])
            album = ""
            if release_groups:
                album = release_groups[0].get("title", "")

            return {
                "title": title,
                "artist": artist,
                "album": album,
                "year": 0,
                "confidence": min(score, 0.95),
                "provider": self.name,
                "source": "acoustid",
                "external_url": f"https://acoustid.org/track/{best.get('id', '')}",
                "artwork_url": "",
                "raw_json": best,
            }
        except Exception as e:
            logger.debug(f"AcoustID identify failed: {e}")
            return None
        finally:
            # Clean up temp file if we created one
            if target != filepath and target and sample_bytes:
                import os
                import contextlib
                with contextlib.suppress(OSError):
                    os.unlink(target)

    def _fingerprint(self, filepath: str) -> tuple[str | None, float]:
        """Run fpcalc and return (fingerprint, duration)."""
        try:
            result = subprocess.run(
                [self._fpcalc_path, "-json", filepath],
                capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                logger.debug("fpcalc failed: %s", result.stderr.strip())
                return None, 0.0
            data = json.loads(result.stdout)
            return data.get("fingerprint"), data.get("duration", 0.0)
        except Exception as e:
            logger.debug("fpcalc error: %s", e)
            return None, 0.0

    @staticmethod
    def _find_fpcalc() -> str | None:
        """Find fpcalc binary in PATH or common locations."""
        import shutil
        path = shutil.which("fpcalc")
        if path:
            return path
        # Common manual install paths
        for p in ["/usr/local/bin/fpcalc", "/usr/bin/fpcalc", "/opt/homebrew/bin/fpcalc"]:
            import os
            if os.path.isfile(p):
                return p
        return None

    def test_connection(self) -> tuple[bool, str]:
        if not self._fpcalc_path:
            return False, "fpcalc not found (install libchromaprint)"
        return True, f"fpcalc ready at {self._fpcalc_path}"
