"""Subsonic API client — Navidrome + Jellyfin shared client.

API docs: http://www.subsonic.org/pages/api.jsp
Auth: token = MD5(password + salt), sent as &t=token&s=salt&u=user&v=1.16.0&c=MichiMusicPlayer&f=json
"""

import hashlib
import json
import urllib.request
import urllib.parse
import urllib.error
import socket
import random
import os
import time
import logging

from core.paths import app_data_dir, subsonic_servers_path
from dataclasses import dataclass

logger = logging.getLogger("michi.subsonic")


class SubsonicError(Exception):
    def __init__(self, message: str, recoverable: bool = False):
        super().__init__(message)
        self.recoverable = recoverable


class AuthError(SubsonicError):
    pass


class ServerNotFoundError(SubsonicError):
    pass


MAX_RETRIES = 3
RETRY_BACKOFF = [1, 3, 6]  # seconds between retries


@dataclass
class ServerConfig:
    name: str
    url: str
    username: str
    password: str
    stype: str = "navidrome"  # "navidrome" | "jellyfin"

    def to_dict(self):
        return {"name": self.name, "url": self.url,
                "username": self.username, "password": self.password,
                "type": self.stype}

    @classmethod
    def from_dict(cls, d: dict):
        return cls(name=d["name"], url=d["url"],
                   username=d["username"], password=d.get("password", ""),
                   stype=d.get("type", "navidrome"))


@dataclass
class RemoteArtist:
    id: str
    name: str


@dataclass
class RemoteAlbum:
    id: str
    name: str
    artist: str
    cover_id: str = ""


@dataclass
class RemoteTrack:
    id: str
    title: str
    artist: str
    album: str
    duration: int
    track: int


class SubsonicClient:
    def __init__(self, server: ServerConfig):
        self.server = server
        self._salt = ""
        self._token = ""
        self._cancelled = False
        self._timeout = 20

    def cancel(self):
        self._cancelled = True

    def _auth(self) -> str:
        if not self._salt:
            self._salt = f"{random.randint(0, 0xFFFFFFFF):08x}"
        token = hashlib.md5(
            (self.server.password + self._salt).encode("utf-8")
        ).hexdigest()
        self._token = token
        return (f"u={urllib.parse.quote(self.server.username)}"
                f"&t={token}&s={self._salt}"
                f"&v=1.16.0&c=MichiMusicPlayer&f=json")

    def _get(self, endpoint: str, params: dict = None) -> dict:
        auth = self._auth()
        extra = ""
        if params:
            extra = "&" + urllib.parse.urlencode(params)
        url = f"{self.server.url.rstrip('/')}/rest/{endpoint}?{auth}{extra}"

        last_error = None
        for attempt in range(MAX_RETRIES):
            if self._cancelled:
                raise SubsonicError("Request cancelled", recoverable=False)
            try:
                req = urllib.request.Request(url)
                req.add_header("User-Agent", "MichiMusicPlayer/1.0")
                with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                sub = data.get("subsonic-response", {})
                if sub.get("status") == "failed":
                    error_msg = sub.get("error", {}).get("message", "Unknown error")
                    error_code = sub.get("error", {}).get("code", 0)
                    if error_code == 40:
                        raise AuthError(error_msg, recoverable=False)
                    if error_code == 70:
                        raise ServerNotFoundError(error_msg, recoverable=True)
                    raise SubsonicError(error_msg, recoverable=True)
                return sub
            except AuthError:
                raise
            except urllib.error.HTTPError as e:
                if e.code in (401, 403):
                    raise AuthError(f"Authentication failed: {e}", recoverable=False) from e
                last_error = SubsonicError(
                    f"Server error ({e.code}): {e.reason}", recoverable=True)
            except urllib.error.URLError as e:
                reason = str(e.reason)
                if "timed out" in reason.lower():
                    last_error = SubsonicError(
                        f"Connection timed out to {self.server.name}", recoverable=True)
                elif "refused" in reason.lower():
                    last_error = SubsonicError(
                        f"Connection refused by {self.server.name}", recoverable=True)
                elif "getaddrinfo" in reason.lower() or "Name or service not known" in reason:
                    last_error = ServerNotFoundError(
                        f"Server not found: {self.server.url}", recoverable=False)
                else:
                    last_error = SubsonicError(
                        f"Network error: {reason}", recoverable=True)
            except (socket.timeout, TimeoutError):
                last_error = SubsonicError(
                    f"Connection timed out to {self.server.name}", recoverable=True)
            except json.JSONDecodeError:
                last_error = SubsonicError(
                    "Invalid response from server", recoverable=True)

            if attempt < MAX_RETRIES - 1 and last_error and last_error.recoverable:
                time.sleep(RETRY_BACKOFF[attempt])
                self._salt = ""  # re-auth on retry

        raise last_error or SubsonicError("Unknown error")

    def ping(self) -> bool:
        try:
            self._get("ping")
            return True
        except Exception as e:
            logger.debug("ping failed for %s: %s", self.server.name, e)
            return False

    def get_artists(self) -> list[RemoteArtist]:
        resp = self._get("getArtists")
        artists = []
        for idx in resp.get("artists", {}).get("index", []):
            for a in idx.get("artist", []):
                artists.append(RemoteArtist(id=a["id"], name=a["name"]))
        return sorted(artists, key=lambda a: a.name.lower())

    def get_albums(self, artist_id: str = None) -> list[RemoteAlbum]:
        if artist_id:
            resp = self._get("getArtist", {"id": artist_id})
            artist_data = resp.get("artist", {})
            albums = []
            for a in artist_data.get("album", []):
                albums.append(RemoteAlbum(
                    id=a["id"], name=a["name"],
                    artist=artist_data.get("name", ""),
                    cover_id=a.get("coverArt", a.get("id", "")),
                ))
            return albums
        # All albums
        resp = self._get("getAlbumList2", {"type": "newest", "size": 500})
        albums = []
        for a in resp.get("albumList2", {}).get("album", []):
            albums.append(RemoteAlbum(
                id=a["id"], name=a["name"],
                artist=a.get("artist", ""),
                cover_id=a.get("coverArt", a.get("id", "")),
            ))
        return albums

    def get_album_tracks(self, album_id: str) -> list[RemoteTrack]:
        resp = self._get("getAlbum", {"id": album_id})
        album_data = resp.get("album", {})
        tracks = []
        for s in album_data.get("song", []):
            tracks.append(RemoteTrack(
                id=s["id"], title=s.get("title", ""),
                artist=s.get("artist", ""), album=s.get("album", ""),
                duration=s.get("duration", 0), track=s.get("track", 0),
            ))
        return sorted(tracks, key=lambda t: t.track)

    def get_cover_url(self, cover_id: str, size: int = 200) -> str:
        auth = self._auth()
        return (f"{self.server.url.rstrip('/')}/rest/getCoverArt"
                f"?{auth}&id={cover_id}&size={size}")

    def get_stream_url(self, track_id: str) -> str:
        auth = self._auth()
        return (f"{self.server.url.rstrip('/')}/rest/stream"
                f"?{auth}&id={track_id}")

    def search(self, query: str) -> list[RemoteArtist]:
        try:
            resp = self._get("search3", {"query": query,
                                          "artistCount": 20,
                                          "albumCount": 0,
                                          "songCount": 0})
            artists = []
            for a in resp.get("searchResult3", {}).get("artist", []):
                artists.append(RemoteArtist(id=a["id"], name=a["name"]))
            return artists
        except Exception as e:
            logger.warning("search failed for %s: %s", self.server.name, e)
            return []


# ── Server persistence ──

CONFIG_DIR = app_data_dir()
SERVERS_PATH = subsonic_servers_path()


def load_servers() -> list[ServerConfig]:
    if os.path.exists(SERVERS_PATH):
        with open(SERVERS_PATH) as f:
            return [ServerConfig.from_dict(d) for d in json.load(f)]
    return []


def save_servers(servers: list[ServerConfig]):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(SERVERS_PATH, "w") as f:
        json.dump([s.to_dict() for s in servers], f, indent=2)
