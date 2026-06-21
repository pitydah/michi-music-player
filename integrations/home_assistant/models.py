"""Home Assistant data models."""
from dataclasses import dataclass, field


@dataclass
class HomeAssistantConfig:
    name: str = ""
    base_url: str = ""
    token: str = ""
    verify_ssl: bool = True


@dataclass
class HomeAudioDevice:
    id: str = ""
    entity_id: str = ""
    name: str = ""
    state: str = "unavailable"
    area: str = ""
    room: str = ""
    device_type: str = ""
    backend: str = ""
    supported_features: int = 0
    volume_level: float | None = None
    muted: bool | None = None
    media_title: str = ""
    media_artist: str = ""
    media_album: str = ""
    source: str = ""
    app_name: str = ""
    entity_picture: str = ""
    ip_address: str = ""
    port: int = 0
    is_cast: bool = False
    is_snapclient: bool = False
    available: bool = True
    group_id: str = ""


@dataclass
class HomeAudioGroup:
    id: str = ""
    name: str = ""
    members: list = field(default_factory=list)
    volume_level: float | None = None
    active: bool = False


@dataclass
class CastRequest:
    target_id: str = ""
    media_url: str = ""
    media_content_type: str = "music"
    title: str = ""
    artist: str = ""
    album: str = ""
    image_url: str = ""
