"""Michi Music Player — media_source for library browsing in Home Assistant."""
import logging
import aiohttp
from homeassistant.components.media_player import MediaClass, MediaType
from homeassistant.components.media_source.error import Unresolvable
from homeassistant.components.media_source.models import (
    MediaSource, MediaSourceItem, BrowseMediaSource,
    PlayMedia,
)
from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_HOST, CONF_PORT, CONF_TOKEN

_LOGGER = logging.getLogger(__name__)

MICHI_URI_SCHEME = "michi-source"
MICHI_MEDIA_ID_PREFIX = f"{MICHI_URI_SCHEME}://"


class AstraMediaSource(MediaSource):
    def __init__(self, hass: HomeAssistant):
        super().__init__(DOMAIN)
        self.hass = hass

    def _get_config(self) -> dict | None:
        entries = self.hass.config_entries.async_entries(DOMAIN)
        if not entries:
            return None
        return dict(entries[0].data)

    async def _api_get(self, path: str) -> dict:
        cfg = self._get_config()
        if not cfg:
            return {}
        url = f"http://{cfg[CONF_HOST]}:{cfg.get(CONF_PORT, 8124)}{path}"
        headers = {"Authorization": f"Bearer {cfg[CONF_TOKEN]}"}
        try:
            async with aiohttp.ClientSession() as session, session.get(
                    url, headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)) as resp:
                return await resp.json()
        except Exception as e:
            _LOGGER.debug("Michi media_source error: %s", e)
            return {}

    async def async_browse_media(self, item: MediaSourceItem) -> BrowseMediaSource:
        parent_id = item.identifier or ""
        if parent_id.startswith(MICHI_MEDIA_ID_PREFIX):
            parent_id = parent_id[len(MICHI_MEDIA_ID_PREFIX):]

        if not parent_id:
            data = await self._api_get("/api/library/browse")
            children = data.get("children", [])
            return BrowseMediaSource(
                domain=DOMAIN, identifier="",
                media_class=MediaClass.DIRECTORY,
                media_content_type=MediaType.MUSIC,
                title="Michi Music Player",
                can_play=False, can_expand=True,
                children=[
                    BrowseMediaSource(
                        domain=DOMAIN,
                        identifier=f"{MICHI_MEDIA_ID_PREFIX}{c['id']}",
                        media_class=MediaClass.DIRECTORY if c.get("can_expand")
                                    else MediaClass.TRACK,
                        media_content_type=MediaType.MUSIC,
                        title=c["title"],
                        can_play=c.get("can_play", False),
                        can_expand=c.get("can_expand", False),
                        thumbnail=c.get("thumbnail"),
                    )
                    for c in children
                ],
            )

        data = await self._api_get(
            f"/api/library/browse?parent_id={parent_id}")
        children = data.get("children", [])
        return BrowseMediaSource(
            domain=DOMAIN, identifier=parent_id,
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.MUSIC,
            title=parent_id.replace("_", " ").title(),
            can_play=False, can_expand=True,
            children=[
                BrowseMediaSource(
                    domain=DOMAIN,
                    identifier=c.get("media_id", c.get("id", "")),
                    media_class=MediaClass.TRACK if c.get("can_play")
                                else MediaClass.DIRECTORY,
                    media_content_type=MediaType.MUSIC,
                    title=c["title"],
                    can_play=c.get("can_play", False),
                    can_expand=c.get("can_expand", False),
                    thumbnail=c.get("thumbnail"),
                )
                for c in children
            ],
        )

    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        media_id = item.identifier or ""
        if media_id.startswith(MICHI_MEDIA_ID_PREFIX):
            media_id = media_id[len(MICHI_MEDIA_ID_PREFIX):]

        cfg = self._get_config()
        if not cfg:
            raise Unresolvable("Michi not configured")

        return PlayMedia(
            url=f"michi://{media_id}",
            mime_type="audio/x-michi-local",
        )


async def async_get_media_source(hass: HomeAssistant):
    return AstraMediaSource(hass)
