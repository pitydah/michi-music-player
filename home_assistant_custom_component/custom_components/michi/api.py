"""Michi API client — async wrapper for the Michi HTTP API."""
import logging
import aiohttp
from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_HOST, CONF_PORT, CONF_TOKEN

_LOGGER = logging.getLogger(__name__)


class MichiApiClient:
    """Async client for Michi Music Player HTTP API."""

    def __init__(self, host: str, port: int, token: str):
        self._host = host
        self._port = port
        self._token = token

    @property
    def base_url(self) -> str:
        return f"http://{self._host}:{self._port}"

    @property
    def headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token}"}

    async def _get(self, path: str) -> dict:
        url = f"{self.base_url}{path}"
        try:
            async with aiohttp.ClientSession() as session, session.get(
                    url, headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=10)) as resp:
                return await resp.json()
        except Exception as e:
            _LOGGER.debug("Michi GET %s error: %s", path, e)
            return {}

    async def _post(self, path: str, data: dict = None) -> dict:
        url = f"{self.base_url}{path}"
        try:
            async with aiohttp.ClientSession() as session, session.post(
                    url, json=data or {}, headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=10)) as resp:
                return await resp.json()
        except Exception as e:
            _LOGGER.debug("Michi POST %s error: %s", path, e)
            return {}

    # ── Player status ──

    async def get_status(self) -> dict:
        return await self._get("/api/player/status")

    # ── Player controls ──

    async def play(self):
        await self._post("/api/player/play")

    async def pause(self):
        await self._post("/api/player/pause")

    async def stop(self):
        await self._post("/api/player/stop")

    async def next_track(self):
        await self._post("/api/player/next")

    async def prev_track(self):
        await self._post("/api/player/previous")

    async def set_volume(self, volume: float):
        await self._post("/api/player/volume", {"volume": int(volume * 100)})

    async def play_media(self, media_id: str, media_content_type: str = "music",
                          title: str = "", artist: str = "",
                          album: str = "", image_url: str = "",
                          destination: str = "local"):
        await self._post("/api/player/play_media", {
            "media_id": media_id,
            "media_content_type": media_content_type,
            "title": title,
            "artist": artist,
            "album": album,
            "image_url": image_url,
            "destination": destination,
        })

    # ── Destinations ──

    async def get_destinations(self) -> list:
        return await self._get("/api/player/destinations")

    async def select_destination(self, dest_id: str):
        await self._post("/api/player/select_destination",
                          {"id": dest_id})

    # ── Library ──

    async def browse_library(self, parent_id: str = "") -> dict:
        path = "/api/library/browse"
        if parent_id:
            path += f"?parent_id={parent_id}"
        return await self._get(path)

    async def library_play(self, media_id: str, destination: str = "local"):
        await self._post("/api/library/play", {
            "media_id": media_id,
            "destination": destination,
        })


def get_client(hass: HomeAssistant) -> MichiApiClient | None:
    """Get Michi API client from config entry."""
    entries = hass.config_entries.async_entries(DOMAIN)
    if not entries:
        return None
    data = dict(entries[0].data)
    return MichiApiClient(
        host=data.get(CONF_HOST, ""),
        port=data.get(CONF_PORT, 8124),
        token=data.get(CONF_TOKEN, ""),
    )
