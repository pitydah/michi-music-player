"""MPD data models."""

from dataclasses import dataclass


@dataclass
class MpdStatus:
    state: str = "stop"
    song: int = -1
    songid: int = -1
    elapsed: float = 0.0
    duration: float = 0.0
    volume: int = -1
    repeat: bool = False
    random: bool = False
    single: bool = False
    consume: bool = False
    playlist: int = 0
    playlistlength: int = 0
    bitrate: int = 0
    audio: str = ""
    error: str = ""


@dataclass
class MpdSong:
    file: str = ""
    title: str = ""
    artist: str = ""
    album: str = ""
    albumartist: str = ""
    track: str = ""
    genre: str = ""
    date: str = ""
    duration: float = 0.0
    pos: int = -1
    id: int = -1


@dataclass
class MpdOutput:
    id: int = 0
    name: str = ""
    enabled: bool = False


@dataclass
class MpdStats:
    artists: int = 0
    albums: int = 0
    songs: int = 0
    uptime: int = 0
    db_playtime: int = 0
    db_update: int = 0
    playtime: int = 0
