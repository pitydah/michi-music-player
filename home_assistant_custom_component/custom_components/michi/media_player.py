"""Michi Music Player — Home Assistant media_player entity."""
import logging
import aiohttp
from homeassistant.components.media_player import (
    MediaPlayerEntity, MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import CONF_HOST, CONF_PORT, CONF_TOKEN

_LOGGER = logging.getLogger(__name__)

SUPPORT_ASTRA = (
    MediaPlayerEntityFeature.PLAY
    | MediaPlayerEntityFeature.PAUSE
    | MediaPlayerEntityFeature.STOP
    | MediaPlayerEntityFeature.NEXT_TRACK
    | MediaPlayerEntityFeature.PREVIOUS_TRACK
    | MediaPlayerEntityFeature.VOLUME_SET
    | MediaPlayerEntityFeature.SELECT_SOURCE
    | MediaPlayerEntityFeature.PLAY_MEDIA
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                             async_add_entities):
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    token = entry.data[CONF_TOKEN]
    async_add_entities([AstraMediaPlayer(host, port, token)])


class AstraMediaPlayer(MediaPlayerEntity):
    def __init__(self, host: str, port: int, token: str):
        self._host = host
        self._port = port
        self._token = token
        self._attr_name = "Michi Music Player"
        self._attr_unique_id = f"michi_{host}_{port}"
        self._attr_state = MediaPlayerState.IDLE
        self._attr_media_title = ""
        self._attr_media_artist = ""
        self._attr_media_album_name = ""
        self._attr_volume_level = 0.7
        self._attr_source_list = ["local"]
        self._attr_source = "local"
        self._attr_supported_features = SUPPORT_ASTRA
        self._attr_media_image_url = ""

    @property
    def _base_url(self) -> str:
        return f"http://{self._host}:{self._port}"

    @property
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token}"}

    async def _get(self, path: str) -> dict:
        async with aiohttp.ClientSession() as session, session.get(
                f"{self._base_url}{path}",
                headers=self._headers) as resp:
            return await resp.json()

    async def _post(self, path: str, data: dict = None) -> dict:
        async with aiohttp.ClientSession() as session, session.post(
                f"{self._base_url}{path}",
                json=data or {}, headers=self._headers) as resp:
            return await resp.json()

    async def async_update(self):
        try:
            data = await self._get("/api/player/status")
            state = data.get("state", "idle")
            self._attr_state = {
                "playing": MediaPlayerState.PLAYING,
                "paused": MediaPlayerState.PAUSED,
                "idle": MediaPlayerState.IDLE,
            }.get(state, MediaPlayerState.IDLE)
            self._attr_media_title = data.get("title", "")
            self._attr_media_artist = data.get("artist", "")
            self._attr_media_album_name = data.get("album", "")
            self._attr_volume_level = data.get("volume", 70) / 100.0
            self._attr_media_image_url = data.get("cover_url", "")
            dests = await self._get("/api/player/destinations")
            self._attr_source_list = [d["name"] for d in dests]
            self._attr_source = "local"
        except Exception as e:
            _LOGGER.debug("Michi update error: %s", e)

    async def async_media_play(self):
        await self._post("/api/player/play")

    async def async_media_pause(self):
        await self._post("/api/player/pause")

    async def async_media_stop(self):
        await self._post("/api/player/stop")

    async def async_media_next_track(self):
        await self._post("/api/player/next")

    async def async_media_previous_track(self):
        await self._post("/api/player/previous")

    async def async_set_volume_level(self, volume: float):
        await self._post("/api/player/volume", {"volume": int(volume * 100)})

    async def async_select_source(self, source: str):
        dests = await self._get("/api/player/destinations")
        for d in dests:
            if d["name"] == source:
                await self._post("/api/player/select_destination",
                                  {"id": d["id"]})

    async def async_play_media(self, media_type: str, media_id: str, **kwargs):
        extra = kwargs.get("extra", {})
        metadata = extra.get("metadata", {})
        await self._post("/api/player/play_media", {
            "media_id": media_id,
            "media_content_type": media_type,
            "title": metadata.get("title", ""),
            "artist": metadata.get("artist", ""),
            "album": metadata.get("album", ""),
            "image_url": metadata.get("image_url", ""),
        })
