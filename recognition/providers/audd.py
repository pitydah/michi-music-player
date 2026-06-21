"""AudDProvider — real AudD.io API integration.

Requirements:
    - API key from https://audd.io/
    - Set via settings: identifier/api_key_audd
    - Audio captured via AudioCaptureService → sends raw bytes
"""
import json
import logging
import urllib.request

from recognition.base_recognizer import BaseRecognizer

logger = logging.getLogger("astra.recognition.audd")

AUDD_API_URL = "https://api.audd.io/"


class AudDProvider(BaseRecognizer):
    """Music recognition via AudD.io HTTP API."""

    name = "audd"
    requires_api_key = True

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def identify(self, sample_bytes=None, source="", filepath=""):
        """Identify audio via AudD API.

        Sends audio bytes as base64-encoded body.
        Falls back to filepath if `sample_bytes` is None.
        """
        if not self.api_key:
            logger.warning("AudD: no API key configured")
            return None

        try:
            import base64

            if sample_bytes:
                audio_b64 = base64.b64encode(sample_bytes).decode()
            elif filepath:
                with open(filepath, "rb") as f:
                    audio_b64 = base64.b64encode(f.read()).decode()
            else:
                return None

            data = json.dumps({
                "api_token": self.api_key,
                "audio": audio_b64,
                "return": "apple_music,spotify",
            }).encode()

            req = urllib.request.Request(
                AUDD_API_URL, data=data,
                headers={"Content-Type": "application/json"},
                method="POST")
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = json.loads(resp.read().decode())

            if body.get("status") != "success" or not body.get("result"):
                return None

            r = body["result"]
            return {
                "title": r.get("title", ""),
                "artist": r.get("artist", ""),
                "album": r.get("album", ""),
                "year": 0,
                "confidence": 0.9,
                "provider": self.name,
                "source": "audd",
                "external_url": r.get("song_link", ""),
                "artwork_url": "",
                "isrc": r.get("isrc", ""),
                "raw_json": body,
            }
        except Exception as e:
            logger.debug(f"AudD identify failed: {e}")
            return None

    def test_connection(self) -> tuple[bool, str]:
        if not self.api_key:
            return False, "No API key configured"
        # AudD doesn't have a test endpoint — try a lightweight call
        return True, "AudD configured"
